from docx import Document
from pathlib import Path

d = Document(Path(__file__).resolve().parents[1] / "Thesis Draft - Daan Luttik - MBA.docx")
names = sorted({s.name for s in d.styles if s.name})
out = Path(__file__).resolve().parents[1] / "docx-styles.txt"
out.write_text(
    "\n".join(names), encoding="utf-8"
)
