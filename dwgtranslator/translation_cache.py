"""翻译缓存模块 - 内存级缓存，避免重复翻译"""
import hashlib
from typing import Dict, Optional


class TranslationCache:
    """翻译缓存类 - 纯内存级
    
    功能:
    1. 内存级缓存（进程内共享）
    2. 按源语言、目标语言、内容生成唯一键
    3. 逐条查询和写入
    """
    
    def __init__(self):
        self._memory_cache: Dict[str, str] = {}
        self._hit_count = 0
        self._miss_count = 0
    
    def _generate_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """生成缓存键"""
        content = f"{source_lang}:{target_lang}:{text.strip()}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """获取缓存的翻译结果
        
        Returns:
            缓存的翻译结果，未命中返回None
        """
        if not text or not text.strip():
            return text
        
        key = self._generate_key(text, source_lang, target_lang)
        result = self._memory_cache.get(key)
        
        if result is not None:
            self._hit_count += 1
        else:
            self._miss_count += 1
        
        return result
    
    def set(self, text: str, source_lang: str, target_lang: str, translated: str):
        """设置翻译结果到缓存（逐条写入）
        
        Args:
            text: 原文
            source_lang: 源语言
            target_lang: 目标语言
            translated: 翻译结果
        """
        if not text or not text.strip() or not translated:
            return
        
        key = self._generate_key(text, source_lang, target_lang)
        self._memory_cache[key] = translated
    
    def clear(self):
        """清空缓存"""
        self._memory_cache.clear()
        self._hit_count = 0
        self._miss_count = 0
    
    def stats(self) -> Dict:
        """获取缓存统计"""
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0.0
        return {
            'total_cache': len(self._memory_cache),
            'hit_count': self._hit_count,
            'miss_count': self._miss_count,
            'hit_rate': f"{hit_rate:.1%}"
        }


# 全局共享缓存实例（进程内共享内存）
_shared_cache = TranslationCache()


def get_shared_cache() -> TranslationCache:
    """获取全局共享缓存实例"""
    return _shared_cache
