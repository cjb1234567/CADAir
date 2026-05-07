# Work Summary: Text Layout Overflow Detection and Safe Shrink

Date: 2026-05-07

## Goal

Detect translated CAD text that exceeds nearby frame/table cell boundaries and provide a conservative utility to shrink overflowing `TEXT` entities without running a full `ezdxf.saveas()` roundtrip.

## Changes

- Added text layout checking and safe shrinking, now exposed through `cadair layout` and implemented in `cadair/layout.py`.
- Used `ezdxf.readfile()` for analysis only.
- Used `ezdxf.addons.text2path` to compute text path bounding boxes where available.
- Inferred rectangular text containers from nearby horizontal/vertical `LINE` and `LWPOLYLINE` segments in the same layout/block.
- Included anonymous block definitions such as `*U4` by default because ODA-generated title blocks can store editable text there.
- Added safety margin support via `--margin-ratio`, defaulting to 5%.
- Implemented shrink output by raw DXF patching group code `40` for `TEXT` height, avoiding `ezdxf.saveas()`.
- Added guardrails for shrink output:
  - `--scale-threshold`
  - `--min-height`
  - `--min-scale`
  - `--dry-run`
  - refusal to overwrite input DXF in place

## Layout Checker

Focused check for a known long title:

```bash
cadair layout \
  data/20260123_translated_translated.dxf \
  --contains "Installation diagram of energy management" \
  --json /tmp/opencode/installation_layout_report.json \
  --limit 20
```

Observed result:

```text
checked_texts=7 containers_found=7 overflows=7
```

Representative output:

```text
overflow handle=97E9 type=TEXT layer=可编辑文字 height=3.5 sides=left,right required_scale=0.496
  text=Installation diagram of energy management system cabinet
  bbox=[220.7488, 16.7885, 364.6755, 21.4349]
  container=[253.0390, 5.0379, 332.3853, 33.0379]
```

With `--margin-ratio 0`, the same small title text still overflowed and required about `0.551` scale, confirming the issue was not just safety margin noise.

Full check on `data/20260123_translated_translated.dxf`:

```text
checked_texts=1097 containers_found=521 overflows=124
```

Filtering out `scale=1.0` left 65 stronger overflow candidates.

## Shrink Utility

Dry-run example:

```bash
cadair layout \
  data/20260123_translated_translated.dxf \
  --shrink \
  --scale-threshold 0.8 \
  --min-height 2.0 \
  --min-scale 0.65
```

Generate a new DXF:

```bash
cadair layout \
  data/20260123_translated_translated.dxf \
  data/20260123_translated_shrunk.dxf \
  --shrink \
  --scale-threshold 0.8 \
  --min-height 2.0 \
  --min-scale 0.65 \
  --json /tmp/opencode/20260123_translated_shrunk_report.json
```

Observed result:

```text
shrink_candidates=52 patched=52
```

The generated DXF was readable by `ezdxf`:

```text
readable AC1021 5649
```

Layout check after shrink:

```text
checked_texts=1097 containers_found=521 overflows=109
```

Some text remains flagged because minimum size limits intentionally prevent excessive shrinking. For example, small title text with required scale `0.496` was clamped by `--min-scale 0.65`:

```text
height=3.5 -> 2.275
required_scale=0.496
applied_scale=0.650 clamped
```

## Notes

- This is a conservative layout adaptation tool, not a complete CAD collision detector.
- Container detection currently targets axis-aligned frame/table cells from `LINE` and `LWPOLYLINE` geometry.
- The checker can report false positives for text that intentionally sits close to a border or is affected by font/path metric differences.
- The shrinker only changes `TEXT` height group code `40`; it does not split text, convert `TEXT` to `MTEXT`, move text, or modify `MULTILEADER` geometry.
- For very long translated title text, short glossary translations are still preferred over aggressive shrink, because shrinking below roughly 50%-60% can reduce readability.

## Generated Artifacts

- `data/20260123_translated_shrunk.dxf`
- `/tmp/opencode/20260123_translated_shrunk_report.json`
- `/tmp/opencode/20260123_translated_shrunk_layout_report.json`
