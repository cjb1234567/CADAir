from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import ezdxf

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency in older installs
    load_dotenv = None

from cadair.layout import (
    build_shrink_actions,
    check_doc,
    copy_if_no_actions,
    patch_text_heights,
    print_check_summary,
    print_shrink_summary,
    write_check_report,
    write_shrink_report,
)
from cadair.oda import convert_dwg_to_dxf
from dwgtranslator import TranslationManager, TranslationEngineFactory
from dwgtranslator.plugins.baidu import AsyncBaiduFieldTranslator, AsyncBaiduGeneralTranslator
from dwgtranslator.writeback import TextWriter


def env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def load_env_file(path: Path | None) -> None:
    if load_dotenv is None:
        return
    if path:
        load_dotenv(path)
    else:
        load_dotenv()


def require_oda_path(value: str | None) -> str:
    oda_path = value or env("ODA_PATH")
    if not oda_path:
        raise ValueError("ODA path is required for DWG input; pass --oda-path or set ODA_PATH")
    return oda_path


def oda_path_for_input(input_path: Path, value: str | None) -> str:
    if input_path.suffix.lower() == ".dwg":
        return require_oda_path(value)
    return value or env("ODA_PATH") or "__not_used_for_dxf_input__"


def source_lang(args: argparse.Namespace) -> str:
    return args.source or env("TRANSLATE_SOURCE", "auto") or "auto"


def target_lang(args: argparse.Namespace) -> str:
    return args.target or env("TRANSLATE_TARGET", "en") or "en"


def default_work_dir(input_path: Path) -> Path:
    return input_path.parent / ".cadair-work"


def work_json_path(work_dir: Path, input_path: Path, suffix: str) -> Path:
    return work_dir / f"{input_path.stem}.{suffix}.json"


def run_convert(args: argparse.Namespace) -> int:
    output = convert_dwg_to_dxf(
        input_path=args.input,
        output_path=args.output,
        oda_path=Path(require_oda_path(args.oda_path)),
        version=args.version,
        recursive=args.recursive,
    )
    print(f"converted: {output}")
    return 0


def run_extract(input_path: Path, extract_json: Path, oda_path: str | None) -> int:
    extract_json.parent.mkdir(parents=True, exist_ok=True)
    manager = TranslationManager(oda_path=oda_path_for_input(input_path, oda_path))
    bundles = manager.extract_only(str(input_path), str(extract_json))
    if input_path.suffix.lower() in {".dwg", ".dxf"}:
        source_dxf = manager._source_dxf_for_raw_access(str(input_path))
        if source_dxf:
            manager.extractor.extract_raw_multileaders(source_dxf)
            manager.extractor.export_json(str(extract_json))
            bundles = manager.extractor.get_bundles()
    print(f"extracted={len(bundles)} json={extract_json}")
    return 0


