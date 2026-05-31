"""Compare user-saved thesis vs agent I15 patch in §4.1–§4.2."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER = (ROOT / ".cache" / "thesis-user-saved.md").read_text(encoding="utf-8")
PATCH = (ROOT / ".cache" / "thesis-agent-patch.md").read_text(encoding="utf-8")


def slice_ch4(text: str) -> str:
    start = text.find("## 4.1")
    if start < 0:
        start = text.find("# 4. Findings")
    end = text.find("## 4.2", start + 1)
    if start < 0 or end < 0:
        return text
    return text[start:end]


def markers(text: str) -> dict[str, bool]:
    ch41 = slice_ch4(text)
    return {
        "i15_credit_card_quote": "credit card details to an LLM" in ch41,
        "i15_mcp_reorder_quote": "I add a print file myself" in ch41,
        "i15_transactional_framing": "transactional end state" in ch41,
        "i15_old_compare_only_close": "agentic re-ordering (§4.1.3)" in ch41
        and "credit card" not in ch41,
        "supplier_cross_ref_412": "webshop connector (§4.1.2)" in ch41,
        "supplier_old_abbrev_quote": "Look, you can couple connectors to Claude" in ch41,
        "navigating_internal_conditions": "Navigating internal conditions" in text,
        "reading_guide": "Reading guide" in text,
    }


user_m = markers(USER)
patch_m = markers(PATCH)

lines = ["=== §4.1 markers: USER saved docx ==="]
for k, v in user_m.items():
    lines.append(f"  {k}: {v}")

lines.append("\n=== §4.1 markers: AGENT patch file ===")
for k, v in patch_m.items():
    lines.append(f"  {k}: {v}")

lines.append("\n=== Recommendation ===")
if user_m == patch_m:
    lines.append("IDENTICAL on key markers — no copy needed.")
elif user_m["i15_credit_card_quote"] and user_m["i15_mcp_reorder_quote"]:
    lines.append(
        "USER file already contains I15 purchase + MCP quotes. "
        "Do NOT copy agent patch over main docx."
    )
elif patch_m["i15_credit_card_quote"] and not user_m["i15_credit_card_quote"]:
    lines.append(
        "USER file is MISSING I15 updates. Safe to apply patch_sec412_i15.py "
        "OR copy thesis_i15_patch.docx — but compare §4.1.2 prose for manual edits first."
    )
else:
    lines.append("PARTIAL overlap — manual review required before overwriting.")

out = ROOT / ".cache" / "thesis_compare_i15.txt"
out.write_text("\n".join(lines), encoding="utf-8")
print(out.read_text(encoding="utf-8"))
