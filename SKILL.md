---
name: pdf-fillable-forms
description: Convert a static PDF (application, registration, membership, contract - usually one with printed blank lines, dash rows, and tick boxes) into a genuinely fillable AcroForm PDF with invisible text fields over every blank, plus checkboxes and radio groups. Use whenever the user asks to "make this PDF editable", "make it fillable / typeable", "add form fields / blank boxes", "turn the blank lines into input fields", "so I can type answers in and save it", or hands you a form PDF that has no interactive fields. Also use when an existing fillable PDF's fields render as opaque white boxes with borders, or typed text lands above/below the printed lines.
---

# Making PDF forms fillable

Goal: keep the printed page pixel-identical, and lay invisible AcroForm widgets over
the existing blanks so the user can type into the form and save it. The finished
fields must show NO border and NO background, and typed text must sit exactly on
the printed lines.

Bundled scripts (run in this order):

1. `scripts/detect.py input.pdf fields.json` - finds blanks, emits a field map
2. `scripts/make_fillable.js fields.json input.pdf output.pdf [top_gap]` - builds the fillable PDF
3. `scripts/verify_fill.py output.pdf fields.json` - pixel-verifies where typed text lands

Dependencies: `python3` with `pdfplumber pypdf pypdfium2 Pillow numpy`, `node` with
`pdf-lib`, and `qpdf` (optional, for validation).

## Workflow

1. Inspect the PDF first:

   ```python
   from pypdf import PdfReader
   r = PdfReader("form.pdf")
   print(len(r.pages), r.get_fields())       # None = no existing form = our case
   for p in r.pages: print(p.extract_text()[:300])
   ```

   - Text extractable and blanks are drawn as rules/rects -> proceed with this skill.
   - Scanned / image-only (little or no extractable text): OCR it first (render with
     pdfium, OCR with tesseract, overlay positioned text) - the line-detection below
     will NOT find vector blanks in a scan.

2. Detect: `python3 scripts/detect.py form.pdf fields.json`

   Heuristics (measured on real forms; tweak via `--min-w/--max-w/--pages` when noise
   appears):
   - **Text blanks** = horizontal rect/line runs, stroke height < 3.5pt, merged when
     segments are < 6pt apart (dotted underlines become one blank), kept when width
     is 30..480pt. Wider runs are full-page section rules, not blanks.
   - **Checkboxes** = near-square rects 4..14pt. Same row: exactly 2 with a small gap
     -> radio pair (Yes/No, Single/Joint); exactly 4 -> two radio pairs
     (Owner/Tenant + Rental/Seasonal); anything else -> independent checkbox.
   - Field names come from the nearest printed word (deduped; unique names are
     mandatory - pdf-lib throws on duplicates).

3. Build: `node scripts/make_fillable.js fields.json form.pdf "form (Editable).pdf"`

   The script does the important parts for you, but know why:

   - **pdf-lib's `addToPage` defaults are white background + black 1pt border.**
     Every field would be an opaque box. Pass `backgroundColor: undefined,
     borderColor: undefined, borderWidth: 0` explicitly.
   - Deleting the widget's `/AP` does NOT stick - pdf-lib regenerates the appearance
     at save whenever a widget lacks one. So leave the (transparent) AP it generates,
     and only delete the `/MK` dict so no border/background hints remain.
   - Checkboxes/radios keep their border (it overlays the printed square 1:1) but get
     an empty background fill. Their rect must exactly equal the printed square, or
     the widget obscures content around it (verify with the ring check in step 4).

4. Validate:

   ```bash
   qpdf --check "form (Editable).pdf"
   python3 -c "
   from pypdf import PdfReader
   print(len(PdfReader('form (Editable).pdf').get_fields()))"
   python3 scripts/verify_fill.py "form (Editable).pdf" fields.json
   ```

   `verify_fill.py` fills a probe value ("JANE" - no descenders), renders the page
   before/after with pypdfium2 (Chrome's PDF engine), and reports the text baseline
   offset from the printed line in points. It prints PASS when the baseline is about
   1.2pt above the line.

## Baseline math (why text lands where it does)

pdf-lib writes a text-matrix constant into each text field's appearance stream. When
a viewer (Chrome/PDFium and most open-source viewers) renders a typed value, it
reuses that matrix: the baseline ends up `BASELINE_DIP` pt above the widget's
BOTTOM edge. For a 13pt-tall field at font size 9.5, `BASELINE_DIP = 3.09` (14pt
tall gives 4.27). The widget currently has its top at `top_gap = 13 - 3.09 + raise`
above the underline, so baseline = line - raise.

- `raise = 1.2` is the user-preferred setting: typed text sits ~3px (~1.2pt) ABOVE
  the line, which reads as handwriting-style "on the line" in practice. Baseline
  exactly AT the line reads slightly low to most people.
- To move text up/down, pass a custom `top_gap` (larger = text higher) or change
  `RAISE` in the script.
- Verify after every change: `verify_fill.py` prints the measurement, don't guess.

Tune per viewed target: if the user opens the PDF in Adobe Acrobat (rather than a
PDFium-based viewer), Acrobat regenerates text appearances with its own layout and
roughly centers text in the widget - the verification script then reports a value
that will not match your other viewers, and the `top_gap` may need nudging (the
widget is also the click target, so keep it overlapping the blank).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Fields are white boxes / have borders | Built without the `undefined` color options from step 3 - rebuild |
| Typed text does not appear | Field has no `/DA` font+size (viewers need it to render values); check the widget dict |
| Text floats above the line | Decrease `top_gap` (or `RAISE`) |
| Text hangs below the line | Increase `top_gap` (or `RAISE`) |
| Widget obscures content beside a checkbox | Checkbox rect must equal the printed square exactly; re-detect |
| Stray extra fields on static labels | Harmless (invisible); narrow with `--min-w` or restrict `--pages` |
| Radios not mutually exclusive | Checkbox pairing heuristics failed (e.g. 3 boxes on a row) - merge manually |
| Viewer still highlights fields on hover | Viewer preference (Acrobat: Highlight Color -> None); not part of the file |

## Notes on scope

- Multi-line answer areas (tall blanks on the form) can be made `enableMultiline()`
  if the printed blank is clearly several lines tall; most single-line blanks should
  stay single-line so the baseline math holds.
- Only operate on the USER's document. If a form is password-protected or has an
  explicit "do not modify" restriction, stop and tell the user instead of bypassing.