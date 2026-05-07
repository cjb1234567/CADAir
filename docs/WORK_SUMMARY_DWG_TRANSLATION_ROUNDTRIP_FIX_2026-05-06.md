# DWG Translation Roundtrip Fix Summary

Date: 2026-05-06

## Background

The translation flow for `data/20260123.dwg` produced a DXF where some `MULTILEADER` arrows and labels were not visible in the CAD viewer. The affected label included text like:

```text
所有屏柜光纤配线架ODF为后置，正面为挡板
```

The original DWG displayed correctly, so the investigation focused on finding which stage broke the display compatibility.

## Root Cause

The root cause was `ezdxf.readfile()` followed by `doc.saveas()` rewriting the whole DXF file.

A zero-change roundtrip test proved this:

```bash
uv run python -c "import ezdxf; doc = ezdxf.readfile('data/20260123_oda_direct.dxf'); doc.saveas('data/20260123_ezdxf_roundtrip.dxf')"
```

Result:

- `data/20260123_oda_direct.dxf` displayed correctly.
- `data/20260123_ezdxf_roundtrip.dxf` no longer displayed the target `MULTILEADER` arrows and labels.
- No translation or writeback changes were involved in this test.

This isolated the failure to the `ezdxf` full-file roundtrip, not ODA conversion or the translation API.

## Fix Strategy

For DWG input, the workflow now avoids using `doc.saveas()` for the final DXF output.

The new path is:

1. Use ODA File Converter to create a viewer-compatible base DXF.
2. Use `ezdxf` only for extraction where it is safe and useful.
3. Supplement missing `MULTILEADER` text by reading the raw ODA DXF text and extracting group code `304` by entity handle.
4. Translate all collected text bundles.
5. Patch the ODA DXF directly by handle, replacing only text group values.
6. Preserve the rest of the DXF byte-level structure as much as practical.

This prevents `ezdxf` from reserializing complex entities and proxy/context data needed by CAD viewers.

## Implementation Details

Changed files:

- `dwgtranslator/core.py`
- `dwgtranslator/extract.py`
- `dwgtranslator/manager.py`
- `dwgtranslator/writeback.py`
- `cadair/oda.py`

Key changes:

- `DWGCore` now records the ODA-generated DXF path in `last_converted_dxf`.
- `DWGCore.convert_dwg_to_dxf()` exposes direct ODA conversion for reuse.
- `TextExtractor.extract_raw_multileaders()` supplements `MULTILEADER` entities from the raw DXF.
- `TextWriter.patch_dxf_file()` patches text directly without using `ezdxf.saveas()`.
- `TranslationManager` uses the direct patch output path for DWG input.
- `cadair convert` provides a standalone ODA conversion tool for diagnostics.

Patched group codes:

| Entity Type | Group Code | Purpose |
|---|---:|---|
| `TEXT` | `1` | Text value |
| `ATTRIB` | `1` | Attribute text value |
| `MTEXT` | `1` | MText content |
| `MULTILEADER` | `304` | MLeader text content |

Important DXF patching detail:

- DXF files are code/value line pairs.
- The patcher must scan in steps of two lines.
- A previous one-line-at-a-time scan could mistake a value line like `1` for group code `1`, corrupting the following code line.
- This was fixed by scanning with `range(start, end - 1, 2)`.

Line break handling:

- `TEXT` and `ATTRIB` values are forced to a single line.
- `MTEXT` and `MULTILEADER` values encode line breaks as `\P`.

## Verification

Direct ODA conversion:

```bash
cadair convert data/20260123.dwg data/20260123_oda_direct.dxf
```

Result:

```text
converted: /mnt/e/aiProjs/CADAir/data/20260123_oda_direct.dxf
```

Zero-change `ezdxf` roundtrip:

```bash
uv run python -c "import ezdxf; doc = ezdxf.readfile('data/20260123_oda_direct.dxf'); doc.saveas('data/20260123_ezdxf_roundtrip.dxf')"
```

Result:

- The roundtrip file did not display the target `MULTILEADER` arrow and label.
- This confirmed the roundtrip issue.

Mock translation patch validation:

```bash
uv run python -c "import os; from dotenv import load_dotenv; load_dotenv(); from dwgtranslator import TranslationManager; m=TranslationManager(os.getenv('ODA_PATH')); m.clear_cache(); ok=m.translate_file('data/20260123.dwg', 'data/20260123_mock_patched_rawmleader_fixed2.dxf', target_lang='zz4', source_lang='zh', custom_translator=lambda text, target: 'PATCHED::' + text); print('ok=', ok)"
```

Result:

```text
共提取 955 条文本
从原始DXF补充提取 MULTILEADER 20 条
成功直接补丁写回 975/975 条文本
ok= True
```

Viewer result:

- `data/20260123_mock_patched_rawmleader_fixed2.dxf` opened normally.
- The arrow and `PATCHED::所有屏柜...` label displayed correctly.
- The CAD viewer no longer prompted to repair the file.

Real Baidu async translation:

