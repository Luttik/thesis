import re

FILLER_WORDS = {
    "yeah", "yep", "mhmm", "okay", "check", "sure", "cool", "interesting",
    "ja", "oké", "sí", "ya", "yes", "no", "nee", "ajá", "indeed", "exactly",
    "great", "zeker", "duidelijk"
}

def is_filler_only(text):
    content = text.strip()
    if not content.startswith("Me:"):
        return False
    content = content[3:].strip()
    tokens = re.split(r'[.\s,!?]+', content.lower())
    tokens = [t for t in tokens if t]
    return len(tokens) > 0 and all(t in FILLER_WORDS for t in tokens)

filepath = r"C:\workspace\thesis\transcripts\Thesis transcript Jon Stephan.md"
with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

filler_indices = set()
filler_count = 0
for i, line in enumerate(lines):
    if is_filler_only(line):
        filler_indices.add(i)
        filler_count += 1

keep = [True] * len(lines)
for i in filler_indices:
    keep[i] = False
    j = i - 1
    while j >= 0 and lines[j].strip() == "":
        keep[j] = False
        j -= 1
    j = i + 1
    while j < len(lines) and lines[j].strip() == "":
        keep[j] = False
        j += 1

result = [lines[i] for i in range(len(lines)) if keep[i]]

merge_count = 0
merged = []
i = 0
while i < len(result):
    line = result[i]
    stripped = line.strip()
    if stripped.startswith("Them:"):
        current = line
        j = i + 1
        while True:
            k = j
            while k < len(result) and result[k].strip() == "":
                k += 1
            if k < len(result) and result[k].strip().startswith("Them:"):
                them_a = current.rstrip()
                if them_a.endswith("  "):
                    them_a = them_a[:-2]
                them_b_content = result[k].strip()[len("Them:"):].strip()
                current = them_a.rstrip() + " " + them_b_content + "  \n"
                merge_count += 1
                j = k + 1
            else:
                break
        merged.append(current)
        merged.append("\n")
        i = j
        while i < len(result) and result[i].strip() == "":
            i += 1
        continue
    merged.append(line)
    i += 1

text = "".join(merged)
text = re.sub(r'\n{3,}', '\n\n', text)
if not text.endswith("\n"):
    text += "\n"

with open(filepath, "w", encoding="utf-8") as f:
    f.write(text)

print(f"Filler lines removed: {filler_count}")
print(f"Them: merges done: {merge_count}")
