#!/usr/bin/env python3
"""Verify where typed text actually lands in a newly generated fillable PDF.

Fills the first text field with a probe value (with NO descenders, e.g. "JANE"),
renders the page before/after with pypdfium2 (the same engine as Chrome's PDF
viewer), and pixel-diffs to find the text baseline. Prints the offset from the
printed underline in points. Expect a small NEGATIVE value (text above the line);
our preferred default is about -1.2 pt.

Usage:
  python3 verify_fill.py editable.pdf fields.json [scale] [field_name]
"""
import math
import sys

import numpy as np
import pypdf
import pypdfium2 as pdfium
from PIL import Image

ED, FIELDS = sys.argv[1], sys.argv[2]
SCALE = int(sys.argv[3]) if len(sys.argv) > 3 else 4
WANT_NAME = sys.argv[4] if len(sys.argv) > 4 else None

import json
with open(FIELDS) as f:
    fields = json.load(f)

text_fields = [f for f in fields if f["type"] == "text"]
if not text_fields:
    print("no text fields to verify"); sys.exit(1)
probe = WANT_NAME or text_fields[0]["name"]
line_y = next(f["y"] for f in fields if f["name"] == probe)

# Tight window around the printed line: typed text occupies roughly y in
# [line-14, line+4]pt (widget top sits ~11pt above the line). A wider window picks
# up OTHER widgets - with /NeedAppearances set, pypdfium (like Chrome) re-synthesizes
# every widget's appearance, so adjacent checkboxes/radios pollute a page-wide diff.
FILLED = "/tmp/pdf_verify_filled.pdf"

def render(path):
    pdf = pdfium.PdfDocument(path)
    pdf.init_forms()
    return np.array(pdf[0].render(scale=SCALE).to_pil().convert("L"))

before = render(ED)

w = pypdf.PdfWriter()
w.append(ED)
w.update_page_form_field_values(w.pages[0], {probe: "JANE"})
w.set_need_appearances_writer(True)
with open(FILLED, "wb") as fh:
    w.write(fh)
after = render(FILLED)

diff = np.abs(before.astype(int) - after.astype(int)) > 40
col = next(f for f in fields if f["name"] == probe)
x0, x1 = int(col["x"] * SCALE), int((col["x"] + col["w"]) * SCALE)
lo, hi = int((line_y - 14) * SCALE), int((line_y + 4) * SCALE)
zone = diff[lo:hi, x0:x1]
ys, xs = np.where(zone)
if len(ys) == 0:
    print(f"FAIL: '{probe}' text not rendered (check /DA, viewer support, or "
          f"that regular viewers regenerate appearances)")
    sys.exit(1)
line_px = line_y * SCALE
baseline_px = ys.max() + lo
delta_pt = (baseline_px - line_px) / SCALE
print(f"'{probe}': text_top {ys.min() + lo}px, baseline {baseline_px}px "
      f"vs line {line_px}px -> {delta_pt:+.2f}pt from line; start x "
      f"{(xs.min() + x0)/SCALE - col['x']:+.1f}pt after field left edge")
if math.isclose(delta_pt, -1.2, abs_tol=1.5):
    print("PASS (baseline ~1.2pt above the line)")
elif -3.5 <= delta_pt <= 1.0:
    print("OK (slightly different but text sits on/near the line)")
else:
    print("NOTE: adjust RAISE in make_fillable.js if this is off")
    sys.exit(2)