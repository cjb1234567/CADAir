"""完整翻译流程测试"""
import os
import sys
sys.path.insert(0, os.getcwd())

import asyncio
from dotenv import load_dotenv
load_dotenv()

os.environ['XDG_RUNTIME_DIR'] = '/tmp/runtime-chongjibo'
os.makedirs('/tmp/runtime-chongjibo', exist_ok=True)

from dwgtranslator import TranslationManager, AsyncBaiduGeneralTranslator

async def main():
    print("=" * 60)
    print("完整翻译流程测试（DWG -> 翻译 -> DXF）")
    print("=" * 60)
    
    oda_path = os.getenv("ODA_PATH")
    app_id = os.getenv("APP_ID")
    app_key = os.getenv("SEC_KEY")
    
    manager = TranslationManager(oda_path=oda_path)
    
    # 测试翻译
    translator = AsyncBaiduGeneralTranslator(
        app_id=app_id,
        app_key=app_key,
        max_concurrent=1,
        requests_per_second=0.3
    )
    manager.set_translator(translator)
    
    output_file = "data/20260123_translated.dxf"
    
    print("\n开始翻译DWG文件...")
    result = await manager.translate_file_async(
        "data/20260123.dwg",
        output_file,
        target_lang="en",
        source_lang="zh"
    )
    
    if result:
        print(f"\n✓ 翻译完成！输出文件: {output_file}")
        
        # 验证翻译结果
        import ezdxf
        doc = ezdxf.readfile(output_file)
        
        print(f"\n翻译验证（块内文本前5条）:")
        count = 0
        for block in doc.blocks:
            for entity in block:
                if entity.dxftype() == 'TEXT':
                    txt = entity.dxf.text
                    if any('\u4e00' <= c <= '\u9fff' for c in str(txt)):
                        print(f"  ⚠ 还有中文: {txt}")
                        count += 1
                        if count >= 5:
                            break
            if count >= 5:
                break
        
        if count == 0:
            print("  ✓ 没有发现中文文本，翻译成功！")
    else:
        print("✗ 翻译失败")

if __name__ == "__main__":
    import subprocess
    
    # 用xvfb-run运行
    subprocess.run([
        'xvfb-run', '-a',
        sys.executable, '-c',
        '''
import os
import sys
sys.path.insert(0, os.getcwd())

import asyncio
from dotenv import load_dotenv
load_dotenv()

os.environ['XDG_RUNTIME_DIR'] = '/tmp/runtime-chongjibo'
os.makedirs('/tmp/runtime-chongjibo', exist_ok=True)

from dwgtranslator import TranslationManager, AsyncBaiduGeneralTranslator

async def main():
    oda_path = os.getenv("ODA_PATH")
    app_id = os.getenv("APP_ID")
    app_key = os.getenv("SEC_KEY")
    
    manager = TranslationManager(oda_path=oda_path)
    
    translator = AsyncBaiduGeneralTranslator(
        app_id=app_id,
        app_key=app_key,
        max_concurrent=1,
        requests_per_second=0.3
    )
    manager.set_translator(translator)
    
    output_file = "data/20260123_translated.dxf"
    
    print("开始翻译DWG文件...")
    result = await manager.translate_file_async(
        "data/20260123.dwg",
        output_file,
        target_lang="en",
        source_lang="zh"
    )
    
    if result:
        print(f"\\n✓ 翻译完成！输出文件: {output_file}")
    else:
        print("✗ 翻译失败")

asyncio.run(main())
'''
    ])

