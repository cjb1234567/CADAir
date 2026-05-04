"""示例5: 使用百度翻译API"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dwgtranslator import TranslationManager, TranslationEngineFactory


def main():
    print("=" * 50)
    print("  示例5: 百度翻译API")
    print("=" * 50)
    
    # 确保百度插件已加载
    from dwgtranslator.plugins.baidu import BaiduFieldTranslator
    
    print(f"可用引擎: {TranslationEngineFactory.list_engines()}")
    print("\n请先申请API: https://fanyi-api.baidu.com/")
    
    # 使用工厂创建
    try:
        baidu = TranslationEngineFactory.create(
            'baidu_field',
            app_id=input("请输入APP ID: ").strip(),
            app_key=input("请输入密钥: ").strip(),
            domain=input("领域 (默认machinery): ").strip() or "machinery"
        )
        
        manager = TranslationManager()
        manager.set_translator(baidu)
        manager.translate_file(
            "data/20260123.dwg", 
            "data/output_baidu.dxf"
        )
        print("百度翻译完成: data/output_baidu.dxf")
        
    except ImportError as e:
        print(f"\n提示: {e}")
    except Exception as e:
        print(f"\n错误: {e}")


if __name__ == "__main__":
    main()
