"""示例2: 使用模拟翻译引擎 - 支持自定义词典"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dwgtranslator import TranslationManager, MockTranslator


def main():
    print("=" * 50)
    print("  示例2: 模拟翻译引擎 (自定义词典)")
    print("=" * 50)
    
    manager = TranslationManager()
    
    # 使用模拟翻译引擎，可自定义词典
    manager.set_translator(MockTranslator(
        prefix="[机翻]",
        translations={
            "baffle": "挡板",
            "Technical Requirements": "技术要求",
            "Material": "材料",
            "Dimension": "尺寸",
            "Drawing": "图纸",
            "Remarks": "备注",
            "Quantity": "数量",
            "Scale": "比例",
            "Weight": "重量"
        }
    ))
    
    manager.translate_file("data/20260123.dwg", "data/output_mock.dxf")
    print("自定义词典翻译完成")
    print("输出文件: data/output_mock.dxf")


if __name__ == "__main__":
    main()
