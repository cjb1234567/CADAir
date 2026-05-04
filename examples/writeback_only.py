"""示例4: 仅写回已翻译的JSON"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dwgtranslator import TranslationManager


def main():
    print("=" * 50)
    print("  示例4: 写回人工翻译结果")
    print("=" * 50)
    
    # 先检查是否有翻译文件
    import os
    if not os.path.exists("data/translation_work.json"):
        print("未找到翻译文件，请先运行: python examples/extract_only.py")
        return
    
    manager = TranslationManager()
    result = manager.writeback_only(
        input_path="data/20260123.dwg",
        translated_json="data/translation_work.json",
        output_path="data/final_output.dxf"
    )
    
    print(f"写回完成: {result}")
    print("输出文件: data/final_output.dxf")


if __name__ == "__main__":
    main()
