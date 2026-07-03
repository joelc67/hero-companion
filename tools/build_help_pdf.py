"""Build the in-app Help PDF (static/help/HeroCompanion-Help.pdf) from docs/help.md +
CHANGELOG.md, stamped with the app / model / database versions. Re-run after editing
either document or bumping VERSION:  python tools/build_help_pdf.py
"""
import datetime
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
from fpdf import FPDF
from fpdf.enums import XPos, YPos

def _mc(pdf, h, txt):
    """multi_cell that always returns the cursor to the left margin, next line."""
    pdf.multi_cell(0, h, txt, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "static", "help", "HeroCompanion-Help.pdf")

# Segoe UI ships with Windows — full Latin + punctuation coverage (no emoji; stripped below).
FONTS = {"": r"C:\Windows\Fonts\segoeui.ttf", "B": r"C:\Windows\Fonts\segoeuib.ttf",
         "I": r"C:\Windows\Fonts\segoeuii.ttf"}


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _versions():
    app_v = _read(os.path.join(ROOT, "VERSION")).strip()
    try:
        db_v = json.loads(_read(os.path.join(ROOT, "data", "archetypes.json"))).get("version", "?")
    except Exception:
        db_v = "?"
    m = re.search(r"MODEL_VERSION\s*=\s*(\d+)", _read(os.path.join(ROOT, "server", "first_principles.py")))
    return app_v, db_v, (m.group(1) if m else "?")


def _clean(text):
    # strip emoji/pictographs (font has no glyphs) but keep typographic punctuation
    text = re.sub(r"[\U0001F000-\U0001FAFF←-⯿️]", "", text)
    # markdown links -> "text (url)"
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", text)
    return text


class HelpPDF(FPDF):
    version_line = ""

    def footer(self):
        self.set_y(-14)
        self.set_font("ui", "", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, f"Hero Companion · {self.version_line} · page {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)


def _write_inline(pdf, line, h):
    """Write a body line honoring **bold** and *italic* spans."""
    parts = re.split(r"(\*\*[^*]+\*\*|\*[^*\n]+\*)", line)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            pdf.set_font("ui", "B", pdf.font_size_pt)
            pdf.write(h, part[2:-2])
            pdf.set_font("ui", "", pdf.font_size_pt)
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            pdf.set_font("ui", "I", pdf.font_size_pt)
            pdf.write(h, part[1:-1])
            pdf.set_font("ui", "", pdf.font_size_pt)
        else:
            pdf.write(h, part)


def _render_md(pdf, text):
    para_open = False
    for raw in _clean(text).split("\n"):
        ln = raw.rstrip()
        if not ln.strip():
            if para_open:
                pdf.ln(9)
                para_open = False
            continue
        if ln.startswith("# "):
            pdf.ln(4); pdf.set_font("ui", "B", 17); pdf.set_text_color(20, 60, 120)
            _mc(pdf, 8, ln[2:]); pdf.set_text_color(0, 0, 0); pdf.ln(1)
        elif ln.startswith("## "):
            pdf.ln(4); pdf.set_font("ui", "B", 13.5); pdf.set_text_color(20, 60, 120)
            _mc(pdf, 7, ln[3:]); pdf.set_text_color(0, 0, 0); pdf.ln(1)
        elif ln.startswith("### "):
            pdf.ln(3); pdf.set_font("ui", "B", 11.5)
            _mc(pdf, 6, ln[4:]); pdf.ln(1)
        elif ln.startswith("- "):
            if para_open:
                pdf.ln(6); para_open = False
            pdf.set_font("ui", "", 10.5)
            pdf.set_x(pdf.l_margin + 4)
            pdf.write(5.6, "•  ")
            _write_inline(pdf, ln[2:], 5.6)
            pdf.ln(6)
        elif ln.strip() == "---":
            pdf.ln(3)
        else:
            pdf.set_font("ui", "", 10.5)
            _write_inline(pdf, ln + " ", 5.6)
            para_open = True
    if para_open:
        pdf.ln(8)


def main():
    app_v, db_v, model_v = _versions()
    today = datetime.date.today().strftime("%B %d, %Y")

    pdf = HelpPDF(format="letter")
    pdf.version_line = f"v{app_v}"
    for style, path in FONTS.items():
        pdf.add_font("ui", style, path)
    pdf.set_margins(20, 18, 20)
    pdf.set_auto_page_break(True, margin=18)
    pdf.add_page()

    # cover block
    pdf.set_font("ui", "B", 26); pdf.set_text_color(20, 60, 120)
    _mc(pdf, 12, "Hero Companion")
    pdf.set_font("ui", "", 12); pdf.set_text_color(70, 70, 70)
    _mc(pdf, 7, "Help & Release Notes — your City of Heroes sidekick")
    pdf.ln(2)
    pdf.set_font("ui", "", 9.5)
    _mc(pdf, 5.5, f"App version {app_v}   ·   Model v{model_v}   ·   Game database {db_v}\n"
                  f"Generated {today}   ·   free & noncommercial forever (CC BY-NC-SA 4.0)")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    _render_md(pdf, _read(os.path.join(ROOT, "docs", "help.md")).split("\n", 1)[1])  # skip md title (cover has it)
    pdf.add_page()
    _render_md(pdf, _read(os.path.join(ROOT, "CHANGELOG.md")))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pdf.output(OUT)
    print(f"OK  {OUT}  ({os.path.getsize(OUT):,} bytes)  app v{app_v} / model v{model_v} / db {db_v}")


if __name__ == "__main__":
    main()
