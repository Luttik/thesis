"""OCR/extract Benninger PDF to text file."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "sources/academic/benninger - collective shaping.pdf"
OUT = Path(__file__).with_name("benninger-extract.txt")


def main() -> None:
    lines: list[str] = []
    try:
        import fitz

        doc = fitz.open(PDF)
        lines.append(f"pages={len(doc)}")
        for i, page in enumerate(doc):
            text = page.get_text()
            lines.append(f"\n--- page {i + 1} text_len={len(text)} ---\n{text}")
            if len(text.strip()) < 50:
                try:
                    tp = page.get_textpage_ocr(language="eng", dpi=200)
                    ocr = tp.extractText()
                    lines.append(f"\n--- page {i + 1} OCR ---\n{ocr}")
                except Exception as ocr_err:
                    lines.append(f"OCR failed: {ocr_err}")
    except ImportError:
        from pypdf import PdfReader

        reader = PdfReader(str(PDF))
        lines.append(f"pages={len(reader.pages)}")
        for i, page in enumerate(reader.pages):
            lines.append(f"\n--- page {i + 1} ---\n{page.extract_text() or ''}")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote", OUT, "size", OUT.stat().st_size)


if __name__ == "__main__":
    main()
