#!/usr/bin/env python3
"""
FFmpeg视频字幕合成工具 - 中文图形界面
"""

import os
import sys
import subprocess
from pathlib import Path


def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


def show_menu():
    """显示主菜单"""
    clear_screen()
    print("=" * 50)
    print("    FFmpeg视频字幕合成工具")
    print("=" * 50)
    print()
    print("请选择操作：")
    print()
    print("1. 运行完整测试")
    print("2. 设置测试环境")
    print("3. 处理单个视频文件")
    print("4. 批量处理目录")
    print("5. 检查系统环境")
    print("6. 安装/更新依赖")
    print("0. 退出")
    print()


def check_system():
    """检查系统环境"""
    clear_screen()
    print("=" * 50)
    print("检查系统环境")
    print("=" * 50)
    print()
    
    # 检查Python
    try:
        result = subprocess.run(['python', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Python已安装: {result.stdout.strip()}")
        else:
            print("❌ Python未安装或不在PATH中")
    except FileNotFoundError:
        print("❌ Python未安装或不在PATH中")
    
    # 检查FFmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg已安装: {version_line}")
        else:
            print("❌ FFmpeg未安装或不在PATH中")
    except FileNotFoundError:
        print("❌ FFmpeg未安装或不在PATH中")
    
    # 检查Python依赖
    print()
    print("检查Python依赖...")
    try:
        import ffmpeg
        print("✅ ffmpeg-python已安装")
    except ImportError:
        print("❌ ffmpeg-python未安装")
    
    print()
    input("按回车键返回主菜单...")


def install_dependencies():
    """安装依赖"""
    clear_screen()
    print("=" * 50)
    print("安装/更新依赖")
    print("=" * 50)
    print()
    
    print("正在安装Python依赖...")
    try:
        result = subprocess.run(['pip', 'install', '-r', 'requirements.txt'], 
                              capture_output=False, text=True)
        if result.returncode == 0:
            print("✅ 依赖安装成功")
        else:
            print("❌ 依赖安装失败")
    except Exception as e:
        print(f"❌ 安装过程中出错: {e}")
    
    print()
    input("按回车键返回主菜单...")


def setup_environment():
    """设置测试环境"""
    clear_screen()
    print("=" * 50)
    print("设置测试环境")
    print("=" * 50)
    print()
    
    try:
        subprocess.run(['python', 'test_merger.py', '--setup-only'], 
                      capture_output=False, text=True)
    except Exception as e:
        print(f"❌ 设置过程中出错: {e}")
    
    print()
    input("按回车键返回主菜单...")


def run_test():
    """运行完整测试"""
    clear_screen()
    print("=" * 50)
    print("运行完整测试")
    print("=" * 50)
    print()
    
    try:
        subprocess.run(['python', 'test_merger.py'], 
                      capture_output=False, text=True)
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
    
    print()
    input("按回车键返回主菜单...")


def process_single_file():
    """处理单个文件"""
    clear_screen()
    print("=" * 50)
    print("处理单个视频文件")
    print("=" * 50)
    print()

    print("请输入文件路径（可以拖拽文件到窗口）：")
    print()

    video_file = input("视频文件路径: ").strip().strip('"')
    if not video_file:
        print("未输入视频文件路径")
        input("按回车键返回主菜单...")
        return

    subtitle_file = input("字幕文件路径: ").strip().strip('"')
    if not subtitle_file:
        print("未输入字幕文件路径")
        input("按回车键返回主菜单...")
        return

    # 自定义后缀选项
    print()
    print("输出文件后缀选项：")
    print("1. 使用默认后缀 '_with_subtitles'")
    print("2. 自定义后缀")
    print("3. 手动指定完整输出路径")
    print()

    suffix_choice = input("请选择 (1-3): ").strip()

    output_file = ""
    if suffix_choice == "1":
        # 默认后缀
        output_file = str(Path(video_file).with_suffix('')) + '_with_subtitles.mp4'
    elif suffix_choice == "2":
        # 自定义后缀
        custom_suffix = input("请输入自定义后缀 (例如: _硬字幕, _中文字幕): ").strip()
        if not custom_suffix:
            custom_suffix = "_with_subtitles"
        output_file = str(Path(video_file).with_suffix('')) + custom_suffix + '.mp4'
    elif suffix_choice == "3":
        # 手动指定完整路径
        output_file = input("请输入完整输出文件路径: ").strip().strip('"')
        if not output_file:
            output_file = str(Path(video_file).with_suffix('')) + '_with_subtitles.mp4'
    else:
        # 默认处理
        output_file = str(Path(video_file).with_suffix('')) + '_with_subtitles.mp4'

    print()
    print(f"输出文件: {output_file}")
    print("正在处理...")

    try:
        cmd = ['python', 'ffmpeg_subtitle_merger.py', video_file, subtitle_file, output_file]
        subprocess.run(cmd, capture_output=False, text=True)
        print("✅ 处理完成")
    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")

    print()
    input("按回车键返回主菜单...")


def batch_process():
    """批量处理"""
    clear_screen()
    print("=" * 50)
    print("批量处理目录")
    print("=" * 50)
    print()

    batch_dir = input("请输入目录路径: ").strip().strip('"')
    if not batch_dir:
        print("未输入目录路径")
        input("按回车键返回主菜单...")
        return

    print()
    print("选择处理模式：")
    print("1. 预览模式 (仅显示将要处理的文件)")
    print("2. 实际处理")
    print()

    mode = input("请选择 (1-2): ").strip()

    # 如果是实际处理，询问后缀选项
    custom_suffix = ""
    if mode == "2":
        print()
        print("输出文件后缀选项：")
        print("1. 使用默认后缀 '_with_subtitles'")
        print("2. 自定义后缀")
        print()

        suffix_choice = input("请选择 (1-2): ").strip()

        if suffix_choice == "2":
            custom_suffix = input("请输入自定义后缀 (例如: _硬字幕, _中文字幕): ").strip()
            if not custom_suffix:
                custom_suffix = "_with_subtitles"
        else:
            custom_suffix = "_with_subtitles"

    print()

    try:
        if mode == "1":
            print("预览模式...")
            if custom_suffix and custom_suffix != "_with_subtitles":
                subprocess.run(['python', 'batch_merger.py', batch_dir, '--dry-run', '--suffix', custom_suffix],
                              capture_output=False, text=True)
            else:
                subprocess.run(['python', 'batch_merger.py', batch_dir, '--dry-run'],
                              capture_output=False, text=True)
        elif mode == "2":
            print(f"开始处理... (使用后缀: {custom_suffix})")
            if custom_suffix and custom_suffix != "_with_subtitles":
                subprocess.run(['python', 'batch_merger.py', batch_dir, '--suffix', custom_suffix],
                              capture_output=False, text=True)
            else:
                subprocess.run(['python', 'batch_merger.py', batch_dir],
                              capture_output=False, text=True)
        else:
            print("无效选项")
    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")

    print()
    input("按回车键返回主菜单...")


def main():
    """主函数"""
    while True:
        show_menu()
        
        choice = input("请输入选项 (0-6): ").strip()
        
        if choice == "0":
            print()
            print("感谢使用！")
            break
        elif choice == "1":
            run_test()
        elif choice == "2":
            setup_environment()
        elif choice == "3":
            process_single_file()
        elif choice == "4":
            batch_process()
        elif choice == "5":
            check_system()
        elif choice == "6":
            install_dependencies()
        else:
            print()
            print("无效选项，请重新选择")
            input("按回车键继续...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
    except Exception as e:
        print(f"\n程序出错: {e}")
        input("按回车键退出...")
