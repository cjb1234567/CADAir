"""示例8: 百度异步翻译API - 支持并发控制和QPS限制"""
import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from dwgtranslator import TranslationManager, TranslationEngineFactory
from dwgtranslator.plugins.baidu import AsyncBaiduGeneralTranslator, AsyncBaiduFieldTranslator

print(f"当前工作目录: {os.getcwd()}")
async def async_translate_demo(args):
    """异步翻译演示"""
    print("=" * 50)
    print("  示例8: 百度异步翻译API (并发+限流)")
    print("=" * 50)
    
    engines = TranslationEngineFactory.list_engines()
    async_engines = [e for e in engines 
                     if hasattr(TranslationEngineFactory._engines[e], 'translate_async')]
    print(f"可用异步引擎: {async_engines}")
    
    # Load from environment variables first
    app_id = os.getenv("APP_ID", "")
    app_key = os.getenv("SEC_KEY", "")
    oda_path = os.getenv("ODA_PATH")
    domain = os.getenv("TRANSLATE_DOMAIN", "machinery")
    qps = float(os.getenv("TRANSLATE_QPS", "5"))
    target_lang = os.getenv("TRANSLATE_TARGET", "en")
    source_lang = os.getenv("TRANSLATE_SOURCE", "auto")
    use_general = os.getenv("TRANSLATE_USE_GENERAL", "y").lower() == "y"
    glossary_json = args.glossary_json or os.getenv("GLOSSARY_JSON")
    glossary_file = args.glossary_file or os.getenv("GLOSSARY_FILE")
    
    # Fallback to input if not set
    if not oda_path:
        oda_path = input("请输入ODA File Converter路径: ").strip()
    if not oda_path:
        print("[错误] 必须指定ODA File Converter路径！")
        return
    
    if not app_id:
        app_id = input("\n请输入APP ID: ").strip()
    if not app_id:
        print("[错误] 必须提供百度翻译APP ID！")
        print("可以从: https://fanyi-api.baidu.com/ 获取")
        return
    
    if not app_key:
        app_key = input("请输入密钥: ").strip()
    if not app_key:
        print("[错误] 必须提供百度翻译密钥！")
        return
    
    print(f"已加载配置: APP_ID={'*' * len(app_id) if app_id else '(未设置)'}")
    print(f"ODA路径: {oda_path}")
    print(f"翻译方向: {source_lang.upper()} → {target_lang.upper()}")
    print(f"QPS限制: {qps}")
    
    if use_general:
        print("使用通用翻译API")
        baidu = AsyncBaiduGeneralTranslator(
            app_id=app_id,
            app_key=app_key,
            max_concurrent=1,
            requests_per_second=qps
        )
    else:
        print(f"使用领域翻译API (domain={domain})")
        baidu = AsyncBaiduFieldTranslator(
            app_id=app_id,
            app_key=app_key,
            domain=domain,
            max_concurrent=1,
            requests_per_second=qps
        )
    
    manager = TranslationManager(
        oda_path=oda_path,
        glossary_json=glossary_json,
        glossary_file=glossary_file,
    )
    manager.set_translator(baidu)
    
    # 使用命令行参数指定文件，或使用默认
    if args.input_file:
        input_file = args.input_file
    else:
        # 默认路径
        input_file = "data/lineweights.sample.dwg"
    
    if not os.path.exists(input_file):
        print(f"错误: 文件不存在: {input_file}")
        print("请将DWG文件放到 data/ 文件夹，或通过命令行参数指定路径")
        print("用法: python examples/baidu_async_translate.py [path/to/file.dwg]")
        return
    
    output_file = input_file.replace(".dwg", "_translated.dxf").replace(".dxf", "_translated.dxf")
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")
    
    result = await manager.translate_file_async(
        input_file,
        output_file,
        target_lang=target_lang,
        source_lang=source_lang
    )
    
    print(f"百度异步翻译完成: {result}")
    print(f"输出文件: {output_file}")
    print(f"翻译方向: {source_lang.upper()} → {target_lang.upper()}")


def main():
    parser = argparse.ArgumentParser(description="Translate a DWG/DXF file with Baidu async API")
    parser.add_argument("input_file", nargs="?", help="Input DWG/DXF file path")
    parser.add_argument(
        "--glossary-json",
        help="Glossary terms as JSON list/object or comma-separated text, e.g. '[\"ODF\",\"PDU\"]'",
    )
    parser.add_argument("--glossary-file", help="Path to a glossary JSON file")
    asyncio.run(async_translate_demo(parser.parse_args()))


if __name__ == "__main__":
    main()
