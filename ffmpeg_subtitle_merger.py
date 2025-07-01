#!/usr/bin/env python3
"""
FFmpeg视频字幕合成工具
使用英伟达显卡硬件编码，将MPS视频和ASS字幕合成为硬字幕视频
保持原视频码率

优化版本 - 修复了安全漏洞，改进了错误处理和性能
"""

import os
import sys
import argparse
import ffmpeg
import json
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from fractions import Fraction


class FFmpegSubtitleMerger:
    """FFmpeg视频字幕合成器 - 优化版本"""

    def __init__(self, log_level: str = 'INFO'):
        self.supported_video_formats = ['.mps', '.mp4', '.avi', '.mkv', '.mov', '.ts', '.m2ts']
        self.supported_subtitle_formats = ['.ass', '.srt', '.vtt', '.sub']

        # 设置日志
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def parse_frame_rate(self, rate_str: str) -> float:
        """
        安全地解析帧率字符串

        Args:
            rate_str: 帧率字符串 (如 "25/1", "29.97")

        Returns:
            帧率浮点数
        """
        try:
            if '/' in rate_str:
                # 使用Fraction来安全处理分数
                fraction = Fraction(rate_str)
                return float(fraction)
            return float(rate_str)
        except (ValueError, ZeroDivisionError):
            self.logger.warning(f"无法解析帧率 '{rate_str}', 使用默认值 25.0")
            return 25.0

    def calculate_smart_bitrate(self, width: int, height: int, fps: float, original_bitrate: int = 0) -> int:
        """
        智能计算码率

        Args:
            width: 视频宽度
            height: 视频高度
            fps: 帧率
            original_bitrate: 原始码率

        Returns:
            建议的码率 (bps)
        """
        if original_bitrate > 0:
            return original_bitrate

        # 基于分辨率的基础码率计算
        pixels = width * height

        if pixels <= 640 * 480:  # SD
            base_bitrate = 1500000  # 1.5 Mbps
        elif pixels <= 1280 * 720:  # HD
            base_bitrate = 3000000  # 3 Mbps
        elif pixels <= 1920 * 1080:  # FHD
            base_bitrate = 5000000  # 5 Mbps
        elif pixels <= 3840 * 2160:  # 4K
            base_bitrate = 15000000  # 15 Mbps
        else:  # 8K+
            base_bitrate = 40000000  # 40 Mbps

        # 根据帧率调整
        fps_factor = min(fps / 25.0, 2.0)  # 最多2倍调整
        return int(base_bitrate * fps_factor)
        
    def probe_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        获取视频信息

        Args:
            video_path: 视频文件路径

        Returns:
            视频信息字典
        """
        try:
            self.logger.info(f"正在分析视频文件: {video_path}")
            probe = ffmpeg.probe(video_path)
            video_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
                None
            )

            if not video_stream:
                raise ValueError("未找到视频流")

            # 安全地获取各项信息
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))

            if width == 0 or height == 0:
                raise ValueError("无法获取视频分辨率信息")

            # 安全地解析帧率
            fps = self.parse_frame_rate(video_stream.get('r_frame_rate', '25/1'))

            # 安全地获取时长
            duration = 0.0
            if 'duration' in video_stream:
                try:
                    duration = float(video_stream['duration'])
                except (ValueError, TypeError):
                    self.logger.warning("无法解析视频时长")

            # 安全地获取码率
            bitrate = 0
            if 'bit_rate' in video_stream:
                try:
                    bitrate = int(video_stream['bit_rate'])
                except (ValueError, TypeError):
                    self.logger.warning("无法解析视频码率")

            video_info = {
                'width': width,
                'height': height,
                'fps': fps,
                'duration': duration,
                'bitrate': bitrate,
                'codec': video_stream.get('codec_name', 'unknown'),
                'pix_fmt': video_stream.get('pix_fmt', 'yuv420p')
            }

            self.logger.info(f"视频信息: {width}x{height} @ {fps}fps, 码率: {bitrate}bps")
            return video_info

        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            raise RuntimeError(f"FFmpeg探测失败: {error_msg}")
        except Exception as e:
            raise RuntimeError(f"获取视频信息失败: {e}")
    
    def validate_inputs(self, video_path: str, subtitle_path: str) -> None:
        """
        验证输入文件

        Args:
            video_path: 视频文件路径
            subtitle_path: 字幕文件路径
        """
        # 检查文件是否存在
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        if not os.path.exists(subtitle_path):
            raise FileNotFoundError(f"字幕文件不存在: {subtitle_path}")

        # 检查文件是否可读
        if not os.access(video_path, os.R_OK):
            raise PermissionError(f"无法读取视频文件: {video_path}")

        if not os.access(subtitle_path, os.R_OK):
            raise PermissionError(f"无法读取字幕文件: {subtitle_path}")

        # 检查文件格式
        video_ext = Path(video_path).suffix.lower()
        subtitle_ext = Path(subtitle_path).suffix.lower()

        if video_ext not in self.supported_video_formats:
            raise ValueError(f"不支持的视频格式: {video_ext}，支持的格式: {self.supported_video_formats}")

        if subtitle_ext not in self.supported_subtitle_formats:
            raise ValueError(f"不支持的字幕格式: {subtitle_ext}，支持的格式: {self.supported_subtitle_formats}")

        # 检查文件大小
        video_size = os.path.getsize(video_path)
        subtitle_size = os.path.getsize(subtitle_path)

        if video_size == 0:
            raise ValueError("视频文件为空")

        if subtitle_size == 0:
            raise ValueError("字幕文件为空")

        self.logger.info(f"输入验证通过 - 视频: {video_size} bytes, 字幕: {subtitle_size} bytes")
    
    def check_nvidia_support(self) -> bool:
        """
        检查是否支持英伟达硬件编码

        Returns:
            是否支持NVENC
        """
        try:
            # 方法1: 直接查询可用编码器
            result = subprocess.run(
                ['ffmpeg', '-encoders'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and 'h264_nvenc' in result.stdout:
                self.logger.info("检测到NVIDIA NVENC编码器支持")
                return True

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            self.logger.warning("无法查询FFmpeg编码器列表")

        try:
            # 方法2: 尝试创建简单的NVENC编码任务
            ffmpeg.run(
                ffmpeg.input('color=c=black:s=320x240:d=0.1', f='lavfi')
                .output('pipe:', vcodec='h264_nvenc', f='null')
                .global_args('-hide_banner', '-loglevel', 'error'),
                capture_stdout=True,
                capture_stderr=True,
                timeout=5
            )
            self.logger.info("NVIDIA NVENC编码器测试成功")
            return True

        except (ffmpeg.Error, subprocess.TimeoutExpired):
            self.logger.info("NVIDIA NVENC编码器不可用，将使用软件编码")
            return False
    
    def escape_subtitle_path(self, subtitle_path: str) -> str:
        """
        转义字幕文件路径，处理Windows路径和特殊字符

        Args:
            subtitle_path: 原始字幕路径

        Returns:
            转义后的路径
        """
        # 转换为绝对路径
        abs_path = os.path.abspath(subtitle_path)

        # Windows路径处理
        if os.name == 'nt':
            # 将反斜杠转换为正斜杠
            abs_path = abs_path.replace('\\', '/')
            # 转义冒号
            abs_path = abs_path.replace(':', '\\:')

        # 转义其他特殊字符
        abs_path = abs_path.replace('[', '\\[').replace(']', '\\]')

        return abs_path

    def merge_video_subtitle(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        force_style: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> None:
        """
        合成视频和字幕

        Args:
            video_path: 输入视频路径
            subtitle_path: 输入字幕路径
            output_path: 输出视频路径
            force_style: 强制字幕样式
            progress_callback: 进度回调函数
        """
        # 验证输入
        self.validate_inputs(video_path, subtitle_path)

        # 获取视频信息
        video_info = self.probe_video_info(video_path)

        # 计算智能码率
        smart_bitrate = self.calculate_smart_bitrate(
            video_info['width'],
            video_info['height'],
            video_info['fps'],
            video_info['bitrate']
        )

        # 检查NVIDIA支持
        use_nvenc = self.check_nvidia_support()

        if use_nvenc:
            self.logger.info("使用NVIDIA硬件编码 (h264_nvenc)")
            video_codec = 'h264_nvenc'
            # NVENC特定参数
            codec_params = {
                'preset': 'medium',
                'rc': 'vbr',
                'cq': '23',
                'b:v': f"{smart_bitrate}",
                'maxrate': f"{int(smart_bitrate * 1.2)}",
                'bufsize': f"{int(smart_bitrate * 2)}",
                'gpu': '0'  # 使用第一个GPU
            }
        else:
            self.logger.info("使用软件编码 (libx264)")
            video_codec = 'libx264'
            # x264参数
            codec_params = {
                'preset': 'medium',
                'crf': '23',
                'b:v': f"{smart_bitrate}",
                'threads': '0'  # 自动检测线程数
            }
        
        # 构建FFmpeg命令
        input_video = ffmpeg.input(video_path)
        
        # 字幕滤镜参数
        subtitle_filter_params = {'filename': subtitle_path}
        if force_style:
            subtitle_filter_params['force_style'] = force_style
        
        # 应用字幕滤镜
        video_with_subtitles = input_video.video.filter('subtitles', **subtitle_filter_params)
        
        # 音频流（直接复制）
        audio = input_video.audio
        
        # 输出配置
        output_params = {
            'vcodec': video_codec,
            'acodec': 'copy',  # 音频直接复制
            'pix_fmt': 'yuv420p',
            **codec_params
        }
        
        # 构建输出
        output = ffmpeg.output(
            video_with_subtitles,
            audio,
            output_path,
            **output_params
        )
        
        # 覆盖输出文件
        output = ffmpeg.overwrite_output(output)
        
        try:
            print(f"开始合成视频...")
            print(f"输入视频: {video_path}")
            print(f"输入字幕: {subtitle_path}")
            print(f"输出视频: {output_path}")
            print(f"使用编码器: {video_codec}")
            
            # 运行FFmpeg命令
            ffmpeg.run(output, capture_stdout=False, capture_stderr=False)
            
            print("视频合成完成!")
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            raise RuntimeError(f"FFmpeg处理失败: {error_msg}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="FFmpeg视频字幕合成工具 - 优化版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python ffmpeg_subtitle_merger.py input.mps subtitle.ass output.mp4
  python ffmpeg_subtitle_merger.py input.mp4 subtitle.ass output.mp4 --force-style "FontSize=24,PrimaryColour=&H00FFFF"
  python ffmpeg_subtitle_merger.py input.mp4 subtitle.ass output.mp4 --log-level DEBUG
        """
    )

    parser.add_argument('video', help='输入视频文件路径')
    parser.add_argument('subtitle', help='输入字幕文件路径')
    parser.add_argument('output', help='输出视频文件路径')
    parser.add_argument(
        '--force-style',
        help='强制字幕样式 (例如: "FontSize=24,PrimaryColour=&H00FFFF")'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='日志级别 (默认: INFO)'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='仅检查输入文件和系统支持，不执行转换'
    )

    args = parser.parse_args()

    try:
        merger = FFmpegSubtitleMerger(log_level=args.log_level)

        if args.check_only:
            # 仅执行检查
            merger.validate_inputs(args.video, args.subtitle)
            video_info = merger.probe_video_info(args.video)
            nvenc_support = merger.check_nvidia_support()

            print("=== 系统检查结果 ===")
            print(f"视频文件: {args.video}")
            print(f"字幕文件: {args.subtitle}")
            print(f"视频信息: {video_info['width']}x{video_info['height']} @ {video_info['fps']}fps")
            print(f"NVIDIA编码支持: {'是' if nvenc_support else '否'}")
            print("检查完成，所有输入有效。")
        else:
            # 执行完整转换
            merger.merge_video_subtitle(
                args.video,
                args.subtitle,
                args.output,
                args.force_style
            )

    except KeyboardInterrupt:
        print("\n用户中断操作", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
