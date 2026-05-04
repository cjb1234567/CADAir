"""示例6: 自定义翻译函数"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dwgtranslator import TranslationManager


def my_translator(text, target_lang):
    """
    自定义翻译函数
    在这里接入任意翻译API: DeepL, Google, 有道, etc.
    """
    translations = {
        "en": {"挡板": "baffle", "技术要求": "Technical Requirements"},
        "zh": {"baffle": "挡板", "Technical Requirements": "技术要求"}
    }
    
    result = translations.get(target_lang, {}).get(text, f"✨{text}")
    return result


def main():
    print("=" * 50)
    print("  示例6: 自定义翻译函数")
    print("=" * 50)
    
    manager = TranslationManager()
    manager.translate_file(
        "data/20260123.dwg",
        "data/output_custom.dxf",
        custom_translator=my_translator
    )
    print("自定义翻译完成: data/output_custom.dxf")


if __name__ == "__main__":
    main()
