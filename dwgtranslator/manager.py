import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
from .core import DWGCore
from .extract import TextExtractor
from .writeback import TextWriter
from .translator import TranslationEngine, MockTranslator
from .translation_cache import get_shared_cache, TranslationCache

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('translation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TranslationManager:
    """翻译流程管理器 - 整合所有模块，支持同步和异步翻译"""
    
    def __init__(self, oda_path: str):
        self.core = DWGCore(oda_path)
        self.extractor = TextExtractor()
        self.writer = TextWriter()
        self.translator: Optional[TranslationEngine] = None
        self.doc = None
    
    def set_translator(self, translator: TranslationEngine):
        """设置翻译引擎"""
        self.translator = translator
    
    def create_translator(self, engine_name: str, **kwargs) -> TranslationEngine:
        """通过工厂创建翻译引擎"""
        from .translator import TranslationEngineFactory
        self.translator = TranslationEngineFactory.create(engine_name, **kwargs)
        return self.translator
    
    def translate_file(self, input_path: str, output_path: str, 
                      target_lang: str = 'zh',
                      source_lang: str = 'auto',
                      enable_chinese_font: bool = True,
                      custom_translator: Optional[Callable[[str, str], str]] = None) -> bool:
        """完整翻译流程 (同步接口)"""
        self.doc = self.core.read(input_path)
        if not self.doc:
            return False
        
        self.core.ensure_encoding(self.doc)
        
        self.extractor.set_document(self.doc)
        bundles = self.extractor.extract()
        
        translated_bundles = self._do_translate(bundles, source_lang, target_lang, custom_translator)
        
        if enable_chinese_font and target_lang == 'zh':
            self.core.set_chinese_fonts(self.doc)
        
        self.writer.set_document(self.doc)
        self.writer.load_translated(translated_bundles)
        self.writer.write_all()
        
        self.core.save(self.doc, output_path)
        return True
    
    async def translate_file_async(self, input_path: str, output_path: str,
                                   target_lang: str = 'en',
                                   source_lang: str = 'auto',
                                   enable_chinese_font: bool = True) -> bool:
        """完整翻译流程 (异步接口 - 用于异步翻译引擎)"""
        self.doc = self.core.read(input_path)
        if not self.doc:
            return False
        
        self.core.ensure_encoding(self.doc)
        
        self.extractor.set_document(self.doc)
        bundles = self.extractor.extract()
        
        translated_bundles = await self._do_translate_async(bundles, source_lang, target_lang)
        
        logger.info("=== 翻译结果详情 ===")
        for handle, data in translated_bundles.items():
            original = data.get('original', '')
            translated = data.get('translated', '')
            logger.info(f"[{handle}] {original} -> {translated}")
        
        if enable_chinese_font and target_lang == 'zh':
            self.core.set_chinese_fonts(self.doc)
        
        self.writer.set_document(self.doc)
        self.writer.load_translated(translated_bundles)
        self.writer.write_all()
        
        self.core.save(self.doc, output_path)
        
        if self.translator and hasattr(self.translator, 'close'):
            await self.translator.close()
        
        return True
    
    def _do_translate(self, bundles: Dict[str, Dict[str, Any]], 
                     source_lang: str, target_lang: str,
                     custom_translator: Optional[Callable] = None) -> Dict[str, Dict[str, Any]]:
        """执行翻译 (同步，每条翻译前先查缓存)"""
        logger.info("开始同步翻译...")
        
        cache = get_shared_cache()
        translated = {}
        total_count = len(bundles)
        cache_hits = 0
        
        for handle, data in bundles.items():
            content = data.get('plain_content') or data.get('content', '')
            
            # 每条翻译前先查缓存
            cached_result = cache.get(content, source_lang, target_lang)
            if cached_result is not None:
                translated[handle] = {
                    **data,
                    'original': content,
                    'translated': cached_result
                }
                cache_hits += 1
            else:
                if custom_translator:
                    result = custom_translator(content, target_lang)
                elif self.translator:
                    result = self.translator.translate(content, source_lang, target_lang)
                else:
                    mock = MockTranslator()
                    result = mock.translate(content, source_lang, target_lang)
                
                # 翻译完成立即写入缓存
                cache.set(content, source_lang, target_lang, result)
                translated[handle] = {
                    **data,
                    'original': content,
                    'translated': result
                }
        
        logger.info(f"翻译完成，共 {total_count} 条，缓存命中: {cache_hits} 条，实际翻译: {total_count - cache_hits} 条")
        return translated
    
    async def _do_translate_async(self, bundles: Dict[str, Dict[str, Any]],
                                  source_lang: str, target_lang: str) -> Dict[str, Dict[str, Any]]:
        """执行翻译 (异步 - 每条翻译前先查缓存)"""
        logger.info("开始异步翻译...")
        
        cache = get_shared_cache()
        translated = {}
        total_count = len(bundles)
        
        # 第一步：遍历所有文本，先查一遍缓存，标记需要翻译的（避免并发下重复翻译）
        unique_content_map = {}  # content -> [(handle, data)]
        cache_hits = 0
        
        for handle, data in bundles.items():
            content = data.get('plain_content') or data.get('content', '')
            
            # 先查缓存
            cached_result = cache.get(content, source_lang, target_lang)
            if cached_result is not None:
                translated[handle] = {
                    **data,
                    'original': content,
                    'translated': cached_result
                }
                cache_hits += 1
            else:
                # 未命中，按内容分组
                if content not in unique_content_map:
                    unique_content_map[content] = []
                unique_content_map[content].append((handle, data))
        
        logger.info(f"缓存命中: {cache_hits} 条，唯一待翻译内容: {len(unique_content_map)} 条")
        
        # 第二步：翻译唯一内容
        if unique_content_map:
            if self.translator and hasattr(self.translator, 'translate_async'):
                # 异步翻译唯一条目
                async def translate_unique(content: str, handle_data_list: list) -> tuple:
                    result = await self.translator.translate_async(content, source_lang, target_lang)
                    # 翻译完成立即写入缓存
                    cache.set(content, source_lang, target_lang, result)
                    return (content, result, handle_data_list)
                
                tasks = [translate_unique(c, hd) for c, hd in unique_content_map.items()]
                results = await asyncio.gather(*tasks)
                
                # 把翻译结果分配给所有使用该内容的handle
                for content, result, handle_data_list in results:
                    for handle, data in handle_data_list:
                        translated[handle] = {
                            **data,
                            'original': content,
                            'translated': result
                        }
            else:
                # 同步翻译
                for content, handle_data_list in unique_content_map.items():
                    if self.translator:
                        result = self.translator.translate(content, source_lang, target_lang)
                    else:
                        mock = MockTranslator()
                        result = mock.translate(content, source_lang, target_lang)
                    cache.set(content, source_lang, target_lang, result)
                    
                    for handle, data in handle_data_list:
                        translated[handle] = {
                            **data,
                            'original': content,
                            'translated': result
                        }
        
        actual_translated = total_count - cache_hits
        logger.info(f"翻译完成，共 {total_count} 条，缓存命中: {cache_hits} 条，实际翻译: {actual_translated} 条")
        return translated
    
    def extract_only(self, input_path: str, json_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """仅提取文本"""
        self.doc = self.core.read(input_path)
        if not self.doc:
            return {}
        
        self.extractor.set_document(self.doc)
        bundles = self.extractor.extract()
        
        if json_path:
            self.extractor.export_json(json_path)
        
        return bundles
    
    def writeback_only(self, input_path: str, translated_json: str, output_path: str) -> bool:
        """仅写回翻译结果"""
        self.doc = self.core.read(input_path)
        if not self.doc:
            return False
        
        self.writer.set_document(self.doc)
        self.writer.load_from_json(translated_json)
        self.writer.write_all()
        
        self.core.save(self.doc, output_path)
        return True
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        cache = get_shared_cache()
        return cache.stats()
    
    def clear_cache(self):
        """清空翻译缓存"""
        cache = get_shared_cache()
        cache.clear()
        logger.info("翻译缓存已清空")


def run_async(coro):
    """运行异步协程的工具函数"""
    return asyncio.run(coro)
