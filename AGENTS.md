# AGENTS.md

Guidance for agents working in this repository.

## What this repo is

A Crush **skill** (`pdf-fillable-forms`): a self-contained toolkit that turns a
static PDF (blanks drawn as printed lines/rules, tick boxes) into a genuinely
fillable AcroForm. It is NOT an application or library. The consumer of this
code is an LLM agent (Crush) that follows `SKILL.md`, not a human API.

Three scripts run in a fixed order and exchange data through a JSON field map:

```
detect.py ──> fields.json ──> make_fillable.js ──> output.pdf ──> verify_fill.py
```

The bundled source *is* the deliverable alongside SKILL.md; contributors edit
here, not in SKILL.md's prose. Keep the two in sync.

## The three scripts

| Script | Lang | Role | Signature |
|---|---|---|---|
| `scripts/detect.py` | Python | Finds blanks/boxes, emits `fields.json` | `detect.py input.pdf fields.json [--pages 1,2] [--min-w 30] [--max-w 480]` |
| `scripts/make_fillable.js` | Node (`pdf-lib`) | Builds the fillable AcroForm PDF | `make_fillable.js fields.json input.pdf output.pdf [top_gap_pt]` |
| `scripts/verify_fill.py` | Python | Pixel-verifies where typed text lands | `verify_fill.py editable.pdf fields.json [scale] [field_name]` |

It is a Unix pipeline: each script does the task SKILL.md says it does and
prints a summary. The `fields.json` field map is the contract between them and
must not be reserialized by any other tool between steps (detect writes it,
make_fillable reads it, verify_fill re-reads the original).

## Field map (`fields.json`) schema

Array of objects. `type` is one of `text`, `checkbox`, `radio`. Common keys:
`page` (0-based), `x`, `y`, `w`, `h` (points, from pdfplumber top-left
coordinates). Naming differs by type:

- **text**: `name` e.g. `T_First_Name` (must be globally unique).
- **checkbox**: `name` e.g. `C_label`.
- **radio**: no `name`; has `group` (e.g. `RG1`) plus `option` (e.g. `o1`, or
  the label text). Radios in the same `group` are one mutually-exclusive set.

Note the coordinate convention: `detect.py` reports `y` measured from the page
**top** (pdfplumber). `make_fillable.js` flips it to pdf-lib's bottom-left
origin via `y = H - f.y` (see `yBottom` / `H - f.y - f.h`). Don't "fix" one
side without the other.

## Dependencies

- Python 3 + `pdfplumber pypdf pypdfium2 Pillow numpy`
- Node + `pdf-lib` (from `npm i pdf-lib`)
- `qpdf` optional (validation only)
- No lockfile or bundled vendor code; the agent installs these ad hoc.

## Conventions & gotchas (do not "fix")

These are measured, intentional behaviors. Preserve them exactly:

- **pdf-lib `addToPage` defaults are a white background + black 1pt border.**
  Every text field must pass `backgroundColor: undefined, borderColor:
  undefined, borderWidth: 0`, or the whole form becomes opaque white boxes.
- **Do NOT delete the widget `/AP`.** pdf-lib regenerates an appearance at save
  whenever a widget lacks one, so deleting it is futile; leave the transparent
  AP it generates. Only delete the `/MK` dict (so no border/background hints
  survive). Checkboxes/radios keep their border (overlays the printed square)
  but get an empty background fill.
- **`BASELINE_DIP = 3.0895` and `RAISE = 1.2`** in `make_fillable.js` are
  crafted constants. The typed-text baseline lands `BASELINE_DIP` pt above the
  widget's bottom; `RAISE` lifts it ~1.2pt above the printed line (the
  user-preferred "handwriting" reading). `top_gap` default is derived:
  `TEXT_H - BASELINE_DIP + RAISE` = 11.11. Change these only via SKILL.md's
  instructions, and always re-verify after.
- Text widget height is a fixed `TEXT_H = 13` click target (not the underline's
  height); field font size is hardcoded `9.5`.
- **Config maps are tuned from real forms**: widths 30..480pt (text blanks),
  boxes 4..14pt, stroke height < 3.5pt, `MERGED_GAP 6.0` for dotted underlines
  → one blank, radio pair gap `RADIO_GAP_MAX 170`. A row's checkbox count is
  the grouping signal: 2 → one radio pair, 4 → two pairs, else independent
  checkboxes. Tune via the `--min-w/--max-w/--pages` flags, not by editing the
  constants when the project isn't broken.
- Unique names are mandatory: pdf-lib throws on duplicate field names (see
  `detect.py`'s `unique_name` / `used_text` / `used_box`).
- `make_fillable.js` text-matrix constant controls where *every* viewer renders
  typed text; Acrobat re-lays-out text when it regenerates appearances, so
  measured baselines differ by viewer. Don't "fix" toward Acrobat's numbers.

## Testing / validation

No unit test suite. Validation is a manual pipeline (see SKILL.md Workflow):

1. Inspect: `pypdf` check the PDF isn't a scan and is a form-less static
   file. Image-only forms must be OCR'd first; the vector line detection will
   not find blanks in a scan.
2. `verify_fill.py` fills a probe value (`"JANE"` — no descenders), renders
   before/after with pypdfium2 (Chrome's engine), pixel-diffs **only within a
   tight window** around the field (`[line-14, line+4]`pt) because other
   widgets' re-synthesized appearances pollute a page-wide diff. It PASSes at
   baseline ≈ `-1.2pt`.

After touching `make_fillable.js` math, ALWAYS re-run the pipeline against a
representative form. The `RAISE`/`TOP_GAP` tuning note expects a real measured
target: don't change baseline behavior on theory.

## Style

- Python: bare `#!/usr/bin/env python3`, hand-rolled `argparse`-free usage via
  `sys.argv` (trace the `"--min-w"`/`"--pages"` parse in `detect.py`); the
  linter flags E501 line-length noise but it isn't enforced.
- Shell command access through `scripts/*`, adjacent helper functions only.

## Editing SKILL.md

AGENTS.md documents the code and workflow; the prose implementation, baseline
math, and troubleshooting decision tree live in `SKILL.md`. Update that file
when a behavioral/constant change is user-visible (`top_gap`/`RAISE` changes,
detection heuristics) so the agent following it does not drift from the code.