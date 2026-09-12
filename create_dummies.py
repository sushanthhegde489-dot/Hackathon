from pathlib import Path
from pypdf import PdfWriter

d = Path("data/resumes")
d.mkdir(parents=True, exist_ok=True)
for i in range(18):
    pdf = PdfWriter()
    pdf.add_blank_page(width=100, height=100)
    with open(d / f"dummy_cand_{i}.pdf", "wb") as f:
        pdf.write(f)
