"""Convert DWG files to DXF by calling ODA File Converter directly."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


if load_dotenv:
    load_dotenv()


def convert_dwg_to_dxf(
    input_path: Path,
    output_path: Path | None,
    oda_path: Path,
    version: str = "ACAD2007",
    recursive: bool = False,
) -> Path:
    """Convert a DWG file to DXF and return the output path."""
    input_path = Path(input_path).resolve()
    oda_path = Path(oda_path).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"input file not found: {input_path}")
    if input_path.suffix.lower() != ".dwg":
        raise ValueError(f"input file must be a .dwg file: {input_path}")
    if not oda_path.exists():
        raise FileNotFoundError(f"ODA File Converter not found: {oda_path}")

    if output_path is None:
        output_path = input_path.with_suffix(".dxf")
    else:
        output_path = Path(output_path).resolve()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="oda_dwg_to_dxf_") as tmp_dir:
        tmp_output_dir = Path(tmp_dir)
        args = [
            str(oda_path),
            str(input_path.parent),
            str(tmp_output_dir),
            version,
            "DXF",
            "0",
            "1" if recursive else "0",
            input_path.name,
        ]

        env = os.environ.copy()
        env.setdefault("XDG_RUNTIME_DIR", "/tmp/runtime-cadair")
        env.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
        Path(env["XDG_RUNTIME_DIR"]).mkdir(parents=True, exist_ok=True)

        if not env.get("DISPLAY") and shutil.which("xvfb-run"):
            args = ["xvfb-run", "-a", *args]

        result = subprocess.run(args, capture_output=True, text=True, env=env, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(
                "ODA File Converter failed\n"
                f"returncode: {result.returncode}\n"
                f"stdout: {result.stdout.strip()}\n"
                f"stderr: {result.stderr.strip()}"
            )

        generated = tmp_output_dir / input_path.with_suffix(".dxf").name
        if not generated.exists():
            candidates = list(tmp_output_dir.glob("*.dxf"))
            if len(candidates) == 1:
                generated = candidates[0]
            else:
                raise FileNotFoundError(
                    f"converted DXF not found in ODA output directory: {tmp_output_dir}"
                )

        shutil.copy2(generated, output_path)
        return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a DWG file to DXF by using ODA File Converter."
    )
    parser.add_argument("input", type=Path, help="source .dwg file")
    parser.add_argument("output", type=Path, nargs="?", help="target .dxf file")
    parser.add_argument(
        "--oda-path",
        type=Path,
        default=Path(os.environ["ODA_PATH"]) if os.getenv("ODA_PATH") else None,
        required=not bool(os.getenv("ODA_PATH")),
        help="path to ODA File Converter executable, or set ODA_PATH",
    )
    parser.add_argument(
        "--version",
        default="ACAD2007",
        help="ODA output version, for example ACAD2007, ACAD2010, ACAD2013",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="let ODA scan input directories recursively",
    )
    args = parser.parse_args()

    try:
        output = convert_dwg_to_dxf(
            input_path=args.input,
            output_path=args.output,
            oda_path=args.oda_path,
            version=args.version,
            recursive=args.recursive,
        )
    except Exception as exc:
        print(f"conversion failed: {exc}", file=sys.stderr)
        return 1

    print(f"converted: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
