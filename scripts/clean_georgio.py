import re

INPUT = r"C:\workspace\thesis\transcripts\Thesis transcript Georgio Mosis.md"

with open(INPUT, "r", encoding="utf-8") as f:
    text = f.read()

lines = text.split("\n")

FILLER_WORDS = {
    "yeah", "yep", "mhmm", "okay", "check", "sure", "cool",
    "interesting", "ja", "oké", "sí", "ya", "yes", "no", "nee",
    "ajá", "indeed", "exactly", "great", "así",
}
FILLER_PHRASES = {"el ocho"}

def is_me_filler_only(line):
    stripped = line.strip()
    if not stripped.startswith("Me: "):
        return False
    content = stripped[4:].strip()
    content = re.sub(r"[.,!?;:]+", " ", content).strip()
    if not content:
        return False
    normalized = content.lower()
    for phrase in FILLER_PHRASES:
        normalized = normalized.replace(phrase, " ")
    words = normalized.split()
    words = [w for w in words if w]
    if not words:
        return True
    return all(w in FILLER_WORDS for w in words)

filler_removed = 0
agency_fixes = 0

# Pass 1: Fix "Agency AI" -> "Agentic AI"
new_lines = []
for line in lines:
    if "Agency AI" in line and line.strip().startswith("Me:"):
        fixed = line.replace("Agency AI", "Agentic AI")
        agency_fixes += line.count("Agency AI")
        new_lines.append(fixed)
    else:
        new_lines.append(line)
lines = new_lines

# Pass 2: Remove filler-only Me: lines
# Build a list of blocks separated by blank lines
# Each block is a group of consecutive non-blank lines
# (In this file, each block is typically one line)

# First, identify which lines to remove
lines_to_remove = set()
for i, line in enumerate(lines):
    if is_me_filler_only(line):
        lines_to_remove.add(i)
        filler_removed += 1

# Remove the marked lines
cleaned = []
for i, line in enumerate(lines):
    if i in lines_to_remove:
        continue
    cleaned.append(line)

# Pass 3: Clean up double blank lines
merged = []
for line in cleaned:
    if line.strip() == "" and merged and merged[-1].strip() == "":
        continue
    merged.append(line)

# Pass 4: Merge adjacent Them: lines
# Two Them: lines separated only by a single blank line should be merged
merge_count = 0
final = []
i = 0
while i < len(merged):
    line = merged[i]
    if line.strip().startswith("Them:"):
        # Look ahead: blank line then another Them: line?
        while (i + 2 < len(merged)
               and merged[i + 1].strip() == ""
               and merged[i + 2].strip().startswith("Them:")):
            next_them_content = merged[i + 2].strip()[5:].strip()
            line = line.rstrip() + " " + next_them_content
            merge_count += 1
            i += 2
        final.append(line)
    else:
        final.append(line)
    i += 1

# Strip trailing whitespace from each line
final = [l.rstrip() for l in final]

# Ensure file ends with a single newline
while final and final[-1] == "":
    final.pop()
final.append("")

output = "\n".join(final)

with open(INPUT, "w", encoding="utf-8") as f:
    f.write(output)

print(f"Filler Me: lines removed: {filler_removed}")
print(f"Adjacent Them: lines merged: {merge_count}")
print(f"'Agency AI' -> 'Agentic AI' fixes: {agency_fixes}")