```bash
uv run python examples/baidu_async_translate.py data/20260123.dwg
```

Result:

```text
共提取 955 条文本
从原始DXF补充提取 MULTILEADER 20 条
成功直接补丁写回 975/975 条文本
百度异步翻译完成: True
输出文件: data/20260123_translated_translated.dxf
```

The generated DXF displayed correctly and solved the missing `MULTILEADER` arrow/label issue.

## Current Behavior

For DWG input:

- ODA conversion creates the base DXF.
- Raw `MULTILEADER` text is supplemented from the ODA DXF.
- Final output is patched directly.
- `ezdxf.saveas()` is avoided for the final output.

For DXF input:

- The old `ezdxf` writeback/save path remains as fallback.
- This path may still be risky for complex `MULTILEADER` entities if the input DXF contains similar viewer-sensitive data.

## Known Limitations

- The direct patcher currently targets the first matching text group value inside each entity range.
- Long translated English text may exceed the original annotation space; this is a layout/typography problem, not a file corruption problem.
- The raw DXF patch path assumes UTF-8 compatible DXF text output from ODA.
- The DXF-input workflow still needs a non-roundtrip patch path if similar issues appear for DXF source files.

## Recommended Next Steps

- Add regression tests for direct DXF patching on representative fixtures.
- Improve language filtering so numbers, cabinet IDs, model names, and short codes are not translated unnecessarily.
- Add layout adaptation for long translations.
- Consider extending non-roundtrip patching to DXF input files.

## Test Sampling And Regression Work

Additional test fixture and regression work was added after the non-roundtrip patch fix.

### Fixture Inputs

Prepared test inputs:

- `tests/data/simple_case.dwg`
- `tests/data/simple_case.oda.dxf`

The `.dwg` file is the source CAD fixture. The `.oda.dxf` file is the ODA-converted DXF baseline used by the sampling scripts. Using the prepared ODA DXF keeps the sampling flow reproducible without requiring every test run to invoke ODA File Converter.

### Sampling Scripts

Added scripts under `tests/scripts/`:

- `tests/scripts/sample_helpers.py`
- `tests/scripts/00_validate_simple_case_inputs.py`
- `tests/scripts/01_extract_simple_case.py`
- `tests/scripts/02_translate_simple_case.py`
- `tests/scripts/03_patch_simple_case_dxf.py`
- `tests/scripts/04_verify_patched_simple_case.py`
- `tests/scripts/run_simple_case_sampling.py`

Run all sampling steps:

```bash
.venv/bin/python tests/scripts/run_simple_case_sampling.py
```

The sampling flow performs these stages:

1. Validate the prepared DWG and ODA DXF inputs.
2. Extract text from `simple_case.oda.dxf` with `ezdxf`.
3. Supplement raw `MULTILEADER` text from group code `304`.
4. Generate stable mock translations using the `TT::` prefix.
5. Patch the DXF directly through `TextWriter.patch_dxf_file()`.
6. Re-open the patched DXF and extract text again to confirm readability and entity coverage.

Generated baseline artifacts:

- `tests/data/simple_case.inputs.json`
- `tests/data/simple_case.extract.json`
- `tests/data/simple_case.extract.summary.json`
- `tests/data/simple_case.translated.json`
- `tests/data/simple_case.patched.dxf`
- `tests/data/simple_case.patch_observation.json`
- `tests/data/simple_case.patched.extract.json`
- `tests/data/simple_case.patched.summary.json`

### Sampling Results

Extraction baseline:

```text
total: 975
TEXT: 937
MTEXT: 18
MULTILEADER: 20
raw MULTILEADER additions: 20
```

Patch baseline:

```text
patched_count: 975/975
matched_expected: 975/975
patched DXF readable by ezdxf: yes
```

Patch observation checks entity-specific group codes:

| Entity Type | Expected Group Code |
|---|---:|
| `TEXT` | `1` |
| `MTEXT` | `1` |
| `ATTRIB` | `1` |
| `MULTILEADER` | `304` |

The observation script also normalizes expected values according to DXF output encoding:

- `TEXT` and `ATTRIB` line breaks are flattened to spaces.
- `MTEXT` and `MULTILEADER` line breaks are encoded as `\P`.

### Regression Tests

Added regression test file:

- `tests/test_simple_case_regression.py`

The tests cover:

- Fixture and generated baseline files exist and are non-empty.
- Extraction counts remain stable.
- Mock translation baselines preserve handles, entity types, and original text.
- Direct DXF patch observation matches every translated handle.
- `MULTILEADER` patches target group code `304`; other text entities target group code `1`.
- Patched DXF remains readable by `ezdxf`.
- Patched extraction summary matches the original extraction summary.

Focused test command:

```bash
.venv/bin/python -m unittest tests.test_simple_case_regression
```

Latest result:

```text
Ran 6 tests in 4.115s

OK
```

`pytest` is not currently installed in `.venv`, so the focused verification used `unittest`. The test file is still compatible with pytest discovery once pytest is installed.