async def run_translate_json_async(args: argparse.Namespace, extract_json: Path, translated_json: Path) -> int:
    with extract_json.open("r", encoding="utf-8") as f:
        bundles = json.load(f)

    manager = TranslationManager(
        oda_path=args.oda_path or env("ODA_PATH") or "__not_used_for_json_translation__",
        glossary_json=args.glossary_json or env("GLOSSARY_JSON"),
        glossary_file=args.glossary_file or env("GLOSSARY_FILE"),
    )
    translator = create_translator(args)
    if translator is not None:
        manager.set_translator(translator)

    translated = await manager._do_translate_async(bundles, source_lang(args), target_lang(args))
    translated_json.parent.mkdir(parents=True, exist_ok=True)
    translated_json.write_text(json.dumps(translated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if translator is not None and hasattr(translator, "close"):
        await translator.close()
    print(f"translated={len(translated)} json={translated_json}")
    return 0


def run_translate_json(args: argparse.Namespace, extract_json: Path, translated_json: Path) -> int:
    return asyncio.run(run_translate_json_async(args, extract_json, translated_json))


def create_translator(args: argparse.Namespace):
    engine = args.engine
    if engine == "mock":
        return TranslationEngineFactory.create("mock", prefix=args.mock_prefix)

    if engine in {"baidu_general", "baidu_field"}:
        app_id = args.app_id or env("APP_ID")
        app_key = args.app_key or env("SEC_KEY")
        if not app_id or not app_key:
            raise ValueError("Baidu translation requires --app-id/--app-key or APP_ID/SEC_KEY")
        translator_class = AsyncBaiduGeneralTranslator if engine == "baidu_general" else AsyncBaiduFieldTranslator
        kwargs = {
            "app_id": app_id,
            "app_key": app_key,
            "max_concurrent": args.max_concurrent,
            "requests_per_second": args.qps or float(env("TRANSLATE_QPS", "1.0") or "1.0"),
        }
        if engine == "baidu_field":
            kwargs["domain"] = args.domain or env("TRANSLATE_DOMAIN", "machinery") or "machinery"
        return translator_class(**kwargs)

    raise ValueError(f"unknown translation engine: {engine}")


def source_dxf_for_writeback(input_path: Path, oda_path: str | None) -> Path:
    if input_path.suffix.lower() == ".dxf":
        return input_path
    if input_path.suffix.lower() != ".dwg":
        raise ValueError(f"input must be DWG or DXF: {input_path}")
    work_dir = default_work_dir(input_path)
    work_dir.mkdir(parents=True, exist_ok=True)
    converted = work_dir / f"{input_path.stem}.oda.dxf"
    return convert_dwg_to_dxf(input_path, converted, Path(require_oda_path(oda_path)))


def run_writeback(input_path: Path, translated_json: Path, output_path: Path, oda_path: str | None) -> int:
    if output_path is None:
        raise ValueError("OUTPUT is required unless --extract-only is used")
    source_dxf = source_dxf_for_writeback(input_path, oda_path)
    writer = TextWriter()
    writer.load_from_json(str(translated_json))
    patched = writer.patch_dxf_file(str(source_dxf), str(output_path))
    print(f"writeback_patched={patched} output={output_path}")
    return 0


def run_full_translate(args: argparse.Namespace) -> int:
    work_dir = args.work_dir or default_work_dir(args.input)
    extract_json = args.extract_json or work_json_path(work_dir, args.input, "extract")
    translated_json = args.translated_json or work_json_path(work_dir, args.input, "translated")

    run_extract(args.input, extract_json, args.oda_path)
    run_translate_json(args, extract_json, translated_json)
    run_writeback(args.input, translated_json, args.output, args.oda_path)

    if args.keep_work_files:
        print(f"work_files={extract_json},{translated_json}")
    return 0


def run_translate(args: argparse.Namespace) -> int:
    if args.extract_only and args.writeback_only:
        raise ValueError("--extract-only and --writeback-only cannot be used together")
    if args.extract_only:
        return run_extract(args.input, args.extract_only, args.oda_path)
    if args.output is None:
        raise ValueError("OUTPUT is required unless --extract-only is used")
    if args.writeback_only:
        return run_writeback(args.input, args.writeback_only, args.output, args.oda_path)
    return run_full_translate(args)


def run_layout(args: argparse.Namespace) -> int:
    if args.output and not args.shrink:
        raise ValueError("OUTPUT is only valid with --shrink")
    if args.output and args.input.resolve() == args.output.resolve():
        raise ValueError("refusing to overwrite input DXF in place")
    if args.min_height < 0:
        raise ValueError("--min-height must be non-negative")
    if not (0 < args.min_scale <= 1):
        raise ValueError("--min-scale must be in (0, 1]")
    if not (0 < args.scale_threshold <= 1):
        raise ValueError("--scale-threshold must be in (0, 1]")

    doc = ezdxf.readfile(args.input)
    reports = check_doc(
        doc,
        contains=args.contains,
        margin_ratio=args.margin_ratio,
        axis_tolerance=args.axis_tolerance,
        flattening_distance=args.flattening_distance,
        include_anonymous_blocks=not args.skip_anonymous_blocks,
    )

    if not args.shrink:
        print_check_summary(reports, args.limit)
        if args.json:
            write_check_report(args.json, args.input, reports)
            print(f"wrote_json={args.json}")
        return 0

    actions = build_shrink_actions(
        reports,
        scale_threshold=args.scale_threshold,
        min_height=args.min_height,
        min_scale=args.min_scale,
    )
    patched = None
    if args.output:
        if actions:
            patched = patch_text_heights(args.input, args.output, actions)
        else:
            copy_if_no_actions(args.input, args.output)
            patched = 0
    print_shrink_summary(actions, patched, args.limit)
    if args.json:
        write_shrink_report(args.json, args.input, args.output, actions, patched)
        print(f"wrote_json={args.json}")
    return 0


def run_engines(args: argparse.Namespace) -> int:
    engines = TranslationEngineFactory.list_engines()
    if args.json:
        print(json.dumps({"engines": engines}, indent=2, ensure_ascii=False))
    else:
        for engine in engines:
            print(engine)
    return 0


def add_common_translate_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--engine", default="mock", choices=["mock", "baidu_general", "baidu_field"])
    parser.add_argument("--source")
    parser.add_argument("--target")
    parser.add_argument("--app-id")
    parser.add_argument("--app-key")
    parser.add_argument("--domain")
    parser.add_argument("--qps", type=float)
    parser.add_argument("--max-concurrent", type=int, default=1)
    parser.add_argument("--mock-prefix", default="")
    parser.add_argument("--glossary-json")
    parser.add_argument("--glossary-file")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cadair", description="CADAir command line tools")
    parser.add_argument("--env-file", type=Path, help="Load environment variables from this .env file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert = subparsers.add_parser("convert", help="Convert DWG to DXF")
    convert.add_argument("input", type=Path)
    convert.add_argument("output", type=Path, nargs="?")
    convert.add_argument("--oda-path")
    convert.add_argument("--version", default="ACAD2007")
    convert.add_argument("--recursive", action="store_true")
    convert.set_defaults(func=run_convert)

    translate = subparsers.add_parser("translate", help="Translate CAD text and write DXF output")
    translate.add_argument("input", type=Path)
    translate.add_argument("output", type=Path, nargs="?")
    translate.add_argument("--oda-path")
    translate.add_argument("--work-dir", type=Path)
    translate.add_argument("--keep-work-files", action="store_true")
    translate.add_argument("--extract-json", type=Path, help="Path for intermediate extracted JSON")
    translate.add_argument("--translated-json", type=Path, help="Path for intermediate translated JSON")
    translate.add_argument("--extract-only", type=Path, help="Only extract text to this JSON path")
    translate.add_argument("--writeback-only", type=Path, help="Only write this translated JSON back to CAD")
    add_common_translate_args(translate)
    translate.set_defaults(func=run_translate)

    layout = subparsers.add_parser("layout", help="Check layout overflow and optionally shrink TEXT")
    layout.add_argument("input", type=Path)
    layout.add_argument("output", type=Path, nargs="?")
    layout.add_argument("--shrink", action="store_true")
    layout.add_argument("--contains")
    layout.add_argument("--json", type=Path)
    layout.add_argument("--limit", type=int, default=20)
    layout.add_argument("--margin-ratio", type=float, default=0.05)
    layout.add_argument("--axis-tolerance", type=float, default=1e-3)
    layout.add_argument("--flattening-distance", type=float, default=0.1)
    layout.add_argument("--skip-anonymous-blocks", action="store_true")
    layout.add_argument("--scale-threshold", type=float, default=1.0)
    layout.add_argument("--min-height", type=float, default=2.0)
    layout.add_argument("--min-scale", type=float, default=0.65)
    layout.set_defaults(func=run_layout)

    engines = subparsers.add_parser("engines", help="List translation engines")
    engines.add_argument("--json", action="store_true")
    engines.set_defaults(func=run_engines)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    load_env_file(args.env_file)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
