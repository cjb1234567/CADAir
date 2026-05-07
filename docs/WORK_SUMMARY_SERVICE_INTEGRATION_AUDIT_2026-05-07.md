# Work Summary: Service Integration Audit Cleanup

Date: 2026-05-07

Branch: `feature/service-integration-audit-cleanup`

## Goal

Prepare CADAir internals and documentation for the planned FastAPI/Docker microservice integration into the AI platform.

The integration target follows:

- `docs/integration/PYTHON-SCENARIO-INTEGRATION-STANDARD.zh-CN.md`
- `docs/integration/PYTHON-APP-MAINTENANCE-DIRECTORY-DESIGN.zh-CN.md`

## Planning Added

Created `TODO_INTEGRATION.md` with the full integration plan for packaging CADAir as a platform-compatible microservice.

Key planned service conventions:

- FastAPI wrapper with `GET /health` and `POST /v1/run`.
- App ID and Skill ID: `cadair_translate`.
- Gateway uploads source files under `/data/uploads`.
- CADAir writes deliverables under `/data/deliveries/apps/cadair_translate/<user_id>/<yyyy-mm-dd>/<request_id>/`.
- Gateway owns OneDrive delivery; CADAir only returns output file paths.
- Request-level glossary input should support `input.params.glossary_json` and `input.params.glossary_file`.
- The first service version should stay synchronous and single-file, then add async jobs later if needed.

## Code Changes

### Configurable ODA Runtime Directory

Updated `dwgtranslator/core.py` to remove the hardcoded runtime directory `/tmp/runtime-chongjibo`.

New resolution order:

1. `XDG_RUNTIME_DIR`
2. `CADAIR_ODA_RUNTIME_DIR`
3. `/tmp/runtime-cadair`

This makes Linux and container runs more predictable and avoids project-specific temp paths.

### Configurable ODA Timeout

Updated both ODA conversion paths:

- `dwgtranslator/core.py`
- `cadair/oda.py`

New behavior:

- Default timeout is `120` seconds.
- Timeout can be configured with `CADAIR_ODA_TIMEOUT_SECONDS`.
- `cadair.oda.convert_dwg_to_dxf()` also accepts a direct `timeout` argument.
- `TranslationManager` now accepts `oda_timeout` and passes it into `DWGCore`.

This avoids fixed conversion limits for larger DWG files in service deployments.

### Service-Friendly Logging

Updated `dwgtranslator/manager.py` logging setup.

Previous behavior:

- Always created `translation.log` in the current working directory at import time.

New behavior:

- Logs to the process stream by default.
- Writes `translation.log` only when `CADAIR_LOG_DIR` is set.
- Creates `CADAIR_LOG_DIR` if needed.

This avoids writing logs into the repository root or container workdir unless explicitly configured.

### Work Directory Override

Updated `cadair/cli.py` so intermediate files can be redirected away from the input directory.

New behavior:

- `CADAIR_WORK_ROOT` overrides the default CLI work root.
- If `CADAIR_WORK_ROOT` is unset, historical behavior remains unchanged: `<input_dir>/.cadair-work`.
- `run_full_translate()` now passes the resolved work dir into writeback.
- `--work-dir` now also applies to DWG conversion during `--writeback-only`.

This is important for service mode because `/data/uploads` should be read-only.

## Documentation Changes

Updated `README.md` with:

- New service/container environment variables.
- `GLOSSARY_FILE` and `GLOSSARY_JSON` examples.
- `CADAIR_WORK_ROOT` usage for read-only upload roots.
- Service integration notes for `/data/uploads`, `/data/deliveries/apps`, Gateway delivery, and request-level glossary parameters.
- References to `TODO_INTEGRATION.md` and `docs/integration/`.

Updated `.env.example` with:

- `CADAIR_OUTPUT_ROOT`
- `CADAIR_UPLOAD_ROOT`
- `CADAIR_ALLOWED_INPUT_ROOTS`
- `CADAIR_WORK_ROOT`
- `CADAIR_LOG_DIR`
- `CADAIR_ODA_RUNTIME_DIR`
- `CADAIR_ODA_TIMEOUT_SECONDS`
- Clarification that `input.params.glossary_json` can be used by the future FastAPI service.

`TODO_INTEGRATION.md` was also updated to mark the completed audit cleanup items.

The real `.env` file was intentionally not read or modified because it may contain local secrets.

## Validation

Regression tests passed:

```bash
.venv/bin/python -m unittest tests.test_simple_case_regression
.venv/bin/python -m unittest tests.test_translation_filter
```

Results:

- `tests.test_simple_case_regression`: `OK`
- `tests.test_translation_filter`: `OK`

CLI work root override was verified:

```bash
CADAIR_WORK_ROOT=/tmp/opencode/cadair-work \
  .venv/bin/python -m cadair.cli translate \
  tests/data/simple_case.oda.dxf \
  /tmp/opencode/simple_case.workroot.dxf \
  --engine mock \
  --mock-prefix WR:: \
  --keep-work-files
```

Observed intermediate files under:

```text
/tmp/opencode/cadair-work/simple_case.oda/
```

Real Baidu async example was also verified:

```bash
.venv/bin/python examples/baidu_async_translate.py \
  data/20260123.dwg \
  --glossary-file config/cad_glossary_zh-en.json
```

Result:

- Translation completed successfully.
- Output file: `data/20260123_translated_translated.dxf`.
- Direct DXF patch writeback: `327/327` translated handles.
- Example confirmed glossary behavior such as `电源分配单元 -> Power Distribution Unit`.

## Notes

The existing `examples/baidu_async_translate.py` script still writes to `data/<stem>_translated.dxf` according to historical example behavior. This is acceptable for examples.

The future FastAPI wrapper should not reuse that output behavior directly. It should always create request-scoped output under `/data/deliveries/apps/cadair_translate/<user_id>/<yyyy-mm-dd>/<request_id>/`.

## Remaining Integration Work

- Add FastAPI dependencies and service schemas.
- Implement `cadair/service.py` with `/health` and `/v1/run`.
- Enforce allowed input root validation for `/data/uploads`, `/data/document-intelligence`, and `/data/deliveries`.
- Write request-scoped `result.json` and `manifest.json`.
- Add Dockerfile and docker-compose examples.
- Create `app-integrations/cadair-translate/` maintenance directory.
- Add service API tests.
- Update TODO completion status after the service wrapper lands.
