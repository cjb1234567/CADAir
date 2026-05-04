"""百度翻译API真实请求测试
直接调用百度API验证签名和功能正确性
"""
import sys
import os
import asyncio
from getpass import getpass

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保UTF-8编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(test_name, success, message=""):
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} {test_name}")
    if message:
        print(f"       {message}")


async def test_field_translation(app_id, app_key):
    """测试领域翻译API - 直接打印API响应看错误码"""
    print_header("测试1: 领域翻译API")
    
    import aiohttp
    
    # 手动发起请求，查看完整响应
    url = "https://fanyi-api.baidu.com/api/trans/vip/fieldtranslate"
    import hashlib
    import random
    
    domain = "machinery"
    text = "hello"
    salt = str(random.randint(32768, 65536))
    sign = hashlib.md5(f"{app_id}{text}{salt}{domain}{app_key}".encode()).hexdigest()
    
    params = {
        'q': text, 'from': 'en', 'to': 'zh',
        'appid': app_id, 'salt': salt, 'sign': sign,
        'domain': domain
    }
    
    print(f"       请求URL: {url}")
    print(f"       domain: {domain}")
    print(f"       文本: {text}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=params, timeout=10) as resp:
            result = await resp.json()
            print(f"       API响应: {result}")
    
    if 'error_code' in result and result['error_code'] != '52000':
        msg = f"错误码: {result.get('error_code')}, 信息: {result.get('error_msg')}"
        if result['error_code'] == '54001':
            msg += " (签名错误，请检查签名公式)"
        elif result['error_code'] == '58003':
            msg += " (未开通领域翻译服务，请去百度翻译后台开通)"
        return False, msg
    
    return True, "领域翻译API正常"
    
    return all_pass, "领域翻译API正常" if all_pass else "部分翻译失败"


async def test_general_translation(app_id, app_key):
    """测试通用翻译API"""
    print_header("测试2: 通用翻译API")
    
    from dwgtranslator.plugins.baidu import BaiduGeneralTranslator
    
    translator = BaiduGeneralTranslator(app_id, app_key)
    
    test_cases = [
        ("hello world", "en", "zh"),
        ("CAD drawing", "en", "zh"),
        ("机械图纸", "zh", "en"),
    ]
    
    all_pass = True
    for text, from_lang, to_lang in test_cases:
        result = await translator.translate_async(text, from_lang, to_lang)
        success = result != text and "error" not in result.lower()
        all_pass = all_pass and success
        print(f"       {text} → {result}")
    
    # 关闭session避免警告
    if translator._session and not translator._session.closed:
        await translator._session.close()
    
    return all_pass, "通用翻译API正常" if all_pass else "部分翻译失败"


async def test_batch_translation(app_id, app_key):
    """测试批量翻译"""
    print_header("测试3: 批量翻译")
    
    from dwgtranslator.plugins.baidu import BaiduGeneralTranslator
    
    # 用通用翻译API测试批量
    translator = BaiduGeneralTranslator(app_id, app_key)
    
    texts = ["hello", "world", "python", "programming", "software"]
    print(f"       并发翻译 {len(texts)} 条文本...")
    
    results = await asyncio.gather(*[translator.translate_async(t, "en", "zh") for t in texts])
    await translator._session.close()
    
    for text, result in zip(texts, results):
        print(f"       {text} → {result}")
    
    # 专有名词可能翻译不变是正常的，判断标准：
    # 1. 结果数量正确，且不是所有都返回原文（排除整体失败情况
    all_same = all(r == t for r, t in zip(results, texts))
    success = len(results) == len(texts) and not all_same
    return success, "批量翻译正常" if success else "批量翻译失败"


async def test_empty_text_handling(app_id, app_key):
    """测试空文本处理"""
    print_header("测试4: 空文本处理")
    
    from dwgtranslator.plugins.baidu import BaiduFieldTranslator
    
    translator = BaiduFieldTranslator(app_id, app_key, domain="it")
    
    test_cases = [
        ("", "空字符串"),
        ("   ", "空白字符"),
        ("\n", "换行符"),
    ]
    
    all_pass = True
    for text, desc in test_cases:
        result = await translator.translate_async(text, "en", "zh")
        success = result == text  # 空文本应该原样返回
        all_pass = all_pass and success
        print(f"       {repr(text)} ({desc}) → {repr(result)}")
    
    # 关闭session
    if translator._session and not translator._session.closed:
        await translator._session.close()
    
    return all_pass, "空文本处理正常" if all_pass else "空文本处理异常"


def test_signature_formula():
    """测试签名公式正确性（离线计算）"""
    print_header("测试5: 签名公式验证 (离线)")
    
    import hashlib
    from dwgtranslator.plugins.baidu import BaiduFieldTranslator, BaiduGeneralTranslator
    
    # 测试用固定参数
    app_id = "20230000000000"
    app_key = "test_secret_key_123456"
    salt = "123456"
    query = "hello world"
    domain = "machinery"
    
    # 领域翻译签名
    field_trans = BaiduFieldTranslator(app_id, app_key, domain)
    field_sign = field_trans._generate_sign(query, salt)
    expected_field = hashlib.md5(f"{app_id}{query}{salt}{domain}{app_key}".encode()).hexdigest()
    field_ok = field_sign == expected_field
    
    print(f"       领域翻译签名:")
    print(f"         预期: {expected_field}")
    print(f"         实际: {field_sign}")
    print(f"         结果: {'一致' if field_ok else '不一致'}")
    
    # 通用翻译签名
    general_trans = BaiduGeneralTranslator(app_id, app_key)
    general_sign = general_trans._generate_sign(query, salt)
    expected_general = hashlib.md5(f"{app_id}{query}{salt}{app_key}".encode()).hexdigest()
    general_ok = general_sign == expected_general
    
    print(f"\n       通用翻译签名:")
    print(f"         预期: {expected_general}")
    print(f"         实际: {general_sign}")
    print(f"         结果: {'一致' if general_ok else '不一致'}")
    
    success = field_ok and general_ok
    return success, "签名公式正确" if success else "签名公式错误"


async def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║             百度翻译API - 真实请求测试                    ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    
    # 从环境变量或用户输入获取凭证
    app_id = os.environ.get('BAIDU_APP_ID') or input("请输入百度翻译 APP_ID: ").strip()
    app_key = os.environ.get('BAIDU_APP_KEY') or getpass("请输入百度翻译 APP_KEY: ").strip()
    
    if not app_id or not app_key:
        print("\n[FAIL] 必须提供 APP_ID 和 APP_KEY")
        print("\n可以通过环境变量设置:")
        print("  set BAIDU_APP_ID=你的ID")
        print("  set BAIDU_APP_KEY=你的密钥")
        return 1
    
    print(f"\n使用 APP_ID: {app_id}")
    print(f"使用 APP_KEY: {'*' * (len(app_key)-4)}{app_key[-4:]}")
    print()
    
    tests = [
        ("签名公式", lambda: test_signature_formula()),
        ("领域翻译API", lambda: test_field_translation(app_id, app_key)),
        ("通用翻译API", lambda: test_general_translation(app_id, app_key)),
        ("批量翻译", lambda: test_batch_translation(app_id, app_key)),
        ("空文本处理", lambda: test_empty_text_handling(app_id, app_key)),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func) or test_name in ["领域翻译API", "通用翻译API", "批量翻译", "空文本处理"]:
                success, message = await test_func()
            else:
                success, message = test_func()
            results.append((test_name, success, message))
            print_result(test_name, success, message)
        except Exception as e:
            results.append((test_name, False, str(e)))
            print_result(test_name, False, str(e))
    
    print_header("测试总结")
    passed = sum(1 for _, s, _ in results if s)
    total = len(results)
    
    for name, success, msg in results:
        status = "✓" if success else "✗"
        print(f"  {status} {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n[SUCCESS] 所有测试通过！百度翻译API工作正常。")
        return 0
    else:
        print("\n[FAIL] 部分测试失败，请检查错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
