from __future__ import annotations

import json
import math
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import ezdxf
from ezdxf.addons import text2path
from ezdxf.math import BoundingBox

from dwgtranslator.writeback import TextWriter, detect_dxf_encoding


@dataclass(frozen=True)
class Segment:
    x1: float
    y1: float
    x2: float
    y2: float
    handle: str
    layer: str

    def is_vertical(self, tol: float) -> bool:
        return abs(self.x1 - self.x2) <= tol and abs(self.y1 - self.y2) > tol

    def is_horizontal(self, tol: float) -> bool:
        return abs(self.y1 - self.y2) <= tol and abs(self.x1 - self.x2) > tol

    @property
    def min_x(self) -> float:
        return min(self.x1, self.x2)

    @property
    def max_x(self) -> float:
        return max(self.x1, self.x2)

    @property
    def min_y(self) -> float:
        return min(self.y1, self.y2)

    @property
    def max_y(self) -> float:
        return max(self.y1, self.y2)


@dataclass(frozen=True)
class Box:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    def inset(self, ratio: float) -> "Box":
        dx = self.width * ratio
        dy = self.height * ratio
        return Box(self.min_x + dx, self.min_y + dy, self.max_x - dx, self.max_y - dy)


@dataclass(frozen=True)
class TextReport:
    handle: str
    space: str
    entity_type: str
    layer: str
    text: str
    height: float | None
    bbox: Box | None
    container: Box | None
    safe_container: Box | None
    overflow: bool
    overflow_sides: list[str]
    required_scale: float | None
    reason: str | None = None


@dataclass(frozen=True)
class ShrinkAction:
    handle: str
    text: str
    entity_type: str
    layer: str
    old_height: float
    new_height: float
    required_scale: float
    applied_scale: float
    clamped_to_min: bool
    still_overflows: bool


def iter_spaces(doc: ezdxf.document.Drawing, include_anonymous_blocks: bool):
    for layout in doc.layouts:
        yield f"layout:{layout.name}", layout
    for block in doc.blocks:
        if include_anonymous_blocks or not block.name.startswith("*"):
            yield f"block:{block.name}", block


def entity_handle(entity) -> str:
    return getattr(entity.dxf, "handle", "") or ""


def entity_layer(entity) -> str:
    return getattr(entity.dxf, "layer", "") or ""


def line_segments(entity) -> list[Segment]:
    handle = entity_handle(entity)
    layer = entity_layer(entity)
    if entity.dxftype() == "LINE":
        start = entity.dxf.start
        end = entity.dxf.end
        return [Segment(start.x, start.y, end.x, end.y, handle, layer)]
    if entity.dxftype() != "LWPOLYLINE":
        return []
    points = [(point[0], point[1]) for point in entity.get_points()]
    if len(points) < 2:
        return []
    pairs = list(zip(points, points[1:]))
    if entity.closed:
        pairs.append((points[-1], points[0]))
    return [Segment(a[0], a[1], b[0], b[1], handle, layer) for a, b in pairs]


def collect_segments(space) -> list[Segment]:
    segments: list[Segment] = []
    for entity in space:
        segments.extend(line_segments(entity))
    return segments


def text_value(entity) -> str:
    if entity.dxftype() == "TEXT":
        return entity.dxf.text or ""
    if entity.dxftype() == "MTEXT":
        return entity.plain_text() if hasattr(entity, "plain_text") else entity.text
    return ""


def text_anchor(entity, bbox: Box | None) -> tuple[float, float] | None:
    if bbox is not None:
        return ((bbox.min_x + bbox.max_x) / 2.0, (bbox.min_y + bbox.max_y) / 2.0)
    point = None
    if entity.dxftype() == "TEXT" and entity.dxf.hasattr("align_point"):
        point = entity.dxf.align_point
    elif entity.dxf.hasattr("insert"):
        point = entity.dxf.insert
    if point is None:
        return None
    return (point.x, point.y)


def bbox_from_text2path(entity, flattening_distance: float) -> Box | None:
    try:
        paths = text2path.make_paths_from_entity(entity)
    except Exception:
        return None
    vertices = []
    for path in paths:
        try:
            vertices.extend(path.flattening(distance=flattening_distance))
        except Exception:
            continue
    box = BoundingBox(vertices)
    if not box.has_data:
        return None
    return Box(box.extmin.x, box.extmin.y, box.extmax.x, box.extmax.y)


