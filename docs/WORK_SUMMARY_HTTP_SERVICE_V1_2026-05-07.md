# Work Summary: HTTP Service V1

Date: 2026-05-07

Branch: `feature/http-service-v1`

## Goal

Implement the first FastAPI HTTP service layer for CADAir so AI Gateway can call CADAir as a standard file-processing skill.

The work follows:

- `TODO_INTEGRATION.md`
- `docs/integration/PYTHON-SCENARIO-INTEGRATION-STANDARD.zh-CN.md`
- `docs/integration/PYTHON-APP-MAINTENANCE-DIRECTORY-DESIGN.zh-CN.md`

## Implemented

Added `cadair/service_schemas.py` with Pydantic models for:

- Platform input files.
- `/v1/run` request params.
- Standard run request and response shapes.
- Standard output files and error payloads.
- `/health` response.

Added `cadair/service.py` with:

- `GET /health`.
- `POST /v1/run`.
- App ID validation for `cadair_translate`.
- Single-file request validation.
- `.dwg` and `.dxf` input support.
- Allowed input root enforcement via `CADAIR_ALLOWED_INPUT_ROOTS`.
- Request-scoped output directory under `CADAIR_OUTPUT_ROOT/cadair_translate/<user_id>/<yyyy-mm-dd>/<request_id>/`.
- Request-scoped `work/` directory.
- Existing CADAir extraction, translation, and DXF writeback flow reuse.
- Request-level `params.glossary_json` support.
- Optional `params.layout_check` support.
- Optional `params.shrink` support.
- `result.json` and `manifest.json` output.
- Standard `ok=false` service error responses.
- Structured service log line with `request_id`, `user_id`, `skill_id`, `trace_id`, `stage`, `duration_ms`, `status`, and `error_code`.

Updated dependencies in `pyproject.toml` and `uv.lock`:

- `fastapi>=0.110,<1`
- `uvicorn>=0.27,<1`
- `pydantic>=2,<3`
- `httpx>=0.27,<1`
- `pytest>=8,<9`

Added `tests/test_service_api.py` covering:

- `/health`.
- Empty `input.files` rejection.
- Unsupported file extension rejection.
- Allowed-root path rejection.
- Missing file under an allowed root.
- Successful mock DXF flow through `/v1/run`.
- Output files written under the configured delivery root.
- `result.json` and `manifest.json` generation.

## Validation

Dependency locking required a mirror because direct PyPI access was slow and timed out on several package index requests.

Successful lock command:

```bash
uv lock --index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

Automated tests passed:

```bash
uv run --index-url https://pypi.tuna.tsinghua.edu.cn/simple pytest tests/test_service_api.py
uv run --index-url https://pypi.tuna.tsinghua.edu.cn/simple pytest tests/test_translation_filter.py
uv run --index-url https://pypi.tuna.tsinghua.edu.cn/simple pytest tests/test_simple_case_regression.py
```

Results:

- `tests/test_service_api.py`: 6 passed.
- `tests/test_translation_filter.py`: 17 passed.
- `tests/test_simple_case_regression.py`: 8 passed.

Total focused validation: 31 passed.

## Manual Smoke Tests

The service was run locally on:

```text
http://127.0.0.1:8101
```

Smoke input:

```text
data/20260123.dwg
```

The input was copied to a platform-like upload root under `/tmp/opencode/cadair-service-smoke/uploads/`.

### Mock Engine

Request settings:

- `engine=mock`
- `source=zh`
- `target=en`
- `layout_check=true`
- `shrink=true`

Result:

- Request succeeded.
- Duration: about 8.5 seconds.
- Extracted text entries: 975.
- DXF writeback: 327/327 translated handles.
- Layout overflows: 34.
- Shrink actions patched: 3.
- Primary output: `20260123_translated_shrunk.dxf`.

### Baidu Field Engine

Request settings:

- `engine=baidu_field`
- `domain=machinery`
- `source=zh`
- `target=en`
- `qps=1.0`
- `max_concurrent=1`
- `layout_check=true`
- `shrink=true`

Result:

- Request succeeded.
- Duration: about 111 seconds.
- Extracted text entries: 975.
- DXF writeback: 327/327 translated handles.
- Layout overflows: 136.
- Shrink actions patched: 86.
- Primary output: `20260123_translated_shrunk.dxf`.

Observed issue:

- One translator-level error line appeared: `请求失败:`.
- The error line did not include exception type, status code, or upstream error code.
- The overall service request still completed successfully.
- Temporary log excerpt saved outside the repository: `/tmp/opencode/cadair-service-smoke/baidu-field-error-log-excerpt.txt`.

Follow-up:

- Improve Baidu translator error diagnostics without logging `APP_ID`, `SEC_KEY`, request signatures, or full customer text.

## Remaining Work

- Add Dockerfile and root `docker-compose.yml`.
- Add repository `.env.example` entries if more service-specific settings are introduced.
- Create `app-integrations/cadair-translate/` maintenance directory.
- Update `README.md` with service startup, request examples, Docker usage, and Gateway handoff notes.
- Improve Baidu translator error logging.
- Decide whether the first production deployment should stay synchronous or add `/v1/jobs` after Gateway integration feedback.
