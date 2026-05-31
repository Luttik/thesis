"""Diff §4.1.2 between user-saved docx and agent I15 patch."""

from __future__ import annotations

import difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def section_412(text: str) -> list[str]:
    start = text.find("### 4.1.2")
    end = text.find("### 4.1.3", start)
    block = text[start:end] if start >= 0 and end >= 0 else ""
    return block.splitlines()


user = section_412((ROOT / ".cache" / "thesis-user-saved.md").read_text(encoding="utf-8"))
agent = section_412((ROOT / ".cache" / "thesis-agent-patch.md").read_text(encoding="utf-8"))

diff = difflib.unified_diff(user, agent, fromfile="user-saved", tofile="agent-patch", lineterm="")
lines = list(diff)
(ROOT / ".cache" / "sec412_diff.txt").write_text("\n".join(lines[:120]), encoding="utf-8")

user_only = [l for l in lines if l.startswith("+") and not l.startswith("+++") and not l[1:].strip() in {x.strip() for x in agent}]
print(f"Diff lines: {len(lines)}")
print("USER-ONLY highlights (in saved doc, not in agent patch):")
for marker in [
    "Regarding pressure from competitors",
    "the need to be visible",
    "Interviewee 15 articulated what she sees",
]:
    in_user = any(marker.lower() in l.lower() for l in user)
    in_agent = any(marker.lower() in l.lower() for l in agent)
    print(f"  {marker!r}: user={in_user} agent={in_agent}")

print("\nAGENT-ONLY highlights (in patch, not in saved doc):")
for marker in [
    "credit card details to an LLM",
    "I add a print file myself",
    "transactional end state",
    "webshop connector (§4.1.2)",
    "CMO at an e-commerce print company",
]:
    in_user = any(marker.lower() in l.lower() for l in user)
    in_agent = any(marker.lower() in l.lower() for l in agent)
    print(f"  {marker!r}: user={in_user} agent={in_agent}")
