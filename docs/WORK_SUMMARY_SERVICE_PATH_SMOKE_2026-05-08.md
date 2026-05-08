# Work Summary: Service Path Validation and DWG Smoke Test

Date: 2026-05-08

## Summary

- Verified the FastAPI service input and output path behavior against the platform file-processing contract.
- Updated service path handling so default upload roots can use `CADAIR_UPLOAD_ROOT` and output roots are normalized to absolute paths.
- Ran a real DWG HTTP smoke test through `POST /v1/run` using `data/20260123.dwg` and confirmed all response file paths exist on disk.

## Code Changes

- `cadair/service.py`
  - `allowed_input_roots()` now respects `CADAIR_UPLOAD_ROOT` when `CADAIR_ALLOWED_INPUT_ROOTS` is not explicitly set.
  - `output_root()` now resolves `CADAIR_OUTPUT_ROOT` to an absolute path before building request delivery paths.

- `tests/test_service_api.py`
  - Added coverage for `CADAIR_UPLOAD_ROOT` fallback behavior.
  - Added coverage ensuring response `files[].path` values remain absolute even when `CADAIR_OUTPUT_ROOT` is configured as a relative path.
  - Added manifest consistency coverage to confirm the delivery manifest excludes itself while the HTTP response can still include `manifest.json`.

## Validation

Automated service API tests passed:

```bash
.venv/bin/python -m unittest tests.test_service_api
```

Result:

```text
Ran 8 tests in 2.433s

OK
```

## HTTP Smoke Test

Started the FastAPI service on port `8030` and verified health:

```bash
GET http://127.0.0.1:8030/health
```

Health response confirmed:

- `service`: `cadair_translate`
- `oda_path_configured`: `true`
- `oda_path_exists`: `true`
- `output_root_writable`: `true`

Submitted a real DWG request using:

- Input: `/mnt/e/aiProjs/CADAir/data/20260123.dwg`
- Engine: `mock`
- Layout diagnostics: enabled
- Output root: `/mnt/e/aiProjs/CADAir/data/deliveries/apps`

The request completed successfully:

```json
{
  "ok": true,
  "status": "success",
  "request_id": "req_cadair_smoke_20260508_0953",
  "provider": "cadair_translate",
  "model": "mock",
  "data": {
    "input_file": "20260123.dwg",
    "output_file": "20260123_translated.dxf",
    "engine": "mock",
    "source": "zh",
    "target": "en",
    "layout_overflow_count": 34,
    "shrink_applied": false
  },
  "metrics": {
    "duration_ms": 9231,
    "input_files": 1,
    "output_files": 4
  }
}
```

Generated request directory:

```text
/mnt/e/aiProjs/CADAir/data/deliveries/apps/cadair_translate/test.user/2026-05-08/req_cadair_smoke_20260508_0953/
```

Response file paths all existed on disk:

```text
20260123_translated.dxf  2062646 bytes
layout_report.json       656759 bytes
result.json              500 bytes
manifest.json            1039 bytes
```

Request-scoped work files were also written under the delivery request directory:

```text
work/20260123.oda.dxf
work/20260123.extract.json
work/20260123.translated.json
```

## Platform Path Notes

The local environment did not allow creating `/data/uploads` or `/data/deliveries`, so the smoke test used repository-local absolute paths to validate the same path mechanics. In Docker or platform deployment, use same-path bind mounts so service responses match host-visible files:

```yaml
volumes:
  - /data/uploads:/data/uploads:ro
  - /data/document-intelligence:/data/document-intelligence:ro
  - /data/deliveries:/data/deliveries
```

With these mounts, `files[].path` values returned by `/v1/run` will be host-visible platform paths such as:

```text
/data/deliveries/apps/cadair_translate/<user_id>/<yyyy-mm-dd>/<request_id>/<file>
```

## Follow-Ups

- Replace remaining `print()` style operational output in DWG conversion and writeback paths with service-safe logging.
- Update integration TODOs and Docker planning from port `8101` to port `8030`.
- Add root `Dockerfile` and `docker-compose.yml` with same-path `/data/...` volume mounts.
