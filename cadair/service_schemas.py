from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class PlatformFile(BaseModel):
    path: str
    filename: str | None = None
    mime_type: str | None = None


class RunParams(BaseModel):
    engine: Literal["mock", "baidu_general", "baidu_field"] = "mock"
    source: str | None = None
    target: str | None = None
    app_id: str | None = None
    app_key: str | None = None
    domain: str | None = None
    qps: float | None = None
    max_concurrent: int = 1
    mock_prefix: str = ""
    glossary_file: str | None = None
    glossary_json: dict[str, Any] | list[Any] | str | None = None
    layout_check: bool = False
    shrink: bool = False
    scale_threshold: float | None = None
    min_height: float = 2.0
    min_scale: float = 0.65


class RunInput(BaseModel):
    text: str | None = None
    files: list[PlatformFile] = Field(default_factory=list)
    params: RunParams = Field(default_factory=RunParams)


class RunContext(BaseModel):
    source: str | None = None
    timezone: str | None = None
    trace_id: str | None = None


class DeliveryOptions(BaseModel):
    auto_deliver: bool = True
    title: str | None = None
    formats: list[str] = Field(default_factory=list)


class RunRequest(BaseModel):
    request_id: str
    user_id: str
    skill_id: str
    input: RunInput = Field(default_factory=RunInput)
    context: RunContext = Field(default_factory=RunContext)
    delivery: DeliveryOptions = Field(default_factory=DeliveryOptions)


class OutputFile(BaseModel):
    path: str
    filename: str
    mime_type: str


class ErrorInfo(BaseModel):
    code: str
    message: str
    retryable: bool = False
    detail: dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    ok: bool
    status: Literal["success", "failed"]
    request_id: str
    provider: str | None = None
    model: str | None = None
    content: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    files: list[OutputFile] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    error: ErrorInfo | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    time: str
    dependencies: dict[str, Any] = Field(default_factory=dict)
