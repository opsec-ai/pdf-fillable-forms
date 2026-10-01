#!/usr/bin/env python3
"""Detect fillable blanks in a static PDF and emit a field map (fields.json).

Finds:
  - text fields: horizontal rules/underline runs (30..480 pt) used as fill-in blanks
  - checkboxes / radio pairs: small square rects (4..14 pt)

Usage:
  python3 detect.py input.pdf fields.json [--pages 1 2 ...] [--min-w 30] [--max-w 480]
"""
import json
import sys

import pdfplumber

# ---- heuristics (measured on real forms; tune per document if needed) ----
RUN_HEIGHT_MAX = 3.5    # underline stroke height
RUN_WIDTH_MIN = 30.0    # shorter = dashes/dots noise
RUN_WIDTH_MAX = 480.0   # wider = full-width section rules (skip)
MERGED_GAP = 6.0        # merge dotted-underline segments that are this close
BOX_MIN = 4.0           # checkbox/radio square sizes
BOX_MAX = 14.0
RADIO_GAP_MAX = 170.0   # 2 boxes on one row closer than this = radio pair

def sanitize(s):
    return "".join(c if c.isalnum() else "_" for c in s).strip("_")[:30]

def nearest_right(words, x0, top, tol=8):
    cands = [w for w in words if abs(w["top"] - top) < tol and w["x0"] >= x0 - 2]
    if not cands:
        return None
    return sanitize(min(cands, key=lambda w: w["x0"])["text"])

def unique_name(base, used):
    name, i = base, 1
    while name in used:
        name = f"{base}_{i}"
        i += 1
    used.add(name)
    return name

def main():
    src, out = sys.argv[1], sys.argv[2]
    args = list(sys.argv)
    only_pages = []
    for opts in ([s for s in args if s.startswith("--")]):
        pass
    min_w = RUN_WIDTH_MIN
    max_w = RUN_WIDTH_MAX
    if "--min-w" in args:
        min_w = float(args[args.index("--min-w") + 1])
    if "--max-w" in args:
        max_w = float(args[args.index("--max-w") + 1])
    if "--pages" in args:
        i = args.index("--pages")
        only_pages = [int(p) for p in args[i + 1].split(",")]

    fields = []
    used_text, used_box = set(), set()
    n_blank = 0

    with pdfplumber.open(src) as pdf:
        for pi, page in enumerate(pdf.pages):
            if only_pages and (pi + 1) not in only_pages:
                continue
            words = page.extract_words()

            # ---------- text fields from underline runs ----------
            objs = [o for o in (page.rects + page.lines)
                    if o.get("height", 0) < RUN_HEIGHT_MAX and o.get("width", 0) > 1]
            rows = {}
            for o in objs:
                rows.setdefault(round(o["top"] / 2.5), []).append((o["x0"], o["x1"]))

            for yk in sorted(rows):
                segs = sorted(rows[yk])
                runs = []
                for x0, x1 in segs:
                    if runs and x0 - runs[-1][1] < MERGED_GAP:
                        runs[-1] = (runs[-1][0], max(runs[-1][1], x1))
                    else:
                        runs.append((x0, x1))
                for x0, x1 in runs:
                    w = x1 - x0
                    if w < min_w or w > max_w:
                        continue
                    n_blank += 1
                    top = yk * 2.5
                    label = nearest_right(words, x0, top - 14, tol=18) or f"blank{n_blank}"
                    fields.append({
                        "type": "text",
                        "name": unique_name("T_" + label, used_text),
                        "page": pi, "x": round(x0, 1), "y": round(top, 1),
                        "w": round(w, 1), "h": 14.0,
                    })

            # ---------- checkboxes / radio groups ----------
            sq = [o for o in (page.rects + page.lines)
                  if BOX_MIN < o.get("width", 0) < BOX_MAX and BOX_MIN < o.get("height", 0) < BOX_MAX]
            rowq = {}
            for o in sq:
                rowq.setdefault(round(o["top"] / 2), []).append(o)

            grp_idx = 0
            for tk in sorted(rowq):
                boxes = sorted(rowq[tk], key=lambda o: o["x0"])
                top = tk * 2.0

                def add_radio(b1, b2):
                    nonlocal grp_idx
                    grp_idx += 1
                    gname = f"RG{grp_idx}"
                    for b, fallback in ((b1, "o1"), (b2, "o2")):
                        fields.append({
                            "type": "radio", "group": gname,
                            "option": nearest_right(words, b["x1"] + 1, top) or fallback,
                            "page": pi, "x": round(b["x0"], 1), "y": round(b["top"], 1),
                            "w": round(b["x1"] - b["x0"], 1),
                            "h": round(b["bottom"] - b["top"], 1),
                        })

                if len(boxes) == 2 and boxes[1]["x0"] - boxes[0]["x1"] < RADIO_GAP_MAX:
                    add_radio(boxes[0], boxes[1])          # Yes/No, Single/Joint, ...
                elif len(boxes) == 4:
                    add_radio(boxes[0], boxes[1])          # Owner/Tenant pair
                    add_radio(boxes[2], boxes[3])          # Rental/Seasonal pair
                else:
                    for o in boxes:                        # independent checkboxes
                        label = (nearest_right(words, o["x1"] + 1, top)
                                 or nearest_right(words, o["x1"] + 1, top - 20)
                                 or f"box{round(o['x0'])}")
                        fields.append({
                            "type": "checkbox",
                            "name": unique_name("C_" + label, used_box),
                            "page": pi, "x": round(o["x0"], 1), "y": round(o["top"], 1),
                            "w": round(o["x1"] - o["x0"], 1),
                            "h": round(o["bottom"] - o["top"], 1),
                        })

    with open(out, "w") as f:
        json.dump(fields, f, indent=1)
    kinds = {}
    for x in fields:
        kinds[x["type"]] = kinds.get(x["type"], 0) + 1
    print(f"{len(fields)} fields on {len(set(f['page'] for f in fields))} page(s): {kinds} -> {out}")

if __name__ == "__main__":
    main()