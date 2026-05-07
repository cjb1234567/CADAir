# CADAir Integration TODO

Last updated: 2026-05-07

## Goal

Package CADAir as a FastAPI-based Python microservice so the existing AI panel can call it through AI Gateway as a standard file-processing skill.

Reference standards:

- `docs/integration/PYTHON-SCENARIO-INTEGRATION-STANDARD.zh-CN.md`
- `docs/integration/PYTHON-APP-MAINTENANCE-DIRECTORY-DESIGN.zh-CN.md`

## Target Integration Model

- Integration type: A class HTTP microservice.
- Gateway entrypoint: AI Gateway calls CADAir; Portal, Dify, and OpenClaw should not call CADAir directly.
- App ID: `cadair_translate`.
- Skill ID: `cadair_translate`.
- Service name: `cadair-translate-service`.
- Default port: `8101`.
- Upload input root: `/data/uploads`.
- Additional read-only input roots: `/data/document-intelligence`, `/data/deliveries`.
- Delivery output root: `/data/deliveries/apps`.
- Output directory format: `/data/deliveries/apps/cadair_translate/<user_id>/<yyyy-mm-dd>/<request_id>/`.
- OneDrive delivery: Gateway-owned; CADAir returns platform file paths only.

## High Priority Implementation Tasks

- [x] Add FastAPI dependencies to `pyproject.toml`: `fastapi>=0.110,<1`, `uvicorn>=0.27,<1`, `pydantic>=2,<3`.
- [x] Add `cadair/service_schemas.py` with standard request, response, file, error, health, and params models.
- [x] Add `cadair/service.py` exposing `GET /health` and `POST /v1/run`.
- [x] Implement platform path policy: accept input files only under configured roots, and write all service outputs under `CADAIR_OUTPUT_ROOT`.
- [x] Implement CAD translation run flow using existing CADAir logic with request-scoped output and work directories.
- [x] Support `params.glossary_json` in `/v1/run`, in addition to `params.glossary_file`.
- [x] Support optional layout diagnostics through `params.layout_check`.
- [x] Support optional safe shrink through `params.shrink` and shrink tuning params.
- [x] Write `result.json` and `manifest.json` for each request.
- [x] Add structured service logs with `request_id`, `user_id`, `skill_id`, `stage`, `duration_ms`, `status`, and `error_code`.
- [x] Add tests for `/health`, invalid input, missing file, path rejection, and mock DXF success flow.
- [ ] Add `Dockerfile` and root `docker-compose.yml` for local service runs.
- [ ] Add `.env.example` without real secrets.
- [ ] Add `app-integrations/cadair-translate/` maintenance directory.
- [ ] Update `README.md` with service and Docker usage.

## API Contract

### Health

```http
GET /health
```

Response:

```json
{
  "status": "ok",
  "service": "cadair_translate",
  "version": "0.1.0",
  "time": "2026-05-07T10:00:00+08:00",
  "dependencies": {
    "oda_path_configured": true,
    "output_root": "/data/deliveries/apps"
  }
}
```

### Run

```http
POST /v1/run
Content-Type: application/json
```

Request example:

```json
{
  "request_id": "req_cadair_001",
  "user_id": "mike.xiang",
  "skill_id": "cadair_translate",
  "input": {
    "files": [
      {
        "path": "/data/uploads/20260123.dwg",
        "filename": "20260123.dwg",
        "mime_type": "application/acad"
      }
    ],
    "params": {
      "engine": "baidu_general",
      "source": "zh",
      "target": "en",
      "glossary_file": "/data/config/cad_glossary_zh-en.json",
      "glossary_json": {
        "terms": ["ODF", "PDU", "CCU", "ETH", "RUN", "ALM", "PWR"],
        "translations": {
          "主柜": "Main Cabinet",
          "备用柜": "Standby Cabinet"
        }
      },
      "layout_check": true,
      "shrink": false,
      "scale_threshold": 0.8,
      "min_height": 2.0,
      "min_scale": 0.65
    }
  },
  "context": {
    "source": "portal",
    "timezone": "Asia/Shanghai",
    "trace_id": "trace_xxx"
  },
  "delivery": {
    "auto_deliver": true,
    "title": "CAD 图纸翻译结果",
    "formats": ["dxf", "json"]
  }
}
```

Success response example:

