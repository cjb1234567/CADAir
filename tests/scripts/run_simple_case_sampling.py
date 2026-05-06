from __future__ import annotations

import runpy
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
STEPS = [
    "00_validate_simple_case_inputs.py",
    "01_extract_simple_case.py",
    "02_translate_simple_case.py",
    "03_patch_simple_case_dxf.py",
    "04_verify_patched_simple_case.py",
]


def main() -> None:
    for step in STEPS:
        path = SCRIPT_DIR / step
        print(f"Running {path.name}")
        runpy.run_path(str(path), run_name="__main__")


if __name__ == "__main__":
    main()
