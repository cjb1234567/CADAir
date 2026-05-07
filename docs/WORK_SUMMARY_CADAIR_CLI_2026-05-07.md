# Work Summary: Unified CADAir CLI

Date: 2026-05-07

## Goal

Provide a small user-facing CLI for common CADAir workflows without exposing every internal pipeline step as a separate command. Keep translation-specific code in `dwgtranslator`, move project-level CAD utilities into `cadair`, and remove legacy `dwg-utils` entry points that duplicated the new command surface.

## Changes

- Added the `cadair` package for project-level CLI and CAD utilities.
- Added `cadair.cli` as the unified command entry point.
- Added `cadair.oda` for direct ODA DWG to DXF conversion.
- Added `cadair.layout` for text overflow diagnostics and conservative `TEXT` height shrinking.
- Added the `cadair` console script in `pyproject.toml`.
- Exposed four user-facing commands:
  - `cadair convert`
  - `cadair translate`
  - `cadair layout`
  - `cadair engines`
- Kept internal single-step functions for extraction, JSON translation, writeback, layout checking, and shrink actions.
- Removed obsolete standalone entry points:
  - `dwg-utils/dwg_to_dxf.py`
  - `dwg-utils/check_text_layout.py`
  - `dwg-utils/shrink_text_layout.py`

## Command Design

`cadair convert` performs direct DWG to DXF conversion through ODA File Converter:

```bash
cadair convert input.dwg output.dxf --oda-path "$ODA_PATH"
```

`cadair translate` performs the normal CAD translation workflow:

```bash
cadair translate input.dwg output.dxf \
  --engine baidu_general \
  --source zh \
  --target en \
  --glossary-file config/cad_glossary_zh-en.json
```

The translate command also supports focused modes for manual workflows:

```bash
cadair translate input.dwg --extract-only translation_work.json
cadair translate input.dwg output.dxf --writeback-only translation_work.json
```

`cadair layout` checks translated text against nearby frame/table containers:

```bash
cadair layout output.dxf --json layout_report.json
```

The same command can preview or apply conservative `TEXT` shrinking:

```bash
cadair layout output.dxf --shrink --json shrink_candidates.json
cadair layout output.dxf output.shrunk.dxf --shrink --json shrink_report.json
```

`cadair engines` lists registered translation engines:

```bash
cadair engines
cadair engines --json
```

## Implementation Notes

- `cadair translate` uses the same extraction and filtering logic as `TranslationManager`.
- Final writeback uses raw DXF patching through `TextWriter.patch_dxf_file()` to avoid an `ezdxf.saveas()` roundtrip.
- `cadair layout --shrink` patches only raw DXF group code `40` for `TEXT` entities.
- `cadair layout` does not modify `MTEXT`, `MULTILEADER`, geometry, positions, or line wrapping.
- The `dwgtranslator` package remains focused on translation behavior and translation engines.
- The `cadair` package owns CLI orchestration, ODA conversion utilities, and non-translation layout tooling.

## Verification

Full test suite:

```bash
.venv/bin/python -m unittest
```

Result:

```text
Ran 35 tests
OK
```

Compile check:

```bash
.venv/bin/python -m compileall cadair dwgtranslator dwg-utils examples tests
```

CLI smoke checks:

```bash
.venv/bin/python -m cadair.cli --help
.venv/bin/python -m cadair.cli convert --help
.venv/bin/python -m cadair.cli translate --help
.venv/bin/python -m cadair.cli layout --help
.venv/bin/python -m cadair.cli engines --json
```

Translation workflow checks:

```bash
.venv/bin/python -m cadair.cli translate tests/data/simple_case.oda.dxf \
  --extract-only /tmp/opencode/regress.simple.extract.json
```

Observed:

```text
extracted=975
```

```bash
.venv/bin/python -m cadair.cli translate tests/data/simple_case.oda.dxf \
  /tmp/opencode/regress.simple.mock.dxf \
  --engine mock \
  --mock-prefix RT:: \
  --work-dir /tmp/opencode/regress-work \
  --keep-work-files
```

Observed:

```text
translated=327
writeback_patched=327
```

```bash
.venv/bin/python -m cadair.cli translate tests/data/simple_case.oda.dxf \
  /tmp/opencode/regress.simple.writeback.dxf \
  --writeback-only tests/data/simple_case.translated.json
```

Observed:

```text
writeback_patched=975
```

Layout workflow checks:

```bash
.venv/bin/python -m cadair.cli layout tests/data/simple_case.patched.dxf \
  --json /tmp/opencode/regress.layout.json \
  --limit 2
```

Observed:

```text
checked_texts=1097 containers_found=521 overflows=91
```

```bash
.venv/bin/python -m cadair.cli layout tests/data/simple_case.patched.dxf \
  /tmp/opencode/regress.simple.shrunk.dxf \
  --shrink \
  --json /tmp/opencode/regress.shrink.json \
  --limit 2
```

Observed:

```text
shrink_candidates=60 patched=60
```

The generated shrunk DXF was readable by `ezdxf`:

```text
AC1021 5649
```

## Follow-Ups

- Add optional `MTEXT` and `MULTILEADER` wrapping as a separate layout adaptation feature.
- Add a DXF patched-range validation tool for code/value line pairing.
- Add a cleanup command for generated diagnostic DXF and JSON files if these artifacts become frequent.