```json
{
  "ok": true,
  "status": "success",
  "request_id": "req_cadair_001",
  "provider": "cadair_translate",
  "model": "baidu_general",
  "content": "CAD 图纸翻译完成，已生成 DXF 输出文件。",
  "data": {
    "input_file": "20260123.dwg",
    "output_file": "20260123_translated.dxf",
    "engine": "baidu_general",
    "source": "zh",
    "target": "en",
    "layout_overflow_count": 124,
    "shrink_applied": false
  },
  "files": [
    {
      "path": "/data/deliveries/apps/cadair_translate/mike.xiang/2026-05-07/req_cadair_001/20260123_translated.dxf",
      "filename": "20260123_translated.dxf",
      "mime_type": "application/dxf"
    },
    {
      "path": "/data/deliveries/apps/cadair_translate/mike.xiang/2026-05-07/req_cadair_001/result.json",
      "filename": "result.json",
      "mime_type": "application/json"
    },
    {
      "path": "/data/deliveries/apps/cadair_translate/mike.xiang/2026-05-07/req_cadair_001/manifest.json",
      "filename": "manifest.json",
      "mime_type": "application/json"
    }
  ],
  "metrics": {
    "duration_ms": 128000,
    "input_files": 1,
    "output_files": 3
  }
}
```

Error response example:

```json
{
  "ok": false,
  "status": "failed",
  "request_id": "req_cadair_001",
  "error": {
    "code": "file_not_found",
    "message": "Input file does not exist",
    "retryable": false,
    "detail": {}
  }
}
```

## Supported Run Params

- `engine`: `mock`, `baidu_general`, or `baidu_field`; default `mock` for local smoke tests.
- `source`: source language; default from `TRANSLATE_SOURCE`, fallback `auto`.
- `target`: target language; default from `TRANSLATE_TARGET`, fallback `en`.
- `app_id`: optional request-level Baidu app id; normally omitted and loaded from service env.
- `app_key`: optional request-level Baidu app key; normally omitted and loaded from service env.
- `domain`: Baidu field translation domain; default from `TRANSLATE_DOMAIN`, fallback `machinery`.
- `qps`: translation API QPS; default from `TRANSLATE_QPS`, fallback `1.0`.
- `max_concurrent`: translation concurrency; default `1`.
- `mock_prefix`: mock translator prefix; default empty string.
- `glossary_file`: path to a platform-managed glossary JSON file.
- `glossary_json`: request-level glossary JSON object or JSON string.
- `layout_check`: run text layout diagnostics after translation.
- `shrink`: run conservative `TEXT` shrink after translation.
- `scale_threshold`: shrink threshold, default `1.0` or service default.
- `min_height`: minimum text height for shrink, default `2.0`.
- `min_scale`: minimum shrink scale, default `0.65`.

Glossary precedence:

- Load environment `GLOSSARY_FILE` and `GLOSSARY_JSON` as base defaults if present.
- Merge `params.glossary_file` if present.
- Merge `params.glossary_json` last so request-specific fixed translations can override file-based translations.
- Do not log the full glossary content by default because it may contain customer/project terminology.

## Platform Directory Requirements

### Input Files

- Uploaded CAD files should be stored by Gateway or the platform under `/data/uploads` before CADAir is called.
- CADAir should also allow read-only inputs from `/data/document-intelligence` and `/data/deliveries` for platform workflows that reuse earlier outputs.
- CADAir should reject paths outside configured roots with `permission_denied`.
- CADAir should support only `.dwg` and `.dxf` input for the first service version.
- CADAir should not accept arbitrary desktop, downloads, personal home, or removable drive paths in service mode.

### Output Files

- CADAir must create one request directory under `/data/deliveries/apps/cadair_translate/<user_id>/<yyyy-mm-dd>/<request_id>/`.
- Final translated DXF must be written to the request directory.
- Intermediate extraction and translated JSON files should be written under a request-scoped work directory inside the request directory, for example `work/<input_stem>.extract.json` and `work/<input_stem>.translated.json`.
- If `layout_check=true`, write `layout_report.json` to the request directory.
- If `shrink=true`, write the shrunk DXF to the request directory and make it the primary output.
- Always write `result.json` and `manifest.json` to the request directory.
- CADAir must return output paths to Gateway and must not write OneDrive paths itself.

## Environment Variables

```env
APP_ID=your_baidu_app_id
SEC_KEY=your_baidu_secret_key
ODA_PATH=/opt/oda/ODAFileConverter.AppImage
TRANSLATE_SOURCE=zh
TRANSLATE_TARGET=en
TRANSLATE_QPS=1.0
TRANSLATE_DOMAIN=machinery
GLOSSARY_FILE=/data/config/cad_glossary_zh-en.json
GLOSSARY_JSON=
CADAIR_APP_ID=cadair_translate
CADAIR_OUTPUT_ROOT=/data/deliveries/apps
CADAIR_UPLOAD_ROOT=/data/uploads
CADAIR_ALLOWED_INPUT_ROOTS=/data/uploads,/data/document-intelligence,/data/deliveries
CADAIR_WORK_ROOT=
CADAIR_LOG_DIR=/data/deliveries/apps/cadair_translate/_logs
```

Notes:

