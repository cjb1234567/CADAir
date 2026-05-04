"""示例9: 同步 vs 异步翻译性能对比"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import asyncio
from dwgtranslator import MockTranslator
from dwgtranslator.plugins.baidu import AsyncBaiduFieldTranslator


class MockSlowTranslator(MockTranslator):
    """模拟慢速翻译API (每个请求100ms)"""
    name = "mock_slow"
    
    def translate(self, text, from_lang='auto', to_lang='zh'):
        time.sleep(0.1)  # 模拟网络延迟
        return f"[同步]{text}"


class MockAsyncSlowTranslator(AsyncBaiduFieldTranslator):
    """模拟异步慢速翻译API"""
    name = "mock_async_slow"
    
    def __init__(self, **kwargs):
        # 不需要真实的API密钥
        self.max_concurrent = kwargs.get('max_concurrent', 5)
        self.min_interval = 0
        self._semaphore = None
        self._session = None
    
    async def translate_async(self, text, from_lang='auto', to_lang='zh'):
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async with self._semaphore:
            await asyncio.sleep(0.1)  # 模拟网络延迟
            return f"[异步]{text}"


def sync_translate_demo(texts):
    """同步翻译"""
    translator = MockSlowTranslator()
    start = time.time()
    results = [translator.translate(t) for t in texts]
    elapsed = time.time() - start
    return results, elapsed


async def async_translate_demo(texts):
    """异步翻译"""
    translator = MockAsyncSlowTranslator(max_concurrent=5)
    start = time.time()
    results = await translator.batch_translate_async(texts)
    elapsed = time.time() - start
    return results, elapsed


def main():
    print("=" * 50)
    print("  示例9: 同步 vs 异步翻译性能对比")
    print("=" * 50)
    
    test_texts = [f"Text {i}" for i in range(20)]
    print(f"测试文本数量: {len(test_texts)}")
    print(f"每个请求模拟延迟: 100ms\n")
    
    # 同步
    _, sync_time = sync_translate_demo(test_texts)
    print(f"同步翻译耗时: {sync_time:.2f}s (预计: {len(test_texts)*0.1}s)")
    
    # 异步
    _, async_time = asyncio.run(async_translate_demo(test_texts))
    print(f"异步翻译耗时: {async_time:.2f}s (并发5，预计: {(len(test_texts)/5)*0.1}s)")
    
    print(f"\n加速比: {sync_time/async_time:.1f}x")


if __name__ == "__main__":
    main()
