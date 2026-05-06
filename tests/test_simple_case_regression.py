"""Regression tests for the simple CAD text patching fixture."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import Mock


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "tests" / "data"
sys.path.insert(0, str(ROOT_DIR))


class TestSimpleCaseRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oda_dxf = DATA_DIR / "simple_case.oda.dxf"
        cls.patched_dxf = DATA_DIR / "simple_case.patched.dxf"
        cls.extract_summary = cls._read_json("simple_case.extract.summary.json")
        cls.extract_data = cls._read_json("simple_case.extract.json")
        cls.translated_data = cls._read_json("simple_case.translated.json")
        cls.patch_observation = cls._read_json("simple_case.patch_observation.json")
        cls.patched_summary = cls._read_json("simple_case.patched.summary.json")

    @staticmethod
    def _read_json(name: str):
        path = DATA_DIR / name
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def test_fixture_files_exist(self):
        expected_files = [
            "simple_case.dwg",
            "simple_case.oda.dxf",
            "simple_case.extract.json",
            "simple_case.extract.summary.json",
            "simple_case.translated.json",
            "simple_case.patched.dxf",
            "simple_case.patch_observation.json",
            "simple_case.patched.extract.json",
            "simple_case.patched.summary.json",
        ]

        for name in expected_files:
            path = DATA_DIR / name
            self.assertTrue(path.exists(), f"missing fixture output: {path}")
            self.assertGreater(path.stat().st_size, 0, f"empty fixture output: {path}")

    def test_extraction_baseline_counts(self):
        self.assertEqual(self.extract_summary["total"], 975)
        self.assertEqual(
            self.extract_summary["type_counts"],
            {"MTEXT": 18, "MULTILEADER": 20, "TEXT": 937},
        )
        self.assertEqual(self.extract_summary["raw_multileaders"], 20)
        self.assertEqual(len(self.extract_data), self.extract_summary["total"])

        actual_counts = Counter(item["type"] for item in self.extract_data.values())
        self.assertEqual(dict(sorted(actual_counts.items())), self.extract_summary["type_counts"])

    def test_translated_baseline_preserves_handles_and_types(self):
        self.assertEqual(set(self.translated_data), set(self.extract_data))

        for handle, extracted in self.extract_data.items():
            translated = self.translated_data[handle]
            original = extracted.get("plain_content") or extracted.get("content") or ""
            self.assertEqual(translated["type"], extracted["type"])
            self.assertEqual(translated["original"], original)
            self.assertEqual(translated["translated"], f"TT::{original}")

    def test_patch_observation_matches_every_translated_handle(self):
        observation = self.patch_observation
        self.assertEqual(observation["total_observed"], len(self.translated_data))
        self.assertEqual(observation["matched_expected"], len(self.translated_data))
        self.assertEqual(observation["patched_count"], len(self.translated_data))

        for handle, item in observation["entities"].items():
            self.assertTrue(item["found"], f"patched entity not found: {handle}")
            self.assertTrue(item["contains_expected"], f"patched value mismatch: {handle}")
            expected_group = "304" if item["type"] == "MULTILEADER" else "1"
            self.assertEqual(item["group_code"], expected_group)

    def test_patched_dxf_is_readable_and_keeps_entity_counts(self):
        import ezdxf

        doc = ezdxf.readfile(self.patched_dxf)
        self.assertIsNotNone(doc)
        self.assertTrue(self.patched_summary["readable_by_ezdxf"])
        self.assertEqual(self.patched_summary["total"], self.extract_summary["total"])
        self.assertEqual(self.patched_summary["type_counts"], self.extract_summary["type_counts"])
        self.assertEqual(self.patched_summary["raw_multileaders"], self.extract_summary["raw_multileaders"])

    def test_patch_observation_has_representative_entity_types(self):
        entities = self.patch_observation["entities"]
        by_type: dict[str, list[dict]] = {}
        for item in entities.values():
            by_type.setdefault(item["type"], []).append(item)

        for entity_type in ("TEXT", "MTEXT", "MULTILEADER"):
            self.assertIn(entity_type, by_type)
            self.assertGreater(len(by_type[entity_type]), 0)
            self.assertTrue(any(item["contains_expected"] for item in by_type[entity_type]))

    def test_dxf_encoding_detection_uses_utf8_for_r2007_and_codepage_for_legacy(self):
        from dwgtranslator.writeback import TextWriter

        writer = TextWriter()
        self.assertEqual(writer._detect_dxf_encoding(str(self.oda_dxf)), "utf-8")

        legacy_dxf = (
            "  0\nSECTION\n"
            "  2\nHEADER\n"
            "  9\n$ACADVER\n"
            "  1\nAC1015\n"
            "  9\n$DWGCODEPAGE\n"
            "  3\nANSI_936\n"
            "  0\nENDSEC\n"
            "  0\nEOF\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT_DIR) as tmp_dir:
            path = Path(tmp_dir) / "legacy.dxf"
            path.write_text(legacy_dxf, encoding="ascii")
            self.assertEqual(writer._detect_dxf_encoding(str(path)), "gbk")

    def test_manager_translates_dxf_input_without_ezdxf_save_roundtrip(self):
        import ezdxf
        from dwgtranslator.manager import TranslationManager
        from tests.scripts.sample_helpers import observe_translated_handles

        manager = TranslationManager(oda_path="/nonexistent/ODAFileConverter")
        manager.core.save = Mock(side_effect=AssertionError("core.save should not be called for DXF input"))

        with tempfile.TemporaryDirectory(dir=ROOT_DIR) as tmp_dir:
            output_path = Path(tmp_dir) / "simple_case_translated.DWG"
            result = manager.translate_file(
                str(self.oda_dxf),
                str(output_path),
                target_lang="en",
                source_lang="zh",
                enable_chinese_font=False,
                custom_translator=lambda text, _target_lang: f"TT::{text}",
            )

            patched_path = output_path.with_suffix(".dxf")
            self.assertTrue(result)
            self.assertTrue(patched_path.exists())
            manager.core.save.assert_not_called()

            doc = ezdxf.readfile(patched_path)
            self.assertIsNotNone(doc)

            translated = {
                handle: {k: v for k, v in data.items() if k != "entity"}
                for handle, data in manager.writer.translated_bundles.items()
            }
            observation = observe_translated_handles(patched_path, translated)
            self.assertEqual(observation["matched_expected"], len(translated))
            self.assertTrue(
                any(item["type"] == "MULTILEADER" and item["contains_expected"] for item in observation["entities"].values())
            )


if __name__ == "__main__":
    unittest.main()
