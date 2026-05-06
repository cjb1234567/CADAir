import unittest

from dwgtranslator.manager import TranslationManager
from dwgtranslator.translation_cache import get_shared_cache
from dwgtranslator.translation_filter import should_translate_text


class CountingTranslator:
    def __init__(self):
        self.calls = []

    def translate(self, text, source_lang, target_lang):
        self.calls.append((text, source_lang, target_lang))
        return f"TT::{text}"


class AsyncCountingTranslator(CountingTranslator):
    async def translate_async(self, text, source_lang, target_lang):
        self.calls.append((text, source_lang, target_lang))
        return f"TT::{text}"


class TestTranslationFilterRules(unittest.TestCase):
    def assert_skipped(self, text, target_lang='en'):
        result = should_translate_text(text, source_lang='zh', target_lang=target_lang)
        self.assertFalse(result.should_translate, text)

    def assert_translated(self, text, target_lang='en'):
        result = should_translate_text(text, source_lang='zh', target_lang=target_lang)
        self.assertTrue(result.should_translate, text)

    def test_skips_numbers_dimensions_and_units(self):
        for text in ('12', '3.5', '-10', '300mm', '100x200', '1:100', '4-20mA'):
            self.assert_skipped(text)

    def test_skips_uppercase_terms_and_equipment_ids(self):
        for text in ('PDU', 'RUN', 'ALM', 'PWR', 'CAB-01', 'XT1', 'U01', '2U'):
            self.assert_skipped(text)

    def test_skips_target_language_english_text(self):
        for text in ('Power supply', 'Main cabinet', 'Control panel'):
            self.assert_skipped(text, target_lang='en')

    def test_translates_chinese_and_mixed_chinese_text_to_english(self):
        for text in ('主柜', '主柜 PDU', '备用 POWER'):
            self.assert_translated(text, target_lang='en')

    def test_skips_target_language_chinese_text(self):
        self.assert_skipped('主柜', target_lang='zh')

    def test_translates_english_sentence_to_chinese(self):
        self.assert_translated('Main cabinet power supply', target_lang='zh')


class TestTranslationManagerFiltering(unittest.TestCase):
    def setUp(self):
        get_shared_cache().clear()

    def test_sync_filter_skips_api_and_writeback_bundle(self):
        manager = TranslationManager.__new__(TranslationManager)
        translator = CountingTranslator()
        manager.set_translator(translator)
        bundles = {
            '1': {'handle': '1', 'content': '主柜', 'type': 'TEXT'},
            '2': {'handle': '2', 'content': 'PDU', 'type': 'TEXT'},
            '3': {'handle': '3', 'content': '100x200', 'type': 'TEXT'},
            '4': {'handle': '4', 'content': 'Power supply', 'type': 'TEXT'},
        }

        translated = manager._do_translate(bundles, source_lang='zh', target_lang='en')

        self.assertEqual(set(translated), {'1'})
        self.assertEqual(translated['1']['translated'], 'TT::主柜')
        self.assertEqual(translator.calls, [('主柜', 'zh', 'en')])

    def test_async_filter_matches_sync_filter(self):
        import asyncio

        manager = TranslationManager.__new__(TranslationManager)
        translator = AsyncCountingTranslator()
        manager.set_translator(translator)
        bundles = {
            '1': {'handle': '1', 'content': '主柜', 'type': 'TEXT'},
            '2': {'handle': '2', 'content': 'PDU', 'type': 'TEXT'},
            '3': {'handle': '3', 'content': 'Power supply', 'type': 'TEXT'},
        }

        translated = asyncio.run(manager._do_translate_async(bundles, source_lang='zh', target_lang='en'))

        self.assertEqual(set(translated), {'1'})
        self.assertEqual(translated['1']['translated'], 'TT::主柜')
        self.assertEqual(translator.calls, [('主柜', 'zh', 'en')])


if __name__ == '__main__':
    unittest.main()
