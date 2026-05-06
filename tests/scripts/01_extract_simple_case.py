from __future__ import annotations

from sample_helpers import (
    DATA_DIR,
    DXF_INPUT,
    ensure_project_imports,
    require_inputs,
    strip_entity_refs,
    summarize_bundles,
    write_json,
)


def main() -> None:
    require_inputs()
    ensure_project_imports()

    import ezdxf
    from dwgtranslator import TextExtractor

    doc = ezdxf.readfile(DXF_INPUT)
    extractor = TextExtractor(doc)
    bundles = extractor.extract()
    raw_multileaders_added = extractor.extract_raw_multileaders(str(DXF_INPUT))
    extracted = strip_entity_refs(extractor.get_bundles())

    extract_path = DATA_DIR / "simple_case.extract.json"
    summary_path = DATA_DIR / "simple_case.extract.summary.json"
    write_json(extract_path, extracted)
    write_json(
        summary_path,
        {
            **summarize_bundles(extracted),
            "source_dxf": str(DXF_INPUT),
            "raw_multileaders_added": raw_multileaders_added,
        },
    )

    print(f"Wrote {extract_path}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
