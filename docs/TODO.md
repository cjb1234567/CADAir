# CADAir TODO

Last updated: 2026-05-07

## High Priority

## Medium Priority

- [ ] Normalize internal CJK spacing for glossary lookup so formatted CAD labels such as `运    行` can match `运行`.
- [ ] Add optional text wrapping for `MTEXT` and `MULTILEADER` output.
- [ ] Add per-entity logging for patched group codes and skipped handles.
- [ ] Add a validation tool that checks DXF code/value line pairing inside patched entity ranges.
- [ ] Add an option to preserve original text when the translator returns incomplete or suspicious output.

## Low Priority

- [ ] Split async translation logging into API request count and handle writeback count.
- [ ] Add CLI commands for common workflows.
- [ ] Add documentation for `.env` configuration and ODA troubleshooting.
- [ ] Add sample screenshots or viewer validation notes.
- [ ] Add a cleanup command for generated diagnostic DXF files.

## Completed

- [x] Confirmed ODA direct DWG to DXF conversion preserves target `MULTILEADER` display.
- [x] Confirmed zero-change `ezdxf.readfile()` plus `doc.saveas()` breaks target `MULTILEADER` display.
- [x] Added direct ODA conversion utility at `dwg-utils/dwg_to_dxf.py`.
- [x] Added raw DXF `MULTILEADER` extraction from group code `304`.
- [x] Added direct DXF text patching to avoid final `ezdxf.saveas()` for DWG input.
- [x] Fixed DXF patcher scanning to respect code/value line pairs.
- [x] Verified `data/20260123_translated_translated.dxf` opens correctly and preserves the target arrows and labels.
- [x] Fixed Linux ODA execution with software rendering and `xvfb-run` fallback.
- [x] Added `tests/data/simple_case.dwg` and `tests/data/simple_case.oda.dxf` fixtures for text patching regression coverage.
- [x] Added sampling scripts under `tests/scripts/` to capture extraction, translation, direct patch, and patched DXF verification outputs.
- [x] Generated `tests/data/simple_case.*.json` baselines and `tests/data/simple_case.patched.dxf` from the sampling flow.
- [x] Added `tests/test_simple_case_regression.py` covering non-roundtrip DXF patch observations for `TEXT`, `MTEXT`, and `MULTILEADER`.
- [x] Verified the simple-case regression suite with `.venv/bin/python -m unittest tests.test_simple_case_regression`.
- [x] Supported non-roundtrip patch output for DXF input files, not only DWG input.
- [x] Added pre-API translation filtering for non-translatable CAD labels, including numbers, dimensions, page numbers, equipment slot labels, target-language text, and uppercase technical abbreviations.
- [x] Verified filtering with `.venv/bin/python -m unittest tests.test_translation_filter` and a full Baidu async run on `data/20260123.dwg`.
- [x] Added configurable glossary/allowlist loading from direct parameters, JSON text, JSON files, `.env`, and async example CLI arguments.
- [x] Added fixed glossary translations that are applied before cache lookup, filtering, and API calls.
- [x] Added direction-named zh-to-en glossary config at `config/cad_glossary_zh-en.json`.
- [x] Verified `examples/baidu_async_translate.py` with `--glossary-file config/cad_glossary_zh-en.json`, producing `data/20260123_translated_translated.dxf` with `327/327` direct patch writebacks.
- [x] Added `dwg-utils/check_text_layout.py` to detect translated text overflow against nearby frame/table containers using `ezdxf.addons.text2path`.
- [x] Added `dwg-utils/shrink_text_layout.py` to safely shrink overflowing `TEXT` height by raw DXF group code `40` patching with minimum height/scale limits.
- [x] Generated and verified `data/20260123_translated_shrunk.dxf`; `ezdxf.readfile()` opens it successfully and layout overflows dropped from `124` to `109` under conservative shrink limits.
