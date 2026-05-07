import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from dwgtranslator.glossary import load_glossary
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
        manager.glossary = load_glossary()
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
        manager.glossary = load_glossary()
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

    def test_sync_filter_uses_custom_glossary(self):
        manager = TranslationManager.__new__(TranslationManager)
        manager.glossary = load_glossary(glossary=['主柜'])
        translator = CountingTranslator()
        manager.set_translator(translator)
        bundles = {
            '1': {'handle': '1', 'content': '主柜', 'type': 'TEXT'},
            '2': {'handle': '2', 'content': '备用柜', 'type': 'TEXT'},
        }

        translated = manager._do_translate(bundles, source_lang='zh', target_lang='en')

        self.assertEqual(set(translated), {'2'})
        self.assertEqual(translator.calls, [('备用柜', 'zh', 'en')])

    def test_async_filter_uses_custom_glossary_json(self):
        import asyncio

        manager = TranslationManager.__new__(TranslationManager)
        manager.glossary = load_glossary(glossary_json='["主柜"]')
        translator = AsyncCountingTranslator()
        manager.set_translator(translator)
        bundles = {
            '1': {'handle': '1', 'content': '主柜', 'type': 'TEXT'},
            '2': {'handle': '2', 'content': '备用柜', 'type': 'TEXT'},
        }

        translated = asyncio.run(manager._do_translate_async(bundles, source_lang='zh', target_lang='en'))

        self.assertEqual(set(translated), {'2'})
        self.assertEqual(translator.calls, [('备用柜', 'zh', 'en')])

    def test_sync_uses_fixed_glossary_translation_before_api(self):
        manager = TranslationManager.__new__(TranslationManager)
        manager.glossary = load_glossary(glossary_json='{"translations": {"主柜": "Main Cabinet"}}')
        translator = CountingTranslator()
        manager.set_translator(translator)
        bundles = {
            '1': {'handle': '1', 'content': '主柜', 'type': 'TEXT'},
            '2': {'handle': '2', 'content': '备用柜', 'type': 'TEXT'},
        }

        translated = manager._do_translate(bundles, source_lang='zh', target_lang='en')

        self.assertEqual(translated['1']['translated'], 'Main Cabinet')
        self.assertEqual(translated['2']['translated'], 'TT::备用柜')
        self.assertEqual(translator.calls, [('备用柜', 'zh', 'en')])

    def test_async_uses_fixed_glossary_translation_before_api(self):
        import asyncio

        manager = TranslationManager.__new__(TranslationManager)
        manager.glossary = load_glossary(glossary_json='{"translations": {"主柜": "Main Cabinet"}}')
        translator = AsyncCountingTranslator()
        manager.set_translator(translator)
        bundles = {
            '1': {'handle': '1', 'content': '主柜', 'type': 'TEXT'},
            '2': {'handle': '2', 'content': '备用柜', 'type': 'TEXT'},
        }

        translated = asyncio.run(manager._do_translate_async(bundles, source_lang='zh', target_lang='en'))

        self.assertEqual(translated['1']['translated'], 'Main Cabinet')
        self.assertEqual(translated['2']['translated'], 'TT::备用柜')
        self.assertEqual(translator.calls, [('备用柜', 'zh', 'en')])


class TestGlossaryLoading(unittest.TestCase):
    def test_loads_json_list(self):
        glossary = load_glossary(glossary_json='["odf", "主柜"]')

        self.assertIn('ODF', glossary.terms)
        self.assertIn('主柜', glossary.terms)

    def test_loads_comma_separated_terms_for_cli(self):
        glossary = load_glossary(glossary_json='odf,pdu,主柜')

        self.assertIn('ODF', glossary.terms)
        self.assertIn('PDU', glossary.terms)
        self.assertIn('主柜', glossary.terms)

    def test_loads_json_file_object(self):
        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / 'glossary.json'
            path.write_text(
                '{"terms": ["主柜"], "translations": {"备用柜": "Standby Cabinet"}}',
                encoding='utf-8',
            )

            glossary = load_glossary(glossary_file=str(path))

        self.assertIn('主柜', glossary.terms)
        self.assertEqual(glossary.translation_for('备用柜'), 'Standby Cabinet')

    def test_loads_translation_map(self):
        glossary = load_glossary(glossary_json='{"translations": {"主柜": "Main Cabinet"}}')

        self.assertEqual(glossary.translation_for('主柜'), 'Main Cabinet')
        self.assertEqual(glossary.translation_for(' 主柜 '), 'Main Cabinet')

    def test_rejects_invalid_json_shape(self):
        with self.assertRaises(ValueError):
            load_glossary(glossary_json='{"term": "ODF"}')


if __name__ == '__main__':
    unittest.main()
