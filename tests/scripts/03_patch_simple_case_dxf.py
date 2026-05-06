from __future__ import annotations

from sample_helpers import (
    DATA_DIR,
    DXF_INPUT,
    ensure_project_imports,
    observe_translated_handles,
    read_json,
    require_inputs,
    write_json,
)


def main() -> None:
    require_inputs()
    ensure_project_imports()

    from dwgtranslator import TextWriter

    translated_path = DATA_DIR / "simple_case.translated.json"
    patched_path = DATA_DIR / "simple_case.patched.dxf"
    observation_path = DATA_DIR / "simple_case.patch_observation.json"

    translated = read_json(translated_path)
    writer = TextWriter()
    writer.load_translated(translated)
    patched_count = writer.patch_dxf_file(str(DXF_INPUT), str(patched_path))

    observation = observe_translated_handles(patched_path, translated)
    observation["patched_count"] = patched_count
    write_json(observation_path, observation)

    print(f"Wrote {patched_path}")
    print(f"Wrote {observation_path}")


if __name__ == "__main__":
    main()
