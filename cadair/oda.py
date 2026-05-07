from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def convert_dwg_to_dxf(
    input_path: Path,
    output_path: Path | None,
    oda_path: Path,
    version: str = "ACAD2007",
    recursive: bool = False,
    timeout: int | None = None,
) -> Path:
    """Convert a DWG file to DXF by calling ODA File Converter directly."""
    input_path = Path(input_path).expanduser().resolve()
    oda_path = Path(oda_path).expanduser().resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"input file not found: {input_path}")
    if input_path.suffix.lower() != ".dwg":
        raise ValueError(f"input file must be a .dwg file: {input_path}")
    if not oda_path.exists():
        raise FileNotFoundError(f"ODA File Converter not found: {oda_path}")

    if output_path is None:
        output_path = input_path.with_suffix(".dxf")
    else:
        output_path = Path(output_path).expanduser().resolve()
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

        timeout_seconds = timeout or int(env.get("CADAIR_ODA_TIMEOUT_SECONDS", "120"))
        result = subprocess.run(args, capture_output=True, text=True, env=env, timeout=timeout_seconds)
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
