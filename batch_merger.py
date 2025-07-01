#!/usr/bin/env python3
"""
批量FFmpeg视频字幕合成工具
支持批量处理指定目录下的所有视频文件
"""

import os
import sys
import argparse
import glob
from pathlib import Path
from typing import List, Tuple
from ffmpeg_subtitle_merger import FFmpegSubtitleMerger


class BatchSubtitleMerger:
    """批量字幕合成器"""
    
    def __init__(self, log_level: str = 'INFO'):
        self.merger = FFmpegSubtitleMerger(log_level)
        self.logger = self.merger.logger
        
    def find_video_subtitle_pairs(self, directory: str) -> List[Tuple[str, str]]:
        """
        在目录中查找视频和字幕文件对
        
        Args:
            directory: 搜索目录
            
        Returns:
            (视频文件, 字幕文件) 元组列表
        """
        video_extensions = ['*.mp4', '*.avi', '*.mkv', '*.mov', '*.mps', '*.ts', '*.m2ts']
        subtitle_extensions = ['*.ass', '*.srt', '*.vtt', '*.sub']
        
        # 查找所有视频文件
        video_files = []
        for ext in video_extensions:
            pattern = os.path.join(directory, '**', ext)
            video_files.extend(glob.glob(pattern, recursive=True))
        
        # 查找所有字幕文件
        subtitle_files = []
        for ext in subtitle_extensions:
            pattern = os.path.join(directory, '**', ext)
            subtitle_files.extend(glob.glob(pattern, recursive=True))
        
        # 匹配视频和字幕文件
        pairs = []
        for video_file in video_files:
            video_stem = Path(video_file).stem
            video_dir = Path(video_file).parent
            
            # 查找同名字幕文件
            matching_subtitles = []
            for subtitle_file in subtitle_files:
                subtitle_stem = Path(subtitle_file).stem
                subtitle_dir = Path(subtitle_file).parent
                
                # 检查是否同名且在同一目录或子目录
                if (subtitle_stem == video_stem or 
                    subtitle_stem.startswith(video_stem + '.') or
                    video_stem.startswith(subtitle_stem + '.')):
                    # 检查目录关系
                    try:
                        video_dir.relative_to(subtitle_dir)
                        matching_subtitles.append(subtitle_file)
                    except ValueError:
                        try:
                            subtitle_dir.relative_to(video_dir)
                            matching_subtitles.append(subtitle_file)
                        except ValueError:
                            if video_dir == subtitle_dir:
                                matching_subtitles.append(subtitle_file)
            
            # 选择最佳匹配的字幕
            if matching_subtitles:
                # 优先选择完全同名的
                best_match = None
                for subtitle in matching_subtitles:
                    if Path(subtitle).stem == video_stem:
                        best_match = subtitle
                        break
                
                if not best_match:
                    best_match = matching_subtitles[0]
                
                pairs.append((video_file, best_match))
        
        return pairs
    
    def batch_merge(
        self, 
        directory: str, 
        output_suffix: str = "_with_subtitles",
        force_style: str = None,
        dry_run: bool = False
    ) -> bool:
        """
        批量合成视频字幕
        
        Args:
            directory: 处理目录
            output_suffix: 输出文件后缀
            force_style: 强制字幕样式
            dry_run: 仅显示将要处理的文件，不实际处理
            
        Returns:
            是否全部成功
        """
        self.logger.info(f"开始批量处理目录: {directory}")
        
        # 查找视频字幕对
        pairs = self.find_video_subtitle_pairs(directory)
        
        if not pairs:
            self.logger.warning("未找到任何视频字幕文件对")
            return False
        
        self.logger.info(f"找到 {len(pairs)} 个视频字幕文件对")
        
        if dry_run:
            print("\n=== 预览模式 - 将要处理的文件 ===")
            for i, (video, subtitle) in enumerate(pairs, 1):
                video_name = os.path.basename(video)
                subtitle_name = os.path.basename(subtitle)
                output_name = Path(video).stem + output_suffix + Path(video).suffix
                
                print(f"{i}. 视频: {video_name}")
                print(f"   字幕: {subtitle_name}")
                print(f"   输出: {output_name}")
                print()
            
            print(f"总计: {len(pairs)} 个文件对")
            return True
        
        # 实际处理
        success_count = 0
        failed_files = []
        
        for i, (video_file, subtitle_file) in enumerate(pairs, 1):
            try:
                self.logger.info(f"处理 {i}/{len(pairs)}: {os.path.basename(video_file)}")
                
                # 生成输出文件名
                video_path = Path(video_file)
                output_file = str(video_path.parent / f"{video_path.stem}{output_suffix}{video_path.suffix}")
                
                # 检查输出文件是否已存在
                if os.path.exists(output_file):
                    self.logger.warning(f"输出文件已存在，跳过: {os.path.basename(output_file)}")
                    continue
                
                # 执行合成
                self.merger.merge_video_subtitle(
                    video_file,
                    subtitle_file,
                    output_file,
                    force_style
                )
                
                success_count += 1
                self.logger.info(f"✅ 完成: {os.path.basename(output_file)}")
                
            except Exception as e:
                self.logger.error(f"❌ 处理失败: {os.path.basename(video_file)} - {e}")
                failed_files.append(video_file)
        
        # 输出结果统计
        self.logger.info(f"\n=== 批量处理完成 ===")
        self.logger.info(f"成功: {success_count}/{len(pairs)}")
        
        if failed_files:
            self.logger.error(f"失败: {len(failed_files)} 个文件")
            for failed_file in failed_files:
                self.logger.error(f"  - {os.path.basename(failed_file)}")
        
        return len(failed_files) == 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="批量FFmpeg视频字幕合成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python batch_merger.py "C:\\测试视频合成"                    # 批量处理目录
  python batch_merger.py "C:\\测试视频合成" --dry-run          # 预览模式
  python batch_merger.py "C:\\测试视频合成" --suffix "_硬字幕"   # 自定义输出后缀
        """
    )
    
    parser.add_argument('directory', help='要处理的目录路径')
    parser.add_argument(
        '--suffix',
        default='_with_subtitles',
        help='输出文件后缀 (默认: _with_subtitles)'
    )
    parser.add_argument(
        '--force-style',
        help='强制字幕样式'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='日志级别'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式，仅显示将要处理的文件'
    )
    
    args = parser.parse_args()
    
    # 检查目录是否存在
    if not os.path.exists(args.directory):
        print(f"❌ 目录不存在: {args.directory}")
        sys.exit(1)
    
    try:
        batch_merger = BatchSubtitleMerger(args.log_level)
        success = batch_merger.batch_merge(
            args.directory,
            args.suffix,
            args.force_style,
            args.dry_run
        )
        
        if success:
            print("\n🎉 批量处理完成!")
        else:
            print("\n⚠️ 批量处理完成，但有部分文件处理失败")
            
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(130)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
