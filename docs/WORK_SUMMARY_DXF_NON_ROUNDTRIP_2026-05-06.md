# DXF Non-Roundtrip Patch Output Summary

Date: 2026-05-06

## Background

The existing non-roundtrip output path protected DWG-derived DXF output from a full `ezdxf.saveas()` rewrite. That fix preserved complex `MULTILEADER` display data by patching the ODA-generated DXF directly.

DXF input files still used the older fallback path:

1. Read the DXF through `ezdxf.readfile()`.
2. Write translated text into entities.
3. Save the entire file with `doc.saveas()`.

That kept DXF input vulnerable to the same roundtrip risk already identified for DWG-derived DXF output.

## Goal

Support non-roundtrip patch output for DXF input files, not only DWG input.

The intended behavior is:

- DWG input: convert to a base DXF with ODA, then patch text directly.
- DXF input: use the original DXF as the base file, then patch text directly.
- Avoid `ezdxf.saveas()` for final output whenever a raw DXF source is available.

## Implementation

Changed files:

- `dwgtranslator/manager.py`
- `dwgtranslator/extract.py`
- `dwgtranslator/writeback.py`
- `tests/test_simple_case_regression.py`
- `README.md`
- `docs/TODO.md`

### Manager Flow

`TranslationManager` now resolves a raw DXF source through `_source_dxf_for_raw_access()`:

- `.dxf` input returns the input path directly.
- `.dwg` input returns `DWGCore.last_converted_dxf` when available.
- `.dwg` input falls back to `DWGCore.convert_dwg_to_dxf()` if needed.
- Unsupported input types return `None` and keep the legacy save fallback.

Both sync and async translation flows now use that source DXF for raw `MULTILEADER` extraction.

Final output uses `_save_without_ezdxf_roundtrip()` for both DWG and DXF sources. The output path is normalized with `Path(output_path).with_suffix('.dxf')`, which avoids fragile string replacement for uppercase or already-DXF paths.

### Raw DXF Extraction

`TextExtractor.extract_raw_multileaders()` now reads raw DXF files with the same encoding detection used by the patcher.

This matters because direct patch output is only safe if raw extraction and raw writeback interpret the source DXF consistently.

### DXF Encoding Handling

`TextWriter` now exposes `detect_dxf_encoding()` for raw DXF reads and writes.

The detection rule is intentionally lightweight and header-based:

- R2007+ DXF versions (`AC1021`, `AC1024`, `AC1027`, `AC1032`) are treated as UTF-8.
- Legacy DXF versions use `$DWGCODEPAGE` mappings.
- Unknown legacy codepages fall back to `cp1252`.

Covered mappings include:

| DXF Codepage | Python Encoding |
|---|---|
| `ANSI_936` | `gbk` |
| `ANSI_932` | `cp932` |
| `ANSI_949` | `cp949` |
| `ANSI_950` | `cp950` |
| `ANSI_1250` - `ANSI_1258` | matching `cp1250` - `cp1258` |

Important fixture detail:

```text
$ACADVER = AC1021
$DWGCODEPAGE = ANSI_936
```

Even though the fixture declares `ANSI_936`, `AC1021` means R2007, so the correct raw text encoding for this workflow is UTF-8. The implementation therefore prioritizes R2007+ version detection over `$DWGCODEPAGE`.

## Tests

Regression coverage was added to `tests/test_simple_case_regression.py`.

New tests cover:

- Current fixture `tests/data/simple_case.oda.dxf` is detected as `utf-8`.
- A synthetic legacy `AC1015 + ANSI_936` DXF is detected as `gbk`.
- `TranslationManager.translate_file()` with DXF input writes output through direct patching.
- DXF input manager flow does not call `core.save()`.
- The patched output DXF remains readable by `ezdxf`.
- The patched output matches expected translated values for all extracted handles.
- The manager-level DXF path includes patched `MULTILEADER` output.

Focused verification command:

```bash
.venv/bin/python -m unittest tests.test_simple_case_regression
```

Latest result:

```text
Ran 8 tests in 5.668s

OK
```

Compile check:

```bash
.venv/bin/python -m py_compile dwgtranslator/writeback.py dwgtranslator/extract.py dwgtranslator/manager.py tests/test_simple_case_regression.py
```

Result: passed with no output.

## Documentation Updates

`README.md` now documents:

- DWG/DXF output compatibility through direct DXF patching.
- Direct patching without final `ezdxf.saveas()` for both DWG and DXF input.
- Header-based DXF encoding detection for raw patch operations.

`docs/TODO.md` was updated to move the task into Completed:

```text
Supported non-roundtrip patch output for DXF input files, not only DWG input.
```

## Current Behavior

For DWG input:

1. ODA converts DWG to DXF.
2. `ezdxf` extracts standard entities.
3. Raw DXF extraction supplements missing `MULTILEADER` group code `304` text.
4. The translated output patches the ODA DXF directly by handle.

For DXF input:

1. The original DXF is used as the base output structure.
2. `ezdxf` extracts standard entities.
3. Raw DXF extraction supplements missing `MULTILEADER` group code `304` text.
4. The translated output patches the original DXF copy directly by handle.

Both paths avoid final `ezdxf.saveas()` when the source format can provide a raw DXF base.

## Commit

Implemented and committed as:

```text
fcfe275 fix: support direct patching for DXF input
```

## Remaining Work

The next high-priority tasks are translation filtering and glossary/allowlist handling. Those should reduce unnecessary API calls and avoid translating CAD/electrical cabinet identifiers such as `ODF`, `PDU`, `CCU`, `ETH`, `RUN`, `ALM`, and `PWR`.