- `APP_ID` and `SEC_KEY` are secrets and must not be committed with real values.
- `CADAIR_WORK_ROOT` can be empty; service mode should default to a request-scoped `work/` directory under the delivery request directory.
- `CADAIR_LOG_DIR` should be configurable so container logs and optional file logs do not write into the repository root.

## Docker Tasks

- [ ] Use `python:3.13-slim` because `pyproject.toml` currently requires Python `>=3.13`.
- [ ] Install runtime libraries needed by ODA on Linux, including `xvfb`, `libgl1`, and `libglib2.0-0`.
- [ ] Do not copy real ODA binaries or secrets into the image.
- [ ] Mount `/data/uploads` read-only.
- [ ] Mount `/data/document-intelligence` read-only if used.
- [ ] Mount `/data/deliveries` read-write.
- [ ] Mount platform config or glossary directory read-only.
- [ ] Expose port `8101`.
- [ ] Start with `uvicorn cadair.service:app --host 0.0.0.0 --port 8101`.

## App Integration Directory Tasks

Create:

```text
app-integrations/
  registry.yaml
  cadair-translate/
    manifest.yaml
    README.zh-CN.md
    api/
      openapi.json
      sample-request.json
      sample-response.json
    deploy/
      docker-compose.yml
      .env.example
      volumes.md
    gateway/
      skill.json
      adapter.md
    dify/
      workflow-notes.md
    portal/
      ui-spec.md
    ops/
      RUNBOOK.zh-CN.md
      CHANGELOG.md
    tests/
      check_health.sh
      check_run.sh
```

## Internal Code Audit Findings

### Must Fix Before Service Integration

- [x] `cadair/cli.py:67-68` defaults intermediate work files to `<input_dir>/.cadair-work`. In service mode the input path is likely under read-only `/data/uploads`, so work files must be redirected to the request delivery directory or `CADAIR_WORK_ROOT`.
- [x] `dwgtranslator/manager.py:13-19` configures `logging.FileHandler('translation.log')`, which writes into the current working directory at import time. Replace with configurable logging or remove the file handler for service mode.
- [x] `dwgtranslator/core.py:33-35` and `dwgtranslator/core.py:95-97` hardcode `/tmp/runtime-chongjibo`. Replace with `XDG_RUNTIME_DIR` from environment, defaulting to `/tmp/runtime-cadair`.
- [ ] `dwgtranslator/core.py:67-80` creates converted DXF files with `tempfile.mkstemp()` when no output path is provided. Service flows should always provide request-scoped output paths to avoid unmanaged temp outputs.
- [x] `dwgtranslator/core.py:106-112` uses a hardcoded ODA timeout of `60` seconds. Service mode should allow `CADAIR_ODA_TIMEOUT_SECONDS`, likely default `120` or higher for large DWG files.
- [x] `cadair/oda.py:55` uses a hardcoded ODA timeout of `120` seconds. Make this configurable for service deployments.
- [ ] `dwgtranslator/core.py:36-38`, `read()`, `save()`, and writeback code use `print()` for operational messages. Service mode should use structured logging and avoid leaking internal paths or exception details to users.

### Should Fix Or Contain

- [ ] `examples/*.py` hardcode `data/...` demo inputs and outputs. This is acceptable for examples, but service docs should not point users to these scripts for production.
- [ ] `tests/test_complete_flow.py` hardcodes `data/20260123.dwg`, `data/20260123_translated.dxf`, and `/tmp/runtime-chongjibo`. Keep out of service CI unless made environment-aware.
- [ ] `dwg-utils/dwg2json.py` hardcodes `../20260123.dwg` and `output.json` in its script entry block. This is unrelated to the service path but should remain outside production service wiring.
- [ ] `dwgtranslator/core.py:125-133` rewrites `.dwg` suffix to `.dxf` with string replace. The current DWG/DXF direct patch path usually bypasses this for final output, but service code should pass `.dxf` output paths explicitly.
- [ ] `cadair/oda.py:28-29` defaults output to input sibling when `output_path=None`. Service code must never call it with `None` because `/data/uploads` should be read-only.
- [ ] `examples/baidu_async_translate.py:41-59` prompts interactively for missing ODA or Baidu credentials. Service code must fail with `invalid_input` or `upstream_error`; no interactive prompts.

### Existing Code That Is Already Suitable

- `cadair translate` accepts explicit input, output, work dir, extract JSON, translated JSON, engine, glossary file, and glossary JSON parameters.
- `TextWriter.patch_dxf_file()` accepts explicit source and output paths and creates the output parent directory.
- `cadair layout` accepts explicit input, output, and JSON report paths.
- `cadair/oda.py` already writes to an explicit output path when provided and uses `/tmp/runtime-cadair` as the ODA runtime default.
- The final DXF output can already avoid `ezdxf.saveas()` for DWG/DXF translation paths.

## Suggested Service Workflow

