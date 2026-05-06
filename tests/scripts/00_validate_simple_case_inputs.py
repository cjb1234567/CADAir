from __future__ import annotations

from sample_helpers import DATA_DIR, DWG_INPUT, DXF_INPUT, require_inputs, write_json


def main() -> None:
    require_inputs()

    import ezdxf

    doc = ezdxf.readfile(DXF_INPUT)
    manifest = {
        "dwg": {
            "path": str(DWG_INPUT.relative_to(DATA_DIR.parent.parent)),
            "exists": DWG_INPUT.exists(),
            "size_bytes": DWG_INPUT.stat().st_size,
        },
        "oda_dxf": {
            "path": str(DXF_INPUT.relative_to(DATA_DIR.parent.parent)),
            "exists": DXF_INPUT.exists(),
            "size_bytes": DXF_INPUT.stat().st_size,
            "dxfversion": doc.dxfversion,
            "layouts": [layout.name for layout in doc.layouts],
            "block_count": len(doc.blocks),
        },
    }
    out_path = DATA_DIR / "simple_case.inputs.json"
    write_json(out_path, manifest)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
