# Work Summary: Glossary Configuration and Fixed CAD Translations

Date: 2026-05-07

## Goal

Add configurable CAD/electrical cabinet glossary support so stable labels can be preserved and selected professional terms can use fixed translations before calling the translation API.

## Changes

- Added `dwgtranslator/glossary.py` for glossary loading and normalization.
- Added `GlossaryConfig` with two behaviors:
  - `terms`: exact allowlist entries that are skipped and preserved as-is.
  - `translations`: exact fixed translations that are written directly without API calls.
- Extended `TranslationManager` to accept:
  - `glossary`
  - `glossary_json`
  - `glossary_file`
- Applied fixed glossary translations before cache lookup, translation filtering, and API calls.
- Kept existing built-in `DEFAULT_GLOSSARY` terms merged by default.
- Added `config/cad_glossary_zh-en.json` as the zh-to-en glossary config.
- Updated `examples/baidu_async_translate.py` with:
  - `--glossary-json`
  - `--glossary-file`
  - `.env` support for `GLOSSARY_JSON` and `GLOSSARY_FILE`
- Exported `load_glossary` from `dwgtranslator/__init__.py`.
- Updated `.env.example`, `README.md`, and `docs/TODO.md`.

## Supported Config Formats

Simple allowlist:

```json
["ODF", "PDU", "RUN"]
```

Allowlist plus fixed translations:

```json
{
  "terms": ["ODF", "PDU", "RUN"],
  "translations": {
    "主柜": "Main Cabinet",
    "备用柜": "Standby Cabinet"
  }
}
```

Direction-specific configs are kept as separate files by naming convention, for example:

```text
config/cad_glossary_zh-en.json
```

## Runtime Behavior

For each extracted text bundle:

1. Check `translations` for an exact normalized match.
2. If matched, write the fixed translation directly and do not call the API.
3. If not matched, run the existing translation filter using `terms` as the allowlist.
4. If still translatable, continue with cache lookup and translator/API call.

This deliberately avoids partial replacement inside longer strings for the first version.

## Verification

JSON validation:

```bash
.venv/bin/python -m json.tool config/cad_glossary_zh-en.json
```

Regression tests:

```bash
.venv/bin/python -m unittest tests.test_translation_filter
.venv/bin/python -m unittest tests.test_simple_case_regression
.venv/bin/python -m unittest tests.test_baidu_translator
```

Results:

- `tests.test_translation_filter`: 17 tests passed.
- `tests.test_simple_case_regression`: 8 tests passed.
- `tests.test_baidu_translator`: 10 tests passed.

Full async Baidu example with config file:

```bash
.venv/bin/python examples/baidu_async_translate.py data/20260123.dwg --glossary-file config/cad_glossary_zh-en.json
```

Observed result:

- Completed successfully with `百度异步翻译完成: True`.
- Output: `data/20260123_translated_translated.dxf`.
- Extracted text: 955 entries.
- Raw `MULTILEADER` supplement: 20 entries.
- Direct DXF patch writeback: 327/327 entries.
- Translation summary: 975 total, 648 skipped, 94 unique API translation inputs.
- Skip reasons: `cad_marker` 537, `target_language` 107, `glossary` 4.

Fixed translation example from config:

```text
[6AF6] 电源分配单元 -> Power Distribution Unit
```

## Notes

- Some formatted CAD text did not hit fixed translations because embedded spacing changes the text, for example `运    行` and `告    警`.
- A future improvement is to normalize internal CJK spacing for glossary lookup so `运    行` can match `运行`.
- Some long Baidu results are incomplete or suspicious, which reinforces the existing TODO for preserving original text when translation output is suspicious.
