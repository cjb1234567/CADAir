"""示例3: 仅提取文本供人工翻译"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dwgtranslator import TranslationManager


def main():
    print("=" * 50)
    print("  示例3: 提取文本供人工翻译")
    print("=" * 50)
    
    manager = TranslationManager()
    bundles = manager.extract_only(
        "data/20260123.dwg", 
        "data/translation_work.json"
    )
    
    print(f"\n已提取 {len(bundles)} 条文本")
    print("请编辑: data/translation_work.json")
    print("为每条记录添加 'translated' 字段")
    print("然后运行: python examples/writeback_only.py")


if __name__ == "__main__":
    main()
