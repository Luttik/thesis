from docx import Document
from pathlib import Path

d = Document(Path(__file__).resolve().parents[1] / "Thesis Draft - Daan Luttik - MBA.docx")
hits = [
    (i, p.style.name, p.text[:80])
    for i, p in enumerate(d.paragraphs)
    if any(k in p.text for k in ("3.4", "4.6", "Shenton", "Lincoln"))
]
Path(__file__).with_name("verify_output.txt").write_text(
    "\n".join(str(h) for h in hits), encoding="utf-8"
)
