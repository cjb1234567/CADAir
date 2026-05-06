from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "tests" / "data"
DWG_INPUT = DATA_DIR / "simple_case.dwg"
DXF_INPUT = DATA_DIR / "simple_case.oda.dxf"


def ensure_project_imports() -> None:
    root = str(ROOT_DIR)
    if root not in sys.path:
        sys.path.insert(0, root)


def require_inputs() -> None:
    missing = [str(path) for path in (DWG_INPUT, DXF_INPUT) if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing input files: {', '.join(missing)}")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def strip_entity_refs(bundles: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for handle, data in sorted(bundles.items()):
        result[handle] = {k: v for k, v in data.items() if k != "entity"}
    return result


def summarize_bundles(bundles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    type_counts = Counter(data.get("type", "UNKNOWN") for data in bundles.values())
    raw_multileaders = sum(1 for data in bundles.values() if data.get("raw_dxf"))
    return {
        "total": len(bundles),
        "type_counts": dict(sorted(type_counts.items())),
        "raw_multileaders": raw_multileaders,
        "handles": sorted(bundles),
    }


def translated_text(original: str) -> str:
    return f"TT::{original}"


def expected_dxf_value(entity_type: str | None, value: str | None) -> str | None:
    if value is None:
        return None
    if entity_type == "TEXT" or entity_type == "ATTRIB":
        return " ".join(str(value).splitlines()).strip()
    if entity_type == "MTEXT" or entity_type == "MULTILEADER":
        return str(value).replace("\r\n", "\\P").replace("\r", "\\P").replace("\n", "\\P")
    return value


def build_translated_bundles(extracted: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    translated: dict[str, dict[str, Any]] = {}
    for handle, data in sorted(extracted.items()):
        original = data.get("plain_content") or data.get("content") or ""
        translated[handle] = {
            **data,
            "original": original,
            "translated": translated_text(original),
        }
    return translated


def index_dxf_entities(path: Path) -> dict[str, dict[str, Any]]:
    lines = path.read_text(encoding="utf-8", errors="surrogateescape").splitlines()
    entities: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None

    for i in range(0, len(lines) - 1, 2):
        code = lines[i].strip()
        value = lines[i + 1]

        if code == "0":
            if current and current.get("handle"):
                entities[current["handle"].upper()] = current
            current = {"type": value.strip(), "handle": None, "groups": {}}
            continue

        if current is None:
            continue

        if code == "5" and current.get("handle") is None:
            current["handle"] = value.strip()
        current["groups"].setdefault(code, []).append(value)

    if current and current.get("handle"):
        entities[current["handle"].upper()] = current

    return entities


def observe_translated_handles(dxf_path: Path, translated: dict[str, dict[str, Any]]) -> dict[str, Any]:
    entities = index_dxf_entities(dxf_path)
    observations: dict[str, Any] = {}

    for handle, data in sorted(translated.items()):
        entity = entities.get(handle.upper())
        entity_type = data.get("type")
        group_code = "304" if entity_type == "MULTILEADER" else "1"
        values = entity.get("groups", {}).get(group_code, []) if entity else []
        expected = expected_dxf_value(entity_type, data.get("translated"))
        observations[handle] = {
            "type": entity_type,
            "group_code": group_code,
            "found": entity is not None,
            "values": values,
            "expected": expected,
            "contains_expected": expected in values,
        }

    return {
        "dxf_path": str(dxf_path.relative_to(ROOT_DIR)),
        "total_observed": len(observations),
        "matched_expected": sum(1 for item in observations.values() if item["contains_expected"]),
        "entities": observations,
    }
