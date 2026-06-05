"""Build artifacts/section-42-quotes.html from QDPX quotation files."""
import os, re, html as html_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUOTATIONS_DIR = ROOT / "qdpx-coding" / "quotations"
OUT_PATH = ROOT / "artifacts" / "section-42-quotes.html"

INTERVIEWEE_MAP = {
    "Andreea Bulisache": (1, "Andreea Bulisache"),
    "Arjan Dijk": (2, "Arjan Dijk"),
    "Berfun Goodwin": (3, "Berfun Goodwin"),
    "Dennis Goedegebuure": (4, "Dennis Goedegebuure"),
    "Erik Hilhorst": (5, "Erik Hilhorst"),
    "Erica": (6, "Erica Hahn"),
    "Georgio Mosis": (7, "Georgio Mosis"),
    "Jon Stephan": (8, "Jon Stephan"),
    "Lauren Stokowski": (9, "Lauren Stokowski"),
    "Maarten Mantjes": (10, "Maarten Mantjes"),
    "Rolf Mulder": (11, "Rolf Mulder"),
    "Scott Brinker": (12, "Scott Brinker"),
    "Tim Wiegel": (13, "Tim Wiegel"),
    "Floris Reguoin": (14, "Floris Reguoin"),
    "Sylvia Vroklage": (15, "Sylvia Vroklage"),
    "Karin Boon": (17, "Karin Boon"),
}

SECTIONS = {
    "4.2.1": {
        "label": "section 4.2.1 — Capacity to change",
        "badge_class": "b421",
        "codes": [
            ("Obstacle: resistance", "Obstacle: resistance"),
            ("Tailwind: Experimenting with AI", "Tailwind: Experimenting with AI"),
            ("Tailwind: Educating / Training / Learning", "Tailwind: Educating / Training / Learning"),
            ("Obstacle: Delaying", "Obstacle: Delaying / analysis paralysis"),
            ("Obstacle: Lacking understanding of AI", "Obstacle: Lacking understanding of AI"),
            ("Obstacle: Lacking the skills", "Obstacle: Lacking the skills to execute"),
        ],
    },
    "4.2.2": {
        "label": "section 4.2.2 — Available resources",
        "badge_class": "b422",
        "codes": [
            ("Tailwind: Having data & tools available", "Tailwind: Having data & tools available"),
            ("Obstacle: Lacking solid data infrastructure", "Obstacle: Lacking solid data infrastructure"),
            ("Obstacle: Lacking systems thinking", "Obstacle: Lacking systems thinking or process knowledge"),
            ("Obstacle: Getting budgets", "Obstacle: Getting budgets"),
        ],
    },
    "4.2.3": {
        "label": "section 4.2.3 — Leadership & Governance",
        "badge_class": "b423",
        "codes": [
            ("Tailwind: AI champion", "Tailwind: AI champion"),
            ("Tailwind: Backed by leadership", "Tailwind: Backed by leadership"),
            ("Tailwind: Bringing people along", "Tailwind: Bringing people along"),
            ("Obstacle: high bureaucracy", "Obstacle: High bureaucracy / governance around AI"),
        ],
    },
}

CSS = """  :root {
    --ink: #1a1a1a; --muted: #5a6472; --line: rgba(0,0,0,.1);
    --bg: #f8f7f5; --card: #fff;
    --sans: system-ui, -apple-system, "Segoe UI", sans-serif;
    --serif: Georgia, "Times New Roman", serif;
  }
  *, *::before, *::after { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink);
         font-family: var(--sans); font-size: 15px; line-height: 1.55; }
  .wrap { max-width: 900px; margin: 0 auto; padding: 48px 24px 80px; }
  header { border-bottom: 2px solid var(--ink); padding-bottom: 16px; margin-bottom: 36px; }
  header h1 { margin: 0 0 6px; font-size: 24px; font-weight: 700; }
  header p  { margin: 0; color: var(--muted); font-size: 13px; }
  .section { margin-bottom: 52px; }
  .section-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
  .badge { font-size: 11px; font-weight: 700; letter-spacing: .06em;
           text-transform: uppercase; border-radius: 4px;
           padding: 3px 8px; color: #fff; white-space: nowrap; }
  .b421 { background: #15803d; }
  .b422 { background: #0f766e; }
  .b423 { background: #1d4ed8; }
  .section-header h2 { margin: 0; font-size: 17px; font-weight: 600; }
  .code-group { margin-bottom: 28px; }
  .code-label { font-size: 12px; font-weight: 600; text-transform: uppercase;
                letter-spacing: .06em; color: var(--muted);
                border-left: 3px solid var(--line); padding-left: 8px; margin-bottom: 10px; }
  .quote-card { background: var(--card); border: 1px solid var(--line);
                border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; }
  .interviewee { font-size: 11.5px; font-weight: 600; text-transform: uppercase;
                 letter-spacing: .05em; color: var(--muted); margin-bottom: 6px; }
  .interviewee .num { display: inline-block; background: var(--ink); color: #fff;
                      border-radius: 3px; padding: 1px 5px; font-size: 10px; margin-right: 4px; }
  blockquote { margin: 0; font-family: var(--serif); font-size: 14.5px;
               line-height: 1.6; color: #2a2a2a;
               border-left: 2px solid var(--line); padding-left: 12px; }"""


