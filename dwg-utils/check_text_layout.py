from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import ezdxf
from ezdxf.addons import text2path
from ezdxf.math import BoundingBox


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

    def contains(self, other: "Box", tol: float) -> bool:
        return (
            other.min_x >= self.min_x - tol
            and other.max_x <= self.max_x + tol
            and other.min_y >= self.min_y - tol
            and other.max_y <= self.max_y + tol
        )


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
        # Keep the fallback conservative for rotated text.
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


def print_summary(reports: list[TextReport], limit: int) -> None:
    with_container = sum(1 for report in reports if report.container is not None)
    overflows = [report for report in reports if report.overflow]
    print(f"checked_texts={len(reports)} containers_found={with_container} overflows={len(overflows)}")
    for report in overflows[:limit]:
        scale = "n/a" if report.required_scale is None else f"{report.required_scale:.3f}"
        bbox = box_to_list(report.bbox)
        container = box_to_list(report.container)
        print(
            f"overflow handle={report.handle} type={report.entity_type} layer={report.layer} "
            f"height={report.height} sides={','.join(report.overflow_sides)} required_scale={scale}"
        )
        print(f"  text={report.text}")
        print(f"  bbox={bbox}")
        print(f"  container={container}")
    if len(overflows) > limit:
        print(f"... {len(overflows) - limit} more overflows not shown")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check translated CAD text overflow against nearby frame lines.")
    parser.add_argument("input", type=Path, help="Input DXF file")
    parser.add_argument("--contains", help="Only check text containing this substring")
    parser.add_argument("--json", type=Path, help="Write full JSON report")
    parser.add_argument("--limit", type=int, default=20, help="Maximum overflow rows to print")
    parser.add_argument("--margin-ratio", type=float, default=0.05, help="Container inset ratio used as safety margin")
    parser.add_argument("--axis-tolerance", type=float, default=1e-3, help="Tolerance for horizontal/vertical line checks")
    parser.add_argument("--flattening-distance", type=float, default=0.1, help="Path flattening distance for text2path bbox")
    parser.add_argument(
        "--skip-anonymous-blocks",
        action="store_true",
        help="Skip anonymous block definitions such as *U4. By default they are checked because ODA output often stores title blocks there.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    doc = ezdxf.readfile(args.input)
    reports = check_doc(
        doc,
        contains=args.contains,
        margin_ratio=args.margin_ratio,
        axis_tolerance=args.axis_tolerance,
        flattening_distance=args.flattening_distance,
        include_anonymous_blocks=not args.skip_anonymous_blocks,
    )
    print_summary(reports, args.limit)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "input": str(args.input),
            "total": len(reports),
            "containers_found": sum(1 for report in reports if report.container is not None),
            "overflows": sum(1 for report in reports if report.overflow),
            "reports": [report_to_dict(report) for report in reports],
        }
        args.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote_json={args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
