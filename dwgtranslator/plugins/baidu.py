import hashlib
import random
import asyncio
import time
import logging
from typing import List

try:
    import aiohttp
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("提示: 百度翻译API需要安装: pip install aiohttp")

logger = logging.getLogger(__name__)

from dwgtranslator.translator import TranslationEngine, TranslationEngineFactory


class BaiduFieldTranslator(TranslationEngine):
    """百度领域翻译API - 同步接口（内部使用aiohttp异步）"""
    
    name: str = "baidu_field"
    BASE_URL = "https://fanyi-api.baidu.com/api/trans/vip/fieldtranslate"
    
    def __init__(self, app_id: str, app_key: str, domain: str = "it", **kwargs):
        if not REQUESTS_AVAILABLE:
            raise ImportError("百度翻译API需要安装: pip install aiohttp")
        
        super().__init__(**kwargs)
        self.app_id = app_id
        self.app_key = app_key
        self.domain = domain
        # 百度免费版QPS=1，默认设置为0.9留余量，避免触发54003错误
        self.max_concurrent = kwargs.get('max_concurrent', 1)
        self.min_interval = 1.0 / kwargs.get('requests_per_second', 0.9)
        self._session = None
        self._semaphore = None
        self._last_request = 0
    
    def _generate_sign(self, query: str, salt: str) -> str:
        """生成签名：app_id + query + salt + domain + app_key"""
        sign_str = f"{self.app_id}{query}{salt}{self.domain}{self.app_key}"
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    
    async def _rate_limit(self):
        """频率控制"""
        now = time.time()
        elapsed = now - getattr(self, '_last_request', 0)
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self._last_request = time.time()
    
    async def translate_async(self, text: str, from_lang: str = 'auto', 
                            to_lang: str = 'zh') -> str:
        """异步翻译"""
        if not text or not text.strip():
            return text
        
        if self._session is None:
            self._session = aiohttp.ClientSession()
        
        # 延迟初始化信号量，用于并发控制
        if not hasattr(self, '_semaphore') or self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        
        salt = str(random.randint(32768, 65536))
        sign = self._generate_sign(text, salt)
        
        params = {
            'q': text, 'from': from_lang, 'to': to_lang,
            'appid': self.app_id, 'salt': salt, 'sign': sign,
            'domain': self.domain
        }
        
        try:
            async with self._semaphore:
                await self._rate_limit()
                async with self._session.post(self.BASE_URL, data=params,
                                            timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    result = await resp.json()
                    
                    if 'error_code' in result and result['error_code'] != '52000':
                        logger.error(f"API错误 [{result.get('error_code')}]: {result.get('error_msg', '未知')}")
                        logger.error(f"  请求参数: text='{text}', from={from_lang}, to={to_lang}, domain={self.domain}")
                        return text
                    
                    if 'trans_result' in result and len(result['trans_result']) > 0:
                        translated = result['trans_result'][0]['dst']
                        return translated
                    
                    logger.warning(f"领域翻译API结果格式错误: {result}")
                    return text
        except Exception as e:
            logger.error(f"请求失败: {e}")
            return text
    
    def translate(self, text: str, from_lang: str = 'auto', to_lang: str = 'zh') -> str:
        """同步接口（兼容基类）"""
        try:
            loop = asyncio.get_running_loop()
            # 已经在事件循环中，直接调用异步（注意：这里需要等待，但同步接口不能await）
            # 更好的做法是：同步流程中调用同步接口，异步流程中调用异步接口
            # 因此这里抛出明确错误提示
            raise RuntimeError("在异步环境中请使用 translate_async() 方法")
        except RuntimeError:
            # 没有运行中的事件循环，可以安全使用 asyncio.run
            return asyncio.run(self.translate_async(text, from_lang, to_lang))
    
    def batch_translate(self, texts: List[str], from_lang: str = 'auto',
                       to_lang: str = 'zh') -> List[str]:
        """批量翻译（异步并发）"""
        async def run():
            tasks = [self.translate_async(t, from_lang, to_lang) for t in texts]
            return await asyncio.gather(*tasks)
        return asyncio.run(run())
    
    def supports_batch(self) -> bool:
        return True
    
    async def close(self):
        """关闭HTTP会话"""
        if self._session:
            await self._session.close()
            self._session = None
    
    def __del__(self):
        """析构时关闭会话"""
        if self._session:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except Exception:
                pass


class BaiduGeneralTranslator(BaiduFieldTranslator):
    """百度通用翻译API - 同步接口"""
    
    name: str = "baidu_general"
    BASE_URL = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    
    def _generate_sign(self, query: str, salt: str) -> str:
        """通用翻译签名：app_id + query + salt + app_key"""
        sign_str = f"{self.app_id}{query}{salt}{self.app_key}"
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    
    async def translate_async(self, text: str, from_lang: str = 'auto', 
                            to_lang: str = 'zh') -> str:
        if not text or not text.strip():
            return text
        
        if self._session is None:
            self._session = aiohttp.ClientSession()
        
        # 延迟初始化信号量，用于并发控制
        if not hasattr(self, '_semaphore') or self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        
        salt = str(random.randint(32768, 65536))
        sign = self._generate_sign(text, salt)
        
        params = {
            'q': text, 'from': from_lang, 'to': to_lang,
            'appid': self.app_id, 'salt': salt, 'sign': sign
        }
        
        try:
            async with self._semaphore:
                await self._rate_limit()
                async with self._session.post(self.BASE_URL, data=params,
                                            timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    result = await resp.json()
                    
                    if 'error_code' in result and result['error_code'] != '52000':
                        logger.error(f"API错误 [{result.get('error_code')}]: {result.get('error_msg', '未知')}")
                        return text
                    
                    if 'trans_result' in result and len(result['trans_result']) > 0:
                        return result['trans_result'][0]['dst']
                    return text
        except Exception as e:
            logger.error(f"请求失败: {e}")
            return text


# 异步版本别名（保持向后兼容）
AsyncBaiduFieldTranslator = BaiduFieldTranslator
AsyncBaiduGeneralTranslator = BaiduGeneralTranslator


# 注册所有引擎
TranslationEngineFactory.register(BaiduFieldTranslator)
TranslationEngineFactory.register(BaiduGeneralTranslator)