def clean_quote(text: str) -> str:
    text = re.sub(r"(\w)�(\w)", r"\1’\2", text)   # apostrophe in word
    text = re.sub(r"\s�\s", " — ", text)           # em-dash with spaces
    text = text.replace("�", "’")                   # remaining -> rsquo
    return text.strip()


def get_interviewee(fname: str):
    name = (fname
            .replace("Thesis Transcript ", "")
            .replace("Thesis interview ", "")
            .replace("Thesis transcript ", "")
            .replace(".md", ""))
    for key, (num, display) in INTERVIEWEE_MAP.items():
        if key.lower() in name.lower():
            return num, display
    if "16" in fname:
        return 16, "Anonymous"
    return None, name


def extract_quotes():
    results: dict[tuple[str, str], list[dict]] = {}
    for fname in sorted(os.listdir(QUOTATIONS_DIR)):
        if not fname.endswith(".md"):
            continue
        num, display_name = get_interviewee(fname)
        fpath = QUOTATIONS_DIR / fname
        content = fpath.read_text(encoding="utf-8-sig")
        blocks = re.split(r"\n(?=## )", content)
        for block in blocks:
            codes_in_block = re.findall(r"`([^`]+)`", block)
            lines = block.strip().split("\n")
            body_lines = [l.lstrip("> ").strip() for l in lines if l.startswith(">")]
            full_quote = clean_quote(" ".join(body_lines))
            if not full_quote or len(full_quote) < 25:
                continue
            for section_id, sdata in SECTIONS.items():
                for target_key, _display_label in sdata["codes"]:
                    for code in codes_in_block:
                        if target_key.lower() in code.lower():
                            key = (section_id, target_key)
                            if key not in results:
                                results[key] = []
                            results[key].append({"num": num, "name": display_name, "quote": full_quote})
                            break
    return results


def quote_card_html(entry: dict) -> str:
    num = entry["num"] or "?"
    name = html_module.escape(entry["name"] or "Unknown")
    quote = html_module.escape(entry["quote"])
    return (
        f'    <div class="quote-card">\n'
        f'      <div class="interviewee"><span class="num">{num}</span>{name}</div>\n'
        f"      <blockquote>{quote}</blockquote>\n"
        f"    </div>"
    )


def build_html(results: dict) -> str:
    sections_html = []
    for section_id, sdata in SECTIONS.items():
        code_groups = []
        for target_key, display_label in sdata["codes"]:
            entries = results.get((section_id, target_key), [])
            if not entries:
                continue
            cards = "\n".join(quote_card_html(e) for e in entries)
            escaped_label = html_module.escape(f"{display_label} — {len(entries)} quotes")
            code_groups.append(
                f'  <div class="code-group">\n'
                f'    <div class="code-label">{escaped_label}</div>\n'
                f"{cards}\n"
                f"  </div>"
            )
        badge = sdata["badge_class"]
        label = html_module.escape(sdata["label"])
        sections_html.append(
            f'<div class="section">\n'
            f'  <div class="section-header">'
            f'<span class="badge {badge}">{section_id}</span>'
            f"<h2>{label}</h2></div>\n"
            + "\n".join(code_groups)
            + "\n</div>"
        )

    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>Section 4.2 — QDPX quotations</title>\n"
        f"<style>\n{CSS}\n</style>\n</head>\n<body>\n<div class=\"wrap\">\n\n"
        "<header>\n"
        "  <h1>Section 4.2 &#8212; QDPX quotations</h1>\n"
        "  <p>All quotes coded for section 4.2 themes. Interviewee numbers match Table 1 in the thesis. "
        "Source: <code>qdpx/Thesis (Daan Luttik 2026-05-30).qdpx</code></p>\n"
        "</header>\n\n"
        + "\n\n".join(sections_html)
        + "\n\n</div>\n</body>\n</html>\n"
    )


if __name__ == "__main__":
    results = extract_quotes()
    total = sum(len(v) for v in results.values())
    print(f"Extracted {total} quotes across {len(results)} code groups")
    html_out = build_html(results)
    OUT_PATH.write_text(html_out, encoding="utf-8")
    print(f"Written: {OUT_PATH}")
