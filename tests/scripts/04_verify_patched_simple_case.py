from __future__ import annotations

from sample_helpers import DATA_DIR, ensure_project_imports, strip_entity_refs, summarize_bundles, write_json


def main() -> None:
    ensure_project_imports()

    import ezdxf
    from dwgtranslator import TextExtractor

    patched_path = DATA_DIR / "simple_case.patched.dxf"
    doc = ezdxf.readfile(patched_path)
    extractor = TextExtractor(doc)
    extractor.extract()
    extractor.extract_raw_multileaders(str(patched_path))
    extracted = strip_entity_refs(extractor.get_bundles())

    verify_path = DATA_DIR / "simple_case.patched.extract.json"
    summary_path = DATA_DIR / "simple_case.patched.summary.json"
    write_json(verify_path, extracted)
    write_json(
        summary_path,
        {
            **summarize_bundles(extracted),
            "patched_dxf": str(patched_path),
            "readable_by_ezdxf": True,
        },
    )

    print(f"Wrote {verify_path}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
