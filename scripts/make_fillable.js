// Turn a static PDF + fields.json (from detect.py) into an AcroForm fillable PDF.
//
// Usage:
//   npm i pdf-lib
//   node make_fillable.js <fields.json> <input.pdf> <output.pdf> [top_gap_pt]
//
// top_gap_pt: distance from the printed underline to the TOP edge of the text
// widget (default 11.11). See SKILL.md "Baseline math" for why.
const fs = require("fs");
const { PDFDocument, rgb, PDFName } = require("pdf-lib");

const [, , FIELDS_JSON, SRC, OUT, GAP_ARG] = process.argv;
if (!FIELDS_JSON || !SRC || !OUT) {
  console.error("usage: node make_fillable.js <fields.json> <input.pdf> <output.pdf> [top_gap_pt]");
  process.exit(1);
}

const TEXT_H = 13;                       // text widget height (click target)
const BASELINE_DIP = 3.0895;             // pdf-lib draws baseline this many pt
                                         // above the widget BOTTOM (measured)
const RAISE = 1.2;                       // user preference: text ~3px (1.2pt)
                                         // ABOVE the printed line
const TOP_GAP = GAP_ARG ? parseFloat(GAP_ARG) : TEXT_H - BASELINE_DIP + RAISE;

const fields = JSON.parse(fs.readFileSync(FIELDS_JSON, "utf8"));

async function main() {
  const doc = await PDFDocument.load(fs.readFileSync(SRC), { updateMetadata: false });
  let form;
  try { form = doc.getForm(); } catch { form = doc.createForm(); }

  const groups = {};
  let n = 0;

  for (const f of fields) {
    const page = doc.getPage(f.page);
    const H = page.getHeight();

    if (f.type === "text") {
      // The underline is the bottom of the writing area: widget top sits TOP_GAP
      // above it so the typed baseline lands RAISE pt above the line.
      const yBottom = H - f.y + TOP_GAP - TEXT_H;
      const tf = form.createTextField(f.name);
      tf.addToPage(page, {
        x: f.x, y: yBottom, width: f.w, height: TEXT_H,
        textColor: rgb(0, 0, 0),
        // CRITICAL: pdf-lib's defaults are WHITE background + BLACK 1pt border.
        // Pass undefined explicitly or every field is an opaque box.
        backgroundColor: undefined,
        borderColor: undefined,
        borderWidth: 0,
      });
      tf.setFontSize(9.5);
      // Drop the /MK dict so viewers never draw border/background hints.
      // Do NOT delete the /AP - pdf-lib regenerates it at save anyway, and
      // viewers (Chrome's PDFium) reuse its text matrix when rendering values.
      tf.acroField.getWidgets()[0].dict.delete(PDFName.of("MK"));
    } else if (f.type === "checkbox") {
      const cb = form.createCheckBox(f.name);
      cb.addToPage(page, { x: f.x, y: H - f.y - f.h, width: f.w, height: f.h });
      const widget = cb.acroField.getWidgets()[0];
      const mk = widget.dict.get(PDFName.of("MK"));
      if (mk) { mk.set(PDFName.of("BG"), doc.context.obj([])); mk.set(PDFName.of("BC"), doc.context.obj([0, 0, 0])); }
    } else if (f.type === "radio") {
      if (!groups[f.group]) groups[f.group] = form.createRadioGroup(f.group);
      groups[f.group].addOptionToPage(f.option, page, { x: f.x, y: H - f.y - f.h, width: f.w, height: f.h });
      const widget = groups[f.group].acroField.getWidgets()
        .find((w) => Math.abs(w.getRectangle().x - f.x) < 0.1);
      if (widget) {
        const mk = widget.dict.get(PDFName.of("MK"));
        if (mk) { mk.set(PDFName.of("BG"), doc.context.obj([])); mk.set(PDFName.of("BC"), doc.context.obj([0, 0, 0])); }
      }
    }
    n++;
  }

  fs.writeFileSync(OUT, await doc.save());
  console.log(`wrote ${OUT}: ${n} widgets, ${Object.keys(groups).length} radio groups (top_gap=${TOP_GAP.toFixed(2)})`);
}
main().catch((e) => { console.error(e); process.exit(1); });