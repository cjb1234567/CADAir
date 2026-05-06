from __future__ import annotations

from sample_helpers import DATA_DIR, build_translated_bundles, read_json, write_json


def main() -> None:
    extract_path = DATA_DIR / "simple_case.extract.json"
    extracted = read_json(extract_path)
    translated = build_translated_bundles(extracted)

    translated_path = DATA_DIR / "simple_case.translated.json"
    write_json(translated_path, translated)
    print(f"Wrote {translated_path}")


if __name__ == "__main__":
    main()
