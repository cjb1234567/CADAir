"""示例7: 列出所有可用翻译引擎"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dwgtranslator import TranslationEngineFactory
from dwgtranslator.plugins import baidu  # 确保插件加载


def main():
    print("=" * 50)
    print("  示例7: 可用翻译引擎")
    print("=" * 50)
    
    engines = TranslationEngineFactory.list_engines()
    
    for name in engines:
        print(f"  ✓ {name}")
    
    print("\n使用方式:")
    print("""
    from dwgtranslator import TranslationEngineFactory
    
    # 创建百度领域翻译
    baidu = TranslationEngineFactory.create(
        'baidu_field', 
        app_id='xxx',
        app_key='yyy',
        domain='machinery'
    )
    
    # 创建模拟翻译
    mock = TranslationEngineFactory.create('mock', prefix='[译]')
    """)


if __name__ == "__main__":
    main()
