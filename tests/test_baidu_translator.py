"""百度翻译API单元测试"""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保UTF-8编码输出
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# 统一检查aiohttp
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    print("提示: 未安装aiohttp，百度翻译相关测试将跳过")


@unittest.skipUnless(AIOHTTP_AVAILABLE, "需要aiohttp才能运行百度翻译测试")
class TestBaiduSignatures(unittest.TestCase):
    """百度API签名测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.app_id = "20220227001099938"
        cls.app_key = "wnUM1_f8rckiUKlo0jg_"
        cls.query = "hello world"
        cls.salt = "123456"
        cls.domain = "machinery"
    
    def test_field_translator_signature(self):
        """测试领域翻译API签名公式"""
        from dwgtranslator.plugins.baidu import BaiduFieldTranslator
        
        translator = BaiduFieldTranslator(self.app_id, self.app_key, self.domain)
        sign = translator._generate_sign(self.query, self.salt)
        
        import hashlib
        expected_sign = hashlib.md5(
            f"{self.app_id}{self.query}{self.salt}{self.domain}{self.app_key}".encode('utf-8')
        ).hexdigest()
        
        self.assertEqual(sign, expected_sign, "领域翻译API签名公式错误")
    
    def test_general_translator_signature(self):
        """测试通用翻译API签名公式"""
        from dwgtranslator.plugins.baidu import BaiduGeneralTranslator
        
        translator = BaiduGeneralTranslator(self.app_id, self.app_key)
        sign = translator._generate_sign(self.query, self.salt)
        
        import hashlib
        expected_sign = hashlib.md5(
            f"{self.app_id}{self.query}{self.salt}{self.app_key}".encode('utf-8')
        ).hexdigest()
        
        self.assertEqual(sign, expected_sign, "通用翻译API签名公式错误")
    
    @unittest.skipUnless(AIOHTTP_AVAILABLE, "需要aiohttp")
    def test_async_field_translator_signature(self):
        """测试异步领域翻译API签名公式"""
        from dwgtranslator.plugins.baidu import AsyncBaiduFieldTranslator
        
        translator = AsyncBaiduFieldTranslator(self.app_id, self.app_key, self.domain)
        sign = translator._generate_sign(self.query, self.salt)
        
        import hashlib
        expected_sign = hashlib.md5(
            f"{self.app_id}{self.query}{self.salt}{self.domain}{self.app_key}".encode('utf-8')
        ).hexdigest()
        
        self.assertEqual(sign, expected_sign, "异步领域翻译API签名公式错误")
    
    @unittest.skipUnless(AIOHTTP_AVAILABLE, "需要aiohttp")
    def test_async_general_translator_signature(self):
        """测试异步通用翻译API签名公式"""
        from dwgtranslator.plugins.baidu import AsyncBaiduGeneralTranslator
        
        translator = AsyncBaiduGeneralTranslator(self.app_id, self.app_key)
        sign = translator._generate_sign(self.query, self.salt)
        
        import hashlib
        expected_sign = hashlib.md5(
            f"{self.app_id}{self.query}{self.salt}{self.app_key}".encode('utf-8')
        ).hexdigest()
        
        self.assertEqual(sign, expected_sign, "异步通用翻译API签名公式错误")


@unittest.skipUnless(AIOHTTP_AVAILABLE, "需要aiohttp")
class TestBaiduTranslatorErrors(unittest.TestCase):
    """百度翻译错误处理测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.app_id = "test_app_id_123"
        cls.app_key = "test_secret_key_456"
    
    @patch('dwgtranslator.plugins.baidu.aiohttp.ClientSession.post')
    def test_invalid_sign_error(self, mock_post):
        """测试Invalid Sign错误处理"""
        from dwgtranslator.plugins.baidu import BaiduFieldTranslator
        
        # 模拟aiohttp响应
        mock_resp = Mock()
        mock_resp.json = AsyncMock(return_value={
            'error_code': '54001',
            'error_msg': 'Invalid Sign'
        })
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_post.return_value = mock_ctx
        
        translator = BaiduFieldTranslator(self.app_id, self.app_key, "it")
        translator._session = Mock()  # 注入模拟session
        
        result = asyncio.run(translator.translate_async("hello", "en", "zh"))
        self.assertEqual(result, "hello", "签名错误应该返回原文")
    
    def test_empty_text(self):
        """测试空文本处理"""
        from dwgtranslator.plugins.baidu import BaiduFieldTranslator
        
        translator = BaiduFieldTranslator(self.app_id, self.app_key, "it")
        
        result = asyncio.run(translator.translate_async("", "en", "zh"))
        self.assertEqual(result, "", "空字符串应该直接返回")
        
        result = asyncio.run(translator.translate_async("   ", "en", "zh"))
        self.assertEqual(result, "   ", "空白字符应该直接返回")


@unittest.skipUnless(AIOHTTP_AVAILABLE, "需要aiohttp")
class TestBaiduConcurrencyConfig(unittest.TestCase):
    """百度翻译并发配置测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.app_id = "test_app_id_123"
        cls.app_key = "test_secret_key_456"
    
    def test_concurrency_config(self):
        """测试并发和QPS配置"""
        from dwgtranslator.plugins.baidu import BaiduFieldTranslator
        
        translator = BaiduFieldTranslator(
            self.app_id, self.app_key, "it",
            max_concurrent=5,
            requests_per_second=2.0
        )
        
        self.assertEqual(translator.max_concurrent, 5)
        self.assertEqual(translator.min_interval, 0.5)  # 1/2 = 0.5s 间隔


class TestEngineRegistration(unittest.TestCase):
    """翻译引擎注册测试"""
    
    def test_all_engines_registered(self):
        """测试所有翻译引擎都已注册"""
        from dwgtranslator.translator import TranslationEngineFactory
        
        engines = TranslationEngineFactory.list_engines()
        
        # 现在百度翻译只有2个引擎（异步版本是别名）
        expected_engines = ['mock', 'baidu_field', 'baidu_general']
        
        for engine in expected_engines:
            self.assertIn(engine, engines, f"引擎 {engine} 未注册")
    
    def test_create_mock_engine(self):
        """测试创建Mock翻译引擎"""
        from dwgtranslator.translator import TranslationEngineFactory
        
        mock = TranslationEngineFactory.create('mock')
        self.assertEqual(mock.get_engine_name(), 'mock')
        
        result = mock.translate("test", "en", "zh")
        self.assertIsNotNone(result)
    
    @unittest.skipUnless(AIOHTTP_AVAILABLE, "需要aiohttp")
    def test_create_baidu_engine(self):
        """测试创建百度翻译引擎"""
        from dwgtranslator.translator import TranslationEngineFactory
        
        baidu = TranslationEngineFactory.create(
            'baidu_field',
            app_id='test',
            app_key='test',
            domain='it'
        )
        self.assertEqual(baidu.get_engine_name(), 'baidu_field')


def run_baidu_tests():
    """运行所有百度翻译相关测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestBaiduSignatures))
    suite.addTests(loader.loadTestsFromTestCase(TestBaiduTranslatorErrors))
    suite.addTests(loader.loadTestsFromTestCase(TestBaiduConcurrencyConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestEngineRegistration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 60)
    print("百度翻译API单元测试")
    print("=" * 60)
    print()
    
    success = run_baidu_tests()
    
    print()
    print("=" * 60)
    if success:
        print("[PASS] 全部测试通过")
    else:
        print("[FAIL] 存在测试失败")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
