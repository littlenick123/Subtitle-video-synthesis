#!/usr/bin/env python3
"""
FFmpeg字幕合成工具测试脚本
支持测试真实视频文件和自动生成测试文件
"""

import os
import sys
import tempfile
import subprocess
import glob
from pathlib import Path

def create_test_video(output_path: str, duration: int = 5) -> bool:
    """
    创建测试视频文件
    
    Args:
        output_path: 输出路径
        duration: 视频时长（秒）
        
    Returns:
        是否创建成功
    """
    try:
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', f'testsrc=duration={duration}:size=1280x720:rate=25',
            '-f', 'lavfi', 
            '-i', 'sine=frequency=1000:duration=5',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-shortest',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
        
    except Exception as e:
        print(f"创建测试视频失败: {e}")
        return False

def create_test_subtitle(output_path: str) -> bool:
    """
    创建测试字幕文件
    
    Args:
        output_path: 输出路径
        
    Returns:
        是否创建成功
    """
    try:
        subtitle_content = """[Script Info]
Title: Test Subtitle
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,测试字幕 1
Dialogue: 0,0:00:03.50,0:00:05.00,Default,,0,0,0,,测试字幕 2
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(subtitle_content)
        return True
        
    except Exception as e:
        print(f"创建测试字幕失败: {e}")
        return False

def find_test_videos(test_dir: str) -> list:
    """
    在指定目录中查找测试视频文件

    Args:
        test_dir: 测试目录路径

    Returns:
        视频文件路径列表
    """
    video_extensions = ['*.mp4', '*.avi', '*.mkv', '*.mov', '*.mps', '*.ts', '*.m2ts']
    video_files = []

    if os.path.exists(test_dir):
        for ext in video_extensions:
            pattern = os.path.join(test_dir, ext)
            video_files.extend(glob.glob(pattern))
            # 也搜索子目录
            pattern = os.path.join(test_dir, '**', ext)
            video_files.extend(glob.glob(pattern, recursive=True))

    return video_files

def find_test_subtitles(test_dir: str) -> list:
    """
    在指定目录中查找测试字幕文件

    Args:
        test_dir: 测试目录路径

    Returns:
        字幕文件路径列表
    """
    subtitle_extensions = ['*.ass', '*.srt', '*.vtt', '*.sub']
    subtitle_files = []

    if os.path.exists(test_dir):
        for ext in subtitle_extensions:
            pattern = os.path.join(test_dir, ext)
            subtitle_files.extend(glob.glob(pattern))
            # 也搜索子目录
            pattern = os.path.join(test_dir, '**', ext)
            subtitle_files.extend(glob.glob(pattern, recursive=True))

    return subtitle_files

def test_with_real_files(test_dir: str) -> bool:
    """
    使用真实文件进行测试

    Args:
        test_dir: 测试目录路径

    Returns:
        测试是否成功
    """
    print(f"\n=== 使用真实文件测试 (目录: {test_dir}) ===")

    # 查找视频和字幕文件
    video_files = find_test_videos(test_dir)
    subtitle_files = find_test_subtitles(test_dir)

    print(f"找到 {len(video_files)} 个视频文件")
    print(f"找到 {len(subtitle_files)} 个字幕文件")

    if not video_files:
        print("❌ 未找到视频文件")
        return False

    if not subtitle_files:
        print("⚠️ 未找到字幕文件，将创建测试字幕")
        # 创建测试字幕
        test_subtitle = os.path.join(test_dir, "test_subtitle.ass")
        if not create_test_subtitle(test_subtitle):
            print("❌ 创建测试字幕失败")
            return False
        subtitle_files = [test_subtitle]

    # 选择第一个视频和字幕文件进行测试
    test_video = video_files[0]
    test_subtitle = subtitle_files[0]

    print(f"测试视频: {os.path.basename(test_video)}")
    print(f"测试字幕: {os.path.basename(test_subtitle)}")

    # 生成输出文件名
    video_name = Path(test_video).stem
    output_video = os.path.join(test_dir, f"{video_name}_with_subtitles.mp4")

    try:
        from ffmpeg_subtitle_merger import FFmpegSubtitleMerger

        merger = FFmpegSubtitleMerger(log_level='INFO')

        # 验证输入文件
        print("验证输入文件...")
        merger.validate_inputs(test_video, test_subtitle)
        print("✅ 输入文件验证通过")

        # 获取视频信息
        print("获取视频信息...")
        video_info = merger.probe_video_info(test_video)
        print(f"✅ 视频信息: {video_info['width']}x{video_info['height']} @ {video_info['fps']:.2f}fps")
        print(f"   编码器: {video_info['codec']}, 码率: {video_info['bitrate']} bps")

        # 检查NVIDIA支持
        print("检查NVIDIA支持...")
        nvenc_support = merger.check_nvidia_support()
        print(f"✅ NVIDIA编码支持: {'是' if nvenc_support else '否'}")

        # 执行合成
        print("执行字幕合成...")
        merger.merge_video_subtitle(
            test_video,
            test_subtitle,
            output_video
        )

        # 验证输出
        if os.path.exists(output_video) and os.path.getsize(output_video) > 0:
            output_size = os.path.getsize(output_video)
            print(f"✅ 字幕合成成功!")
            print(f"   输出文件: {output_video}")
            print(f"   文件大小: {output_size:,} bytes")
            return True
        else:
            print("❌ 输出文件创建失败")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_merger(test_dir: str = None):
    """测试字幕合成工具"""
    print("=== FFmpeg字幕合成工具测试 ===")

    # 检查FFmpeg是否可用
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
        if result.returncode != 0:
            print("❌ FFmpeg不可用")
            return False
        print("✅ FFmpeg可用")
    except FileNotFoundError:
        print("❌ FFmpeg未安装或不在PATH中")
        return False

    # 用户指定的测试目录
    user_test_dir = test_dir or r"C:\Users\Nickxxx\Desktop\测试视频合成"

    # 首先尝试使用真实文件测试
    if os.path.exists(user_test_dir):
        success = test_with_real_files(user_test_dir)
        if success:
            return True
        print("真实文件测试失败，继续使用生成的测试文件...")
    else:
        print(f"指定目录不存在: {user_test_dir}")
        print("将创建目录并使用生成的测试文件...")

        # 尝试创建测试目录
        try:
            os.makedirs(user_test_dir, exist_ok=True)
            print(f"✅ 创建测试目录: {user_test_dir}")
        except Exception as e:
            print(f"⚠️ 无法创建测试目录: {e}")
            user_test_dir = tempfile.mkdtemp()
            print(f"使用临时目录: {user_test_dir}")

    # 使用生成的测试文件
    print(f"\n=== 使用生成的测试文件 ===")
    test_video = os.path.join(user_test_dir, "test_video.mp4")
    test_subtitle = os.path.join(user_test_dir, "test_subtitle.ass")
    output_video = os.path.join(user_test_dir, "output_video.mp4")

    print(f"测试目录: {user_test_dir}")

    # 创建测试文件
    print("创建测试视频...")
    if not create_test_video(test_video):
        print("❌ 创建测试视频失败")
        return False
    print("✅ 测试视频创建成功")

    print("创建测试字幕...")
    if not create_test_subtitle(test_subtitle):
        print("❌ 创建测试字幕失败")
        return False
    print("✅ 测试字幕创建成功")

    # 测试工具
    print("测试字幕合成工具...")
    try:
        from ffmpeg_subtitle_merger import FFmpegSubtitleMerger

        merger = FFmpegSubtitleMerger(log_level='INFO')

        # 首先进行检查
        print("验证输入文件...")
        merger.validate_inputs(test_video, test_subtitle)
        print("✅ 输入文件验证通过")

        # 获取视频信息
        print("获取视频信息...")
        video_info = merger.probe_video_info(test_video)
        print(f"✅ 视频信息: {video_info['width']}x{video_info['height']} @ {video_info['fps']:.2f}fps")

        # 检查NVIDIA支持
        print("检查NVIDIA支持...")
        nvenc_support = merger.check_nvidia_support()
        print(f"✅ NVIDIA编码支持: {'是' if nvenc_support else '否'}")

        # 执行合成
        print("执行字幕合成...")
        merger.merge_video_subtitle(
            test_video,
            test_subtitle,
            output_video
        )

        # 验证输出
        if os.path.exists(output_video) and os.path.getsize(output_video) > 0:
            output_size = os.path.getsize(output_video)
            print(f"✅ 字幕合成成功!")
            print(f"   输出文件: {output_video}")
            print(f"   文件大小: {output_size:,} bytes")
            return True
        else:
            print("❌ 输出文件创建失败")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def setup_test_environment():
    """设置测试环境"""
    test_dir = r"C:\Users\Nickxxx\Desktop\测试视频合成"

    print(f"=== 设置测试环境 ===")
    print(f"测试目录: {test_dir}")

    # 创建测试目录
    try:
        os.makedirs(test_dir, exist_ok=True)
        print(f"✅ 测试目录已创建/存在")
    except Exception as e:
        print(f"❌ 无法创建测试目录: {e}")
        return False

    # 检查是否已有测试文件
    video_files = find_test_videos(test_dir)
    subtitle_files = find_test_subtitles(test_dir)

    if video_files:
        print(f"✅ 找到 {len(video_files)} 个现有视频文件")
        for video in video_files[:3]:  # 只显示前3个
            print(f"   - {os.path.basename(video)}")
        if len(video_files) > 3:
            print(f"   ... 还有 {len(video_files) - 3} 个文件")

    if subtitle_files:
        print(f"✅ 找到 {len(subtitle_files)} 个现有字幕文件")
        for subtitle in subtitle_files[:3]:  # 只显示前3个
            print(f"   - {os.path.basename(subtitle)}")
        if len(subtitle_files) > 3:
            print(f"   ... 还有 {len(subtitle_files) - 3} 个文件")

    # 如果没有测试文件，创建一些
    if not video_files:
        print("创建示例视频文件...")
        test_video = os.path.join(test_dir, "sample_video.mp4")
        if create_test_video(test_video, duration=10):
            print(f"✅ 创建示例视频: {os.path.basename(test_video)}")
        else:
            print("❌ 创建示例视频失败")

    if not subtitle_files:
        print("创建示例字幕文件...")
        test_subtitle = os.path.join(test_dir, "sample_subtitle.ass")
        if create_test_subtitle(test_subtitle):
            print(f"✅ 创建示例字幕: {os.path.basename(test_subtitle)}")
        else:
            print("❌ 创建示例字幕失败")

    return True

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="FFmpeg字幕合成工具测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python test_merger.py                    # 运行完整测试
  python test_merger.py --setup-only      # 仅设置测试环境
  python test_merger.py --test-dir "路径"  # 指定测试目录
        """
    )

    parser.add_argument(
        '--setup-only',
        action='store_true',
        help='仅设置测试环境，不运行测试'
    )

    parser.add_argument(
        '--test-dir',
        default=r"C:\Users\Nickxxx\Desktop\测试视频合成",
        help='指定测试目录路径'
    )

    args = parser.parse_args()

    if args.setup_only:
        success = setup_test_environment()
        if success:
            print("\n🎉 测试环境设置完成!")
            print(f"请将您的视频和字幕文件放入: {args.test_dir}")
            print("然后运行: python test_merger.py")
        else:
            print("\n❌ 测试环境设置失败!")
        sys.exit(0 if success else 1)

    # 设置环境并运行测试
    print("正在设置测试环境...")
    setup_success = setup_test_environment()

    if not setup_success:
        print("❌ 测试环境设置失败!")
        sys.exit(1)

    print("\n正在运行测试...")
    success = test_merger(args.test_dir)

    if success:
        print("\n🎉 所有测试通过!")
        print(f"测试文件位于: {args.test_dir}")
        sys.exit(0)
    else:
        print("\n❌ 测试失败!")
        sys.exit(1)

if __name__ == "__main__":
    main()
