from __future__ import annotations

import argparse
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import ezdxf
from fastapi import FastAPI

from cadair.cli import run_extract, run_translate_json, run_writeback
from cadair.layout import (
    build_shrink_actions,
    check_doc,
    copy_if_no_actions,
    patch_text_heights,
    write_check_report,
    write_shrink_report,
)
from cadair.service_schemas import ErrorInfo, HealthResponse, OutputFile, RunRequest, RunResponse


APP_VERSION = "0.1.0"
DEFAULT_APP_ID = "cadair_translate"
TZ = timezone(timedelta(hours=8), "Asia/Shanghai")
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")
logger = logging.getLogger("cadair.service")

app = FastAPI(title="CADAir Translate Service", version=APP_VERSION)


class ServiceException(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False, detail: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.detail = detail or {}


def env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def app_id() -> str:
    return env("CADAIR_APP_ID", DEFAULT_APP_ID) or DEFAULT_APP_ID


def now_iso() -> str:
    return datetime.now(TZ).isoformat()


def allowed_input_roots() -> list[Path]:
    value = env("CADAIR_ALLOWED_INPUT_ROOTS")
    if value:
        roots = [item.strip() for item in value.split(",") if item.strip()]
    else:
        roots = ["/data/uploads", "/data/document-intelligence", "/data/deliveries"]
    return [Path(root).expanduser().resolve(strict=False) for root in roots]


def output_root() -> Path:
    return Path(env("CADAIR_OUTPUT_ROOT", "/data/deliveries/apps") or "/data/deliveries/apps").expanduser()


def sanitize_component(value: str, fallback: str) -> str:
    sanitized = SAFE_NAME_RE.sub("_", value.strip()).strip("._-")
    return sanitized or fallback


def resolve_under_allowed(path_value: str, roots: list[Path]) -> Path:
    path = Path(path_value).expanduser().resolve(strict=False)
    for root in roots:
        if path == root or root in path.parents:
            return path
    raise ServiceException("permission_denied", "Input path is outside allowed roots")


def validate_request(req: RunRequest) -> tuple[Path, str]:
    if req.skill_id != app_id():
        raise ServiceException("invalid_input", "skill_id does not match this service")
    request_id = sanitize_component(req.request_id, "request")
    user_id = sanitize_component(req.user_id, "user")
    if request_id != req.request_id or user_id != req.user_id:
        raise ServiceException("invalid_input", "request_id and user_id may only contain safe path characters")
    if len(req.input.files) != 1:
        raise ServiceException("invalid_input", "Exactly one input CAD file is required")
    input_path = resolve_under_allowed(req.input.files[0].path, allowed_input_roots())
    suffix = input_path.suffix.lower()
    if suffix not in {".dwg", ".dxf"}:
        raise ServiceException("file_type_not_supported", "Only DWG and DXF inputs are supported")
    if not input_path.exists():
        raise ServiceException("file_not_found", "Input file does not exist")
    params = req.input.params
    if params.glossary_file:
        resolve_under_allowed(params.glossary_file, allowed_input_roots())
    if params.scale_threshold is not None and not (0 < params.scale_threshold <= 1):
        raise ServiceException("invalid_input", "scale_threshold must be in (0, 1]")
    if params.min_height < 0:
        raise ServiceException("invalid_input", "min_height must be non-negative")
    if not (0 < params.min_scale <= 1):
        raise ServiceException("invalid_input", "min_scale must be in (0, 1]")
    return input_path, input_path.stem


def request_dir(req: RunRequest) -> Path:
    date_part = datetime.now(TZ).strftime("%Y-%m-%d")
    return output_root() / app_id() / req.user_id / date_part / req.request_id


def glossary_json_value(value: Any) -> str | None:
    if value is None:
        return env("GLOSSARY_JSON")
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def translate_args(req: RunRequest, work_dir: Path, extract_json: Path, translated_json: Path) -> argparse.Namespace:
    params = req.input.params
    return argparse.Namespace(
        engine=params.engine,
        source=params.source,
        target=params.target,
        app_id=params.app_id,
        app_key=params.app_key,
        domain=params.domain,
        qps=params.qps,
        max_concurrent=params.max_concurrent,
        mock_prefix=params.mock_prefix,
        glossary_json=glossary_json_value(params.glossary_json),
        glossary_file=params.glossary_file or env("GLOSSARY_FILE"),
        oda_path=env("ODA_PATH"),
        work_dir=work_dir,
        extract_json=extract_json,
        translated_json=translated_json,
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def as_output_file(path: Path, mime_type: str) -> OutputFile:
    return OutputFile(path=str(path), filename=path.name, mime_type=mime_type)


def emit_log(req: RunRequest, stage: str, status: str, started: float, error_code: str | None = None) -> None:
    logger.info(
        json.dumps(
            {
                "request_id": req.request_id,
                "user_id": req.user_id,
                "skill_id": req.skill_id,
                "trace_id": req.context.trace_id,
                "stage": stage,
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "status": status,
                "error_code": error_code,
            },
            ensure_ascii=False,
        )
    )


def run_cadair(req: RunRequest) -> RunResponse:
    started = time.perf_counter()
    input_path, input_stem = validate_request(req)
    safe_stem = sanitize_component(input_stem, "input")
    out_dir = request_dir(req)
    work_dir = out_dir / "work"
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    extract_json = work_dir / f"{safe_stem}.extract.json"
    translated_json = work_dir / f"{safe_stem}.translated.json"
    translated_dxf = out_dir / f"{safe_stem}_translated.dxf"
    primary_dxf = translated_dxf
    params = req.input.params

    args = translate_args(req, work_dir, extract_json, translated_json)
    try:
        run_extract(input_path, extract_json, args.oda_path)
        run_translate_json(args, extract_json, translated_json)
        run_writeback(input_path, translated_json, translated_dxf, args.oda_path, work_dir)
    except TimeoutError as exc:
        raise ServiceException("upstream_timeout", "CAD translation timed out", retryable=True) from exc
    except ValueError as exc:
        raise ServiceException("invalid_input", str(exc)) from exc

    layout_overflow_count = None
    files: list[OutputFile] = [as_output_file(primary_dxf, "application/dxf")]

    if params.layout_check or params.shrink:
        layout_report = out_dir / "layout_report.json"
        doc = ezdxf.readfile(primary_dxf)
        reports = check_doc(
            doc,
            contains=None,
            margin_ratio=0.05,
            axis_tolerance=1e-3,
            flattening_distance=0.1,
            include_anonymous_blocks=True,
        )
        layout_overflow_count = sum(1 for report in reports if report.overflow)
        if params.layout_check:
            write_check_report(layout_report, primary_dxf, reports)
            files.append(as_output_file(layout_report, "application/json"))
        if params.shrink:
            shrink_report = out_dir / "shrink_report.json"
            shrunk_dxf = out_dir / f"{safe_stem}_translated_shrunk.dxf"
            actions = build_shrink_actions(
                reports,
                scale_threshold=params.scale_threshold if params.scale_threshold is not None else 1.0,
                min_height=params.min_height,
                min_scale=params.min_scale,
            )
            if actions:
                patched = patch_text_heights(primary_dxf, shrunk_dxf, actions)
            else:
                copy_if_no_actions(primary_dxf, shrunk_dxf)
                patched = 0
            write_shrink_report(shrink_report, primary_dxf, shrunk_dxf, actions, patched)
            primary_dxf = shrunk_dxf
            files[0] = as_output_file(primary_dxf, "application/dxf")
            files.append(as_output_file(shrink_report, "application/json"))

    data = {
        "input_file": req.input.files[0].filename or input_path.name,
        "output_file": primary_dxf.name,
        "engine": params.engine,
        "source": params.source or env("TRANSLATE_SOURCE", "auto") or "auto",
        "target": params.target or env("TRANSLATE_TARGET", "en") or "en",
        "layout_overflow_count": layout_overflow_count,
        "shrink_applied": bool(params.shrink),
    }
    result_path = out_dir / "result.json"
    manifest_path = out_dir / "manifest.json"
    duration_ms = int((time.perf_counter() - started) * 1000)
    result_payload = {
        "ok": True,
        "status": "success",
        "request_id": req.request_id,
        "provider": app_id(),
        "model": params.engine,
        "content": "CAD 图纸翻译完成，已生成 DXF 输出文件。",
        "data": data,
        "metrics": {"duration_ms": duration_ms, "input_files": 1},
    }
    write_json(result_path, result_payload)
    files.extend([as_output_file(result_path, "application/json"), as_output_file(manifest_path, "application/json")])
    manifest = {
        "app_id": app_id(),
        "request_id": req.request_id,
        "user_id": req.user_id,
        "skill_id": req.skill_id,
        "title": req.delivery.title or "CAD 图纸翻译结果",
        "created_at": now_iso(),
        "source": req.context.source,
        "trace_id": req.context.trace_id,
        "files": [file.model_dump() for file in files if file.path != str(manifest_path)],
    }
    write_json(manifest_path, manifest)

    metrics = {"duration_ms": duration_ms, "input_files": 1, "output_files": len(files)}
    emit_log(req, "run", "success", started)
    return RunResponse(
        ok=True,
        status="success",
        request_id=req.request_id,
        provider=app_id(),
        model=params.engine,
        content="CAD 图纸翻译完成，已生成 DXF 输出文件。",
        data=data,
        files=files,
        metrics=metrics,
    )


def failed_response(req: RunRequest, exc: ServiceException, started: float) -> RunResponse:
    emit_log(req, "run", "failed", started, exc.code)
    return RunResponse(
        ok=False,
        status="failed",
        request_id=req.request_id,
        error=ErrorInfo(code=exc.code, message=exc.message, retryable=exc.retryable, detail=exc.detail),
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    oda_path = env("ODA_PATH")
    root = output_root()
    return HealthResponse(
        status="ok",
        service=app_id(),
        version=APP_VERSION,
        time=now_iso(),
        dependencies={
            "oda_path_configured": bool(oda_path),
            "oda_path_exists": bool(oda_path and Path(oda_path).exists()),
            "output_root": str(root),
            "output_root_writable": root.exists() and os.access(root, os.W_OK),
            "allowed_input_roots": [str(path) for path in allowed_input_roots()],
        },
    )


@app.post("/v1/run", response_model=RunResponse)
def run(req: RunRequest) -> RunResponse:
    started = time.perf_counter()
    try:
        return run_cadair(req)
    except ServiceException as exc:
        return failed_response(req, exc, started)
    except Exception as exc:  # pragma: no cover - exercised by platform smoke tests, not unit-specific
        logger.exception("cadair service internal error")
        return failed_response(req, ServiceException("internal_error", "Unexpected service error"), started)
