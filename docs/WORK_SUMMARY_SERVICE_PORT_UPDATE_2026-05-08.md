# Work Summary: Service Port Update

Date: 2026-05-08

Branch: `main`

Commit: `b907d56` (`docs: update CADAir service port`)

## Goal

Align CADAir service documentation and integration TODOs with the current required local service port `8030`.

The requested configuration cleanup covered:

- Target integration model default port.
- Docker expose and startup port guidance.
- Local validation commands.
- Docker validation health check.

## Changes

Updated `TODO_INTEGRATION.md`:

- Changed the Target Integration Model default port from `8101` to `8030`.
- Changed Docker Tasks expose port from `8101` to `8030`.
- Changed Docker Tasks uvicorn startup command from `--port 8101` to `--port 8030`.
- Changed Validation Commands uvicorn startup command from `--port 8101` to `--port 8030`.
- Changed Validation Commands health check from `http://localhost:8101/health` to `http://localhost:8030/health`.
- Changed Docker validation health check from `http://localhost:8101/health` to `http://localhost:8030/health`.

Updated `README.md`:

- Changed the local FastAPI service startup example to use port `8030`.
- Changed the health check example to use `http://127.0.0.1:8030/health`.
- Changed the synchronous `/v1/run` curl example to use `http://127.0.0.1:8030/v1/run`.

## Validation

Confirmed `TODO_INTEGRATION.md` contains only the expected CADAir service port references:

```text
- Default port: `8030`.
- [ ] Expose port `8030`.
- [ ] Start with `uvicorn cadair.service:app --host 0.0.0.0 --port 8030`.
uv run uvicorn cadair.service:app --host 0.0.0.0 --port 8030
curl http://localhost:8030/health
curl http://localhost:8030/health
```

Confirmed `README.md` service examples now use `8030`:

```text
uv run uvicorn cadair.service:app --host 0.0.0.0 --port 8030
curl http://127.0.0.1:8030/health
curl -X POST http://127.0.0.1:8030/v1/run \
```

## Notes

Repository-wide search still found unrelated `8101` occurrences outside this CADAir port update scope:

- `docs/integration/PYTHON-SCENARIO-INTEGRATION-STANDARD.zh-CN.md` uses `8101` in generic integration standard examples.
- DXF data files contain numeric substrings that include `8101`; these are drawing data, not service port configuration.
- Existing historical work summaries may still mention prior smoke test URLs for the earlier `8101` run context.

These were intentionally left unchanged to avoid rewriting historical or unrelated reference material.
