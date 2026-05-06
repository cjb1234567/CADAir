# CADAir TODO

Last updated: 2026-05-06

## High Priority

- [ ] Add translation filtering before API calls.
- [ ] Skip pure numbers, dimensions, page numbers, and equipment slot labels by default.
- [ ] Add a glossary/allowlist for CAD and electrical cabinet terms such as `ODF`, `PDU`, `CCU`, `ETH`, `RUN`, `ALM`, `PWR`, and cabinet IDs.

## Medium Priority

- [ ] Improve long translation layout handling.
- [ ] Add optional text wrapping for `MTEXT` and `MULTILEADER` output.
- [ ] Add width/height adaptation for translated `TEXT` where safe.
- [ ] Add per-entity logging for patched group codes and skipped handles.
- [ ] Add a validation tool that checks DXF code/value line pairing inside patched entity ranges.
- [ ] Add an option to preserve original text when the translator returns incomplete or suspicious output.

## Low Priority

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