def display_width_units(text: str) -> float:
    width = 0.0
    for char in text:
        code = ord(char)
        if char.isspace():
            width += 0.3
        elif 0x4E00 <= code <= 0x9FFF:
            width += 1.0
        elif char.isupper():
            width += 0.65
        elif char.islower() or char.isdigit():
            width += 0.55
        elif char in "-_/\\.,:;()[]{}#":
            width += 0.35
        else:
            width += 0.6
    return width


def estimated_text_bbox(entity) -> Box | None:
    if not entity.dxf.hasattr("insert") or not entity.dxf.hasattr("height"):
        return None
    insert = entity.dxf.insert
    height = float(entity.dxf.height)
    width_factor = float(entity.dxf.get("width", 1.0))
    width = display_width_units(text_value(entity)) * height * width_factor
    rotation = math.radians(float(entity.dxf.get("rotation", 0.0)))
    if abs(rotation) > 1e-9:
        return None
    return Box(insert.x, insert.y, insert.x + width, insert.y + height)


def text_bbox(entity, flattening_distance: float) -> Box | None:
    return bbox_from_text2path(entity, flattening_distance) or estimated_text_bbox(entity)


def find_container(anchor: tuple[float, float], segments: Iterable[Segment], tol: float) -> Box | None:
    x, y = anchor
    verticals = [seg for seg in segments if seg.is_vertical(tol) and seg.min_y - tol <= y <= seg.max_y + tol]
    horizontals = [seg for seg in segments if seg.is_horizontal(tol) and seg.min_x - tol <= x <= seg.max_x + tol]
    left = max((seg.x1 for seg in verticals if seg.x1 < x - tol), default=None)
    right = min((seg.x1 for seg in verticals if seg.x1 > x + tol), default=None)
    bottom = max((seg.y1 for seg in horizontals if seg.y1 < y - tol), default=None)
    top = min((seg.y1 for seg in horizontals if seg.y1 > y + tol), default=None)
    if left is None or right is None or bottom is None or top is None:
        return None
    if right <= left or top <= bottom:
        return None
    return Box(left, bottom, right, top)


def overflow_sides(text_box: Box, safe_box: Box, tol: float) -> list[str]:
    sides: list[str] = []
    if text_box.min_x < safe_box.min_x - tol:
        sides.append("left")
    if text_box.max_x > safe_box.max_x + tol:
        sides.append("right")
    if text_box.min_y < safe_box.min_y - tol:
        sides.append("bottom")
    if text_box.max_y > safe_box.max_y + tol:
        sides.append("top")
    return sides


def required_scale(text_box: Box, safe_box: Box) -> float | None:
    if text_box.width <= 0 or text_box.height <= 0 or safe_box.width <= 0 or safe_box.height <= 0:
        return None
    return min(1.0, safe_box.width / text_box.width, safe_box.height / text_box.height)


def check_doc(
    doc: ezdxf.document.Drawing,
    *,
    contains: str | None,
    margin_ratio: float,
    axis_tolerance: float,
    flattening_distance: float,
    include_anonymous_blocks: bool,
) -> list[TextReport]:
    reports: list[TextReport] = []
    for space_name, space in iter_spaces(doc, include_anonymous_blocks):
        segments = collect_segments(space)
        for entity in space:
            if entity.dxftype() not in {"TEXT", "MTEXT"}:
                continue
            value = text_value(entity).strip()
            if not value:
                continue
            if contains and contains not in value:
                continue
            box = text_bbox(entity, flattening_distance)
            anchor = text_anchor(entity, box)
            container = find_container(anchor, segments, axis_tolerance) if anchor else None
            safe_container = container.inset(margin_ratio) if container else None
            sides = overflow_sides(box, safe_container, axis_tolerance) if box and safe_container else []
            reports.append(
                TextReport(
                    handle=entity_handle(entity),
                    space=space_name,
                    entity_type=entity.dxftype(),
                    layer=entity_layer(entity),
                    text=value,
                    height=float(entity.dxf.height) if entity.dxf.hasattr("height") else None,
                    bbox=box,
                    container=container,
                    safe_container=safe_container,
                    overflow=bool(sides),
                    overflow_sides=sides,
                    required_scale=required_scale(box, safe_container) if box and safe_container and sides else None,
                    reason=None if container else "no_container_detected",
                )
            )
    return reports


def box_to_list(box: Box | None) -> list[float] | None:
    if box is None:
        return None
    return [box.min_x, box.min_y, box.max_x, box.max_y]