1. Validate `request_id`, `user_id`, `skill_id`, and exactly one input CAD file.
2. Resolve and validate input file path under `CADAIR_ALLOWED_INPUT_ROOTS`.
3. Create request directory under `CADAIR_OUTPUT_ROOT`.
4. Create request work directory under the request directory.
5. Build deterministic output filenames from sanitized input stem:
   - `<stem>_translated.dxf`
   - `<stem>_translated_shrunk.dxf` if shrink is enabled
   - `work/<stem>.extract.json`
   - `work/<stem>.translated.json`
   - `layout_report.json` if layout check is enabled
   - `shrink_report.json` if shrink is enabled
   - `result.json`
   - `manifest.json`
6. Run extraction, translation, and direct DXF patch writeback using existing CADAir logic.
7. Run layout diagnostics if requested.
8. Run shrink if requested and make the shrunk DXF the primary deliverable.
9. Write `result.json` with structured counters and output metadata.
10. Write `manifest.json` using the AI platform delivery manifest format.
11. Return the standard `/v1/run` response.

## Error Mapping

- `invalid_input`: missing file, multiple files, missing required params, unsupported extension, invalid glossary JSON.
- `file_not_found`: input file path does not exist.
- `file_type_not_supported`: input is not `.dwg` or `.dxf`.
- `permission_denied`: input or glossary file path is outside allowed roots.
- `upstream_timeout`: ODA or translation API timeout.
- `upstream_error`: ODA conversion failure or translation API failure.
- `internal_error`: unexpected service failure.

## Test Plan

- [x] Unit test `/health` with `TestClient`.
- [x] Unit test `/v1/run` rejects empty `input.files`.
- [x] Unit test `/v1/run` rejects unsupported file extensions.
- [x] Unit test `/v1/run` rejects paths outside allowed roots.
- [x] Unit test `/v1/run` returns `file_not_found` for missing allowed path.
- [x] Unit test `/v1/run` succeeds with `tests/data/simple_case.oda.dxf` copied or mounted under an allowed test upload root and `engine=mock`.
- [ ] Unit test request-level `params.glossary_json` fixed translation behavior.
- [x] Unit test outputs are written under the configured delivery root.
- [x] Keep existing regression tests: `tests.test_simple_case_regression` and `tests.test_translation_filter`.

## Validation Commands

```bash
uv run pytest tests/test_service_api.py
uv run pytest tests/test_simple_case_regression.py
uv run pytest tests/test_translation_filter.py
uv run uvicorn cadair.service:app --host 0.0.0.0 --port 8101
curl http://localhost:8101/health
```

## HTTP Service V1 Validation Notes

Completed on 2026-05-07 on branch `feature/http-service-v1`.

Automated tests passed with the Tsinghua PyPI mirror:

```bash
uv lock --index-url https://pypi.tuna.tsinghua.edu.cn/simple
uv run --index-url https://pypi.tuna.tsinghua.edu.cn/simple pytest tests/test_service_api.py
uv run --index-url https://pypi.tuna.tsinghua.edu.cn/simple pytest tests/test_translation_filter.py
uv run --index-url https://pypi.tuna.tsinghua.edu.cn/simple pytest tests/test_simple_case_regression.py
```

Results:

- `tests/test_service_api.py`: 6 passed.
- `tests/test_translation_filter.py`: 17 passed.
- `tests/test_simple_case_regression.py`: 8 passed.

Manual smoke tests using `data/20260123.dwg` also passed:

- `engine=mock`, `layout_check=true`, `shrink=true`: completed in about 8.5 seconds, extracted 975 text entries, wrote back 327 translated handles, detected 34 layout overflows, and patched 3 shrink actions.
- `engine=baidu_field`, `domain=machinery`, `layout_check=true`, `shrink=true`: completed in about 111 seconds, extracted 975 text entries, wrote back 327 translated handles, detected 136 layout overflows, and patched 86 shrink actions.

Observed issue:

- During the `baidu_field` smoke run, the translator logged one `请求失败:` line without exception details, but the overall request completed successfully. A temporary excerpt was saved outside the repository at `/tmp/opencode/cadair-service-smoke/baidu-field-error-log-excerpt.txt`. Follow-up should improve Baidu translator error diagnostics without logging secrets.

Docker validation:

```bash
docker compose build
docker compose up
curl http://localhost:8101/health
```

## First Version Boundaries

- Do not implement real background job queue in the first version.
- Do not integrate directly with Gateway database tables.
- Do not write OneDrive directories directly.
- Do not implement Portal UI code in this repository.
- Do not accept multipart uploads directly; Gateway should provide platform file paths under `/data/uploads`.
- Do not support multiple input CAD files in one request until the single-file flow is stable.
- Do not commit real ODA binaries, Baidu keys, or customer drawings into the image or repository.
