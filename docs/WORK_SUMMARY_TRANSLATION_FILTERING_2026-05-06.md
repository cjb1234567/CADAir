# Translation Filtering Summary

Date: 2026-05-06

## Background

The translation workflow extracted many CAD labels that should not be sent to the translation API. Examples include numbers, dimensions, cabinet identifiers, equipment slot labels, already-English labels, and short electrical abbreviations.

Sending these labels to the API had three practical costs:

- Higher API usage and slower full-file translation.
- Risk of corrupting stable CAD identifiers such as `PDU`, `ODF`, `U01`, or `CAB-01`.
- Noisy output where labels that should remain exact were rewritten unnecessarily.

## Goal

Add pre-API filtering so only text that likely needs translation is sent to the translator.

The required behavior is:

- Filter before cache lookup and before API calls.
- Keep skipped entities unchanged in the output file.
- Use the same filtering rules for sync and async translation flows.
- Log skip counts and skip reasons for diagnostics.

## Implementation

Changed files:

- `dwgtranslator/translation_filter.py`
- `dwgtranslator/manager.py`
- `tests/test_translation_filter.py`
- `docs/TODO.md`

### Filter Module

`dwgtranslator/translation_filter.py` adds `should_translate_text()`.

It returns a `TranslationFilterResult` with:

- `should_translate`: whether the text should be translated.
- `reason`: why a text was skipped, such as `empty`, `cad_marker`, `glossary`, or `target_language`.

Default skipped categories include:

- Empty or whitespace-only text.
- Pure numbers such as `12`, `3.5`, and `-10`.
- Dimensions and CAD markers such as `300mm`, `100x200`, `1:100`, and `4-20mA`.
- Slot and equipment labels such as `U01`, `2U`, `CAB-01`, and `XT1`.
- Uppercase technical abbreviations such as `PDU`, `ODF`, `CCU`, `ETH`, `RUN`, `ALM`, and `PWR`.
- Text already matching the target language, such as English labels when translating to English.

Mixed source-language text is still translated. For example, `主柜 PDU` is sent to the translator because it contains Chinese that needs English output.

### Manager Integration

`TranslationManager._do_translate()` and `TranslationManager._do_translate_async()` now call `should_translate_text()` before cache lookup.

Skipped text is not added to `translated_bundles`. This means:

- The translator API is not called for skipped handles.
- The translation cache is not polluted with unchanged CAD markers.
- `TextWriter` does not write those handles back.
- The original DXF/DWG text remains unchanged through the direct patch output path.

Both sync and async paths log:

- Total extracted text count.
- Skipped text count.
- Cache hit count.
- Translation count.
- Skip reason summary.

## Verification

Focused unit tests:

```bash
.venv/bin/python -m unittest tests.test_translation_filter
```

Result:

```text
Ran 8 tests

OK
```

Regression tests for direct DXF patching:

```bash
.venv/bin/python -m unittest tests.test_simple_case_regression
```

Result:

```text
Ran 8 tests

OK
```

Full Baidu async translation flow:

```bash
.venv/bin/python examples/baidu_async_translate.py data/20260123.dwg
```

Result:

```text
共提取 955 条文本
从原始DXF补充提取 MULTILEADER 20 条
跳过: 648 条，缓存命中: 0 条，唯一待翻译内容: 95 条
跳过原因统计: {'cad_marker': 537, 'target_language': 107, 'glossary': 4}
成功直接补丁写回 327/327 条文本
百度异步翻译完成: True
输出文件: data/20260123_translated_translated.dxf
```

## Current Behavior

For target English output:

- Chinese text is translated.
- Chinese plus stable technical labels is translated as mixed text.
- Pure English text is skipped because it already matches the target language.
- CAD markers, dimensions, numbers, slot labels, and uppercase abbreviations are skipped.

For target Chinese output:

- Existing Chinese text is skipped.
- English sentences remain translatable.
- Stable CAD markers and uppercase abbreviations remain skipped.

## Known Limitations

- The default glossary is code-based, not user-configurable yet.
- Some short English words may be ambiguous between normal text and indicator labels.
- The async log currently reports handle-level translated output count; API request count is better represented by `唯一待翻译内容`.
- Suspicious or incomplete translator output is not yet rejected automatically.

## Recommended Next Steps

- Add a configurable glossary/allowlist for project-specific CAD and electrical cabinet terms.
- Split async logging into API request count and handle writeback count.
- Add optional validation to preserve original text when translator output is incomplete or suspicious.
- Add more real drawing samples for filter false-positive and false-negative review.