def report_to_dict(report: TextReport) -> dict:
    data = asdict(report)
    data["bbox"] = box_to_list(report.bbox)
    data["container"] = box_to_list(report.container)
    data["safe_container"] = box_to_list(report.safe_container)
    return data


def build_shrink_actions(
    reports: list[TextReport],
    *,
    scale_threshold: float,
    min_height: float,
    min_scale: float,
) -> list[ShrinkAction]:
    actions: list[ShrinkAction] = []
    for report in reports:
        if not report.overflow or report.entity_type != "TEXT":
            continue
        if report.height is None or report.required_scale is None:
            continue
        if report.required_scale >= scale_threshold:
            continue
        lower_bound = max(min_height, report.height * min_scale)
        target_height = report.height * report.required_scale
        new_height = max(target_height, lower_bound)
        applied_scale = new_height / report.height if report.height else 1.0
        actions.append(
            ShrinkAction(
                handle=report.handle,
                text=report.text,
                entity_type=report.entity_type,
                layer=report.layer,
                old_height=float(report.height),
                new_height=float(new_height),
                required_scale=float(report.required_scale),
                applied_scale=float(applied_scale),
                clamped_to_min=bool(new_height > target_height),
                still_overflows=bool(applied_scale > report.required_scale),
            )
        )
    return actions


def format_float(value: float) -> str:
    return f"{value:.12g}"


def replace_first_group_value(lines: list[str], start: int, end: int, code: str, value: str) -> bool:
    newline = "\r\n" if lines[start].endswith("\r\n") else "\n"
    for i in range(start, end - 1, 2):
        if lines[i].strip() == code:
            lines[i + 1] = value + newline
            return True
    return False


def patch_text_heights(source_path: Path, output_path: Path, actions: list[ShrinkAction]) -> int:
    encoding = detect_dxf_encoding(str(source_path))
    with source_path.open("r", encoding=encoding, errors="surrogateescape", newline="") as f:
        lines = f.readlines()
    ranges = TextWriter()._index_entity_ranges(lines)
    patched = 0
    for action in actions:
        entity_range = ranges.get(action.handle.upper())
        if not entity_range:
            continue
        start, end = entity_range
        if replace_first_group_value(lines, start, end, "40", format_float(action.new_height)):
            patched += 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding=encoding, errors="surrogateescape", newline="") as f:
        f.writelines(lines)
    return patched


def copy_if_no_actions(source_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, output_path)


def write_check_report(path: Path, input_path: Path, reports: list[TextReport]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": "check",
        "input": str(input_path),
        "total": len(reports),
        "containers_found": sum(1 for report in reports if report.container is not None),
        "overflows": sum(1 for report in reports if report.overflow),
        "reports": [report_to_dict(report) for report in reports],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_shrink_report(
    path: Path,
    source: Path,
    output: Path | None,
    actions: list[ShrinkAction],
    patched: int | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": "shrink",
        "source": str(source),
        "output": str(output) if output else None,
        "actions": len(actions),
        "patched": patched,
        "items": [asdict(action) for action in actions],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def print_check_summary(reports: list[TextReport], limit: int) -> None:
    with_container = sum(1 for report in reports if report.container is not None)
    overflows = [report for report in reports if report.overflow]
    print(f"checked_texts={len(reports)} containers_found={with_container} overflows={len(overflows)}")
    for report in overflows[:limit]:
        scale = "n/a" if report.required_scale is None else f"{report.required_scale:.3f}"
        print(
            f"overflow handle={report.handle} type={report.entity_type} layer={report.layer} "
            f"height={report.height} sides={','.join(report.overflow_sides)} required_scale={scale}"
        )
        print(f"  text={report.text}")
        print(f"  bbox={box_to_list(report.bbox)}")
        print(f"  container={box_to_list(report.container)}")
    if len(overflows) > limit:
        print(f"... {len(overflows) - limit} more overflows not shown")


def print_shrink_summary(actions: list[ShrinkAction], patched: int | None, limit: int) -> None:
    print(f"shrink_candidates={len(actions)}" + ("" if patched is None else f" patched={patched}"))
    for action in actions[:limit]:
        status = " clamped" if action.clamped_to_min else ""
        print(
            f"handle={action.handle} height={action.old_height:.6g}->{action.new_height:.6g} "
            f"required_scale={action.required_scale:.3f} applied_scale={action.applied_scale:.3f}{status}"
        )
        print(f"  text={action.text}")
    if len(actions) > limit:
        print(f"... {len(actions) - limit} more candidates not shown")
