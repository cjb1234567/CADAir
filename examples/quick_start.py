"""示例1: 快速开始 - 一行代码完成翻译"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dwgtranslator import TranslationManager


def main():
    print("=" * 50)
    print("  示例1: 快速开始")
    print("=" * 50)
    
    manager = TranslationManager()
    result = manager.translate_file("data/20260123.dwg", "data/output.dxf")
    
    print(f"翻译完成: {result}")
    print("输出文件: data/output.dxf")


if __name__ == "__main__":
    main()
