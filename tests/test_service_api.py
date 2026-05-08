from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from cadair.service import app


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "tests" / "data"


class TestServiceApi(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT_DIR)
        self.tmp_path = Path(self.tmp.name)
        self.upload_root = self.tmp_path / "uploads"
        self.output_root = self.tmp_path / "deliveries" / "apps"
        self.upload_root.mkdir(parents=True)
        self.output_root.mkdir(parents=True)
        self.env = patch.dict(
            "os.environ",
            {
                "CADAIR_APP_ID": "cadair_translate",
                "CADAIR_ALLOWED_INPUT_ROOTS": str(self.upload_root),
                "CADAIR_OUTPUT_ROOT": str(self.output_root),
                "TRANSLATE_SOURCE": "zh",
                "TRANSLATE_TARGET": "en",
            },
            clear=False,
        )
        self.env.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def payload(self, path: Path, **params):
        return {
            "request_id": "req_test_001",
            "user_id": "test.user",
            "skill_id": "cadair_translate",
            "input": {
                "files": [
                    {
                        "path": str(path),
                        "filename": path.name,
                        "mime_type": "application/dxf",
                    }
                ],
                "params": {"engine": "mock", "mock_prefix": "TT::", **params},
            },
            "context": {"source": "unittest", "timezone": "Asia/Shanghai", "trace_id": "trace_test"},
            "delivery": {"auto_deliver": True, "title": "CAD 图纸翻译结果", "formats": ["dxf", "json"]},
        }

    def test_health(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["service"], "cadair_translate")
        self.assertEqual(body["dependencies"]["output_root"], str(self.output_root))

    def test_run_rejects_empty_files(self):
        payload = self.payload(self.upload_root / "missing.dxf")
        payload["input"]["files"] = []

        response = self.client.post("/v1/run", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "invalid_input")

    def test_run_rejects_outside_allowed_roots(self):
        outside = self.tmp_path / "outside.dxf"
        outside.write_text("0\nEOF\n", encoding="utf-8")

        response = self.client.post("/v1/run", json=self.payload(outside))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "permission_denied")

    def test_run_returns_file_not_found_for_allowed_missing_path(self):
        response = self.client.post("/v1/run", json=self.payload(self.upload_root / "missing.dxf"))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "file_not_found")

    def test_run_accepts_cadair_upload_root_default(self):
        upload_root = self.tmp_path / "configured_uploads"
        upload_root.mkdir()
        input_path = upload_root / "missing.dxf"
        environ = dict(os.environ)
        environ["CADAIR_UPLOAD_ROOT"] = str(upload_root)
        environ.pop("CADAIR_ALLOWED_INPUT_ROOTS", None)
        with patch.dict("os.environ", environ, clear=True):
            response = self.client.post("/v1/run", json=self.payload(input_path))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "file_not_found")

    def test_run_rejects_unsupported_extension(self):
        pdf = self.upload_root / "input.pdf"
        pdf.write_text("not cad", encoding="utf-8")

        response = self.client.post("/v1/run", json=self.payload(pdf))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "file_type_not_supported")

    def test_run_mock_dxf_success_writes_delivery_files(self):
        input_path = self.upload_root / "simple_case.oda.dxf"
        shutil.copyfile(DATA_DIR / "simple_case.oda.dxf", input_path)

        response = self.client.post("/v1/run", json=self.payload(input_path, glossary_json={"translations": {"主柜": "Main Cabinet"}}))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"], body)
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["provider"], "cadair_translate")
        self.assertEqual(body["model"], "mock")
        self.assertEqual(body["metrics"]["input_files"], 1)
        self.assertGreaterEqual(body["metrics"]["output_files"], 3)

        file_paths = [Path(item["path"]) for item in body["files"]]
        for path in file_paths:
            self.assertTrue(path.exists(), path)
            self.assertTrue(str(path).startswith(str(self.output_root)), path)

        result_path = next(path for path in file_paths if path.name == "result.json")
        manifest_path = next(path for path in file_paths if path.name == "manifest.json")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertTrue(result["ok"])
        self.assertEqual(manifest["app_id"], "cadair_translate")
        self.assertEqual(manifest["request_id"], "req_test_001")
        self.assertEqual(manifest["files"], [item for item in body["files"] if item["path"] != str(manifest_path)])

    def test_run_resolves_relative_output_root_to_absolute_response_paths(self):
        input_path = self.upload_root / "simple_case.oda.dxf"
        shutil.copyfile(DATA_DIR / "simple_case.oda.dxf", input_path)
        relative_output_root = self.tmp_path.relative_to(ROOT_DIR) / "relative-deliveries" / "apps"

        with patch.dict("os.environ", {"CADAIR_OUTPUT_ROOT": str(relative_output_root)}, clear=False):
            response = self.client.post("/v1/run", json=self.payload(input_path))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"], body)
        for item in body["files"]:
            self.assertTrue(Path(item["path"]).is_absolute(), item)


if __name__ == "__main__":
    unittest.main()
