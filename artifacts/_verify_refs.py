import json, urllib.parse, urllib.request

TITLES = [
    "Generative AI in innovation and marketing processes: A roadmap of research opportunities",
    "AI Agents vs. Agentic AI: A Conceptual Taxonomy, Applications and Challenges",
    "The Rise of Agentic AI: Implications, Concerns, and the Path Forward",
    "The role of agentic AI in shaping a smart future: A systematic review",
]

def fetch(title):
    q = urllib.parse.urlencode({"query.bibliographic": title, "rows": 4,
                                "mailto": "support@techonomy.nl"})
    url = "https://api.crossref.org/works?" + q
    req = urllib.request.Request(url, headers={"User-Agent": "thesis-refcheck/1.0 (mailto:support@techonomy.nl)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["message"]["items"]

for t in TITLES:
    print("=" * 90)
    print("QUERY:", t)
    try:
        for it in fetch(t)[:3]:
            auths = "; ".join(
                f"{a.get('family','?')}, {a.get('given','?')}" for a in it.get("author", [])
            ) or "(no authors listed)"
            year = (it.get("issued", {}).get("date-parts", [[None]])[0][0])
            print("-" * 70)
            print("  title :", (it.get("title") or ["?"])[0])
            print("  auth  :", auths)
            print("  year  :", year)
            print("  jrnl  :", (it.get("container-title") or ["?"])[0])
            print("  vol   :", it.get("volume"), "| issue:", it.get("issue"), "| page:", it.get("page"))
            print("  type  :", it.get("type"))
            print("  DOI   :", it.get("DOI"))
    except Exception as e:
        print("  ERROR:", repr(e))
