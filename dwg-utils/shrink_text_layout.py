from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import ezdxf


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dwgtranslator.writeback import TextWriter, detect_dxf_encoding  # noqa: E402


def load_check_text_layout_module():
    module_path = Path(__file__).with_name("check_text_layout.py")
    spec = importlib.util.spec_from_file_location("check_text_layout", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


layout = load_check_text_layout_module()


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


def format_float(value: float) -> str:
    return f"{value:.12g}"


def build_actions(
    reports,
    *,
    scale_threshold: float,
    min_height: float,
    min_scale: float,
) -> list[ShrinkAction]:
    actions: list[ShrinkAction] = []
    for report in reports:
        if not report.overflow:
            continue
        if report.entity_type != "TEXT":
            continue
        if report.height is None or report.required_scale is None:
            continue
        if report.required_scale >= scale_threshold:
            continue

        lower_bound = max(min_height, report.height * min_scale)
        target_height = report.height * report.required_scale
        new_height = max(target_height, lower_bound)
        applied_scale = new_height / report.height if report.height else 1.0
        clamped_to_min = new_height > target_height
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
                clamped_to_min=bool(clamped_to_min),
                still_overflows=bool(applied_scale > report.required_scale),
            )
        )
    return actions


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


def replace_first_group_value(lines: list[str], start: int, end: int, code: str, value: str) -> bool:
    newline = "\r\n" if lines[start].endswith("\r\n") else "\n"
    for i in range(start, end - 1, 2):
        if lines[i].strip() == code:
            lines[i + 1] = value + newline
            return True
    return False


def write_json_report(path: Path, source: Path, output: Path | None, actions: list[ShrinkAction], patched: int | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": str(source),
        "output": str(output) if output else None,
        "actions": len(actions),
        "patched": patched,
        "items": [asdict(action) for action in actions],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def print_summary(actions: list[ShrinkAction], patched: int | None, limit: int) -> None:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Shrink overflowing TEXT heights based on check_text_layout results.")
    parser.add_argument("input", type=Path, help="Input DXF file")
    parser.add_argument("output", type=Path, nargs="?", help="Output DXF file. Required unless --dry-run is used.")
    parser.add_argument("--dry-run", action="store_true", help="Only report shrink candidates; do not write output")
    parser.add_argument("--contains", help="Only process text containing this substring")
    parser.add_argument("--scale-threshold", type=float, default=1.0, help="Shrink only reports with required scale below this value")
    parser.add_argument("--min-height", type=float, default=2.0, help="Minimum resulting TEXT height")
    parser.add_argument("--min-scale", type=float, default=0.65, help="Minimum resulting height as a fraction of original height")
    parser.add_argument("--margin-ratio", type=float, default=0.05, help="Container inset ratio used as safety margin")
    parser.add_argument("--axis-tolerance", type=float, default=1e-3, help="Tolerance for horizontal/vertical line checks")
    parser.add_argument("--flattening-distance", type=float, default=0.1, help="Path flattening distance for text2path bbox")
    parser.add_argument("--skip-anonymous-blocks", action="store_true", help="Skip anonymous block definitions")
    parser.add_argument("--json", type=Path, help="Write JSON shrink report")
    parser.add_argument("--limit", type=int, default=20, help="Maximum candidate rows to print")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.dry_run and args.output is None:
        raise SystemExit("output DXF path is required unless --dry-run is used")
    if args.output and args.input.resolve() == args.output.resolve():
        raise SystemExit("refusing to overwrite input DXF in place")
    if args.min_height < 0:
        raise SystemExit("--min-height must be non-negative")
    if not (0 < args.min_scale <= 1):
        raise SystemExit("--min-scale must be in (0, 1]")
    if not (0 < args.scale_threshold <= 1):
        raise SystemExit("--scale-threshold must be in (0, 1]")

    doc = ezdxf.readfile(args.input)
    reports = layout.check_doc(
        doc,
        contains=args.contains,
        margin_ratio=args.margin_ratio,
        axis_tolerance=args.axis_tolerance,
        flattening_distance=args.flattening_distance,
        include_anonymous_blocks=not args.skip_anonymous_blocks,
    )
    actions = build_actions(
        reports,
        scale_threshold=args.scale_threshold,
        min_height=args.min_height,
        min_scale=args.min_scale,
    )

    patched = None
    if not args.dry_run:
        assert args.output is not None
        if not actions:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.input, args.output)
            patched = 0
        else:
            patched = patch_text_heights(args.input, args.output, actions)

    print_summary(actions, patched, args.limit)
    if args.json:
        write_json_report(args.json, args.input, None if args.dry_run else args.output, actions, patched)
        print(f"wrote_json={args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
