# -*- coding: utf-8 -*-
"""
Clean (non-tracked) revision of §5.2 (practical implications), §5.3 (future
research cluster), and §6 (conclusion):
  - reframe off the "inside-out / configuration determines value" claim toward
    the manager-across-the-process spine;
  - weave a Chapter 2 theoretical anchor into each practical implication;
  - pull future research into a signposted cluster of four directions;
  - recast the conclusion's headline + contribution around the process model.
Reuses the clean builders from patch_sec51_discussion.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from docx import Document

from patch_sec44_inside_out import find_elem, insert_before
from patch_sec51_discussion import clean_body

ROOT      = Path(__file__).resolve().parents[1]
DOCX_PATH = ROOT / "Thesis Draft - Daan Luttik - MBA.docx"
BACKUP    = ROOT / "Thesis Draft - Daan Luttik - MBA.sec5236-backup.docx"

# (anchor substring, [new paragraph strings])  -- one or more replacement paras
REPLACEMENTS = [
    # ---------------- §5.2 intro ----------------
    ("the practical implications of this study concern", [
        "Because value creation with agentic AI is the product of managerial work across "
        "the process the model describes — building the conditions, steering the "
        "organization, designing how the technology is applied, and managing the value that "
        "results — rather than of the procurement decision alone, the practical "
        "implications of this study concern how marketing managers do that work. The "
        "guidance below follows the stages of the model developed in Chapter 4; an "
        "operational checklist of these implications, organized by those stages, is provided "
        "in Appendix B."
    ]),
    # ---------------- §5.2.1 ----------------
    ("The most consistent obstacle to value was organizational", [
        "The most consistent obstacle to value was organizational rather than technical "
        "(Section 4.2.1): limited AI literacy, resistance to change, and an inability to "
        "think in systems. Managers should therefore treat adoption as a change program "
        "rather than a procurement, which is the practical counterpart to the long-"
        "established finding that the value of a digital technology is realized only through "
        "the complementary assets — skills, structure, leadership, and culture — "
        "that surround it (Ancillai et al., 2023; Enholm et al., 2022; Holmström, 2022). In "
        "practice this means investing in the enabling conditions and leading the change "
        "directly: educating in a way that is differentiated by level; making data and "
        "tooling accessible enough for an agent to act within the organization’s "
        "systems (Section 4.2.3); stating clearly where the organization is going with AI "
        "and what success looks like; bringing people along so that the resistance which "
        "otherwise stalls adoption is reduced; and identifying, empowering, and protecting "
        "the AI champions whose visible prototypes attract backing and scale into "
        "organization-wide initiatives (Section 4.2.2). Above all, managers should create "
        "protected, funded space for experimentation — accepting that early learning "
        "does not always produce immediate returns — because tangible value is most "
        "reliably discovered by doing rather than planning, and because senior leaders who "
        "absorb or centralize that cost remove one of the most powerful brakes on adoption."
    ]),
    # ---------------- §5.2.2 ----------------
    ("The findings imply a strategic choice between two postures", [
        "The findings imply a strategic choice between two postures. Much adoption is "
        "essentially AI hygiene — executing proven use cases efficiently to reach "
        "parity — and because competitors will inevitably pursue the same efficiency "
        "gains, these are unlikely to confer durable advantage; indeed, where every firm "
        "adopts similar systems the result can be a homogenization of output that erodes "
        "distinctiveness (Doshi & Hauser, 2024). Pursuing outsized returns instead requires "
        "differentiation: finding novel use cases, experimenting to learn what works, and "
        "assembling the skills to implement them well — the strategic, rather than "
        "merely operational, register of value (Section 2.4). Neither posture is inherently "
        "wrong, but they demand different investments, and managers should choose "
        "consciously rather than drift; for a structurally resistant organization, even "
        "disciplined following may be the value-maximizing option."
    ]),
    # ---------------- §5.2.3 ----------------
    ("Value was most reliably created when managers began from a marketing", [
        "Value was most reliably created when managers began from a marketing problem or "
        "workflow and inserted AI where they trusted its performance, rather than adopting "
        "AI for its own sake (Section 4.3.1); a practical method evident in the data is to "
        "decompose a process into its constituent steps and apply agentic AI only to the "
        "steps where it is reliable, retaining human judgment elsewhere. Because the result "
        "then depends on how the agent is embedded, managers should treat the configuration "
        "as a real object of design — the harness around the agent (accessible data, "
        "memory, tool access, a clear system prompt, and guardrails) together with the "
        "surrounding data infrastructure and integration with existing systems (Section "
        "4.3.2). This is the translation work through which a broad technological "
        "possibility becomes a bounded, governable use case (Enholm et al., 2022; Kitsios & "
        "Kamariotou, 2021); doing it deliberately lowers risk and makes the specific "
        "contribution of AI measurable."
    ]),
    # ---------------- §5.2.4 ----------------
    ("The same configuration logic offers the most effective response", [
        "The same design logic offers the most effective response to the risks of agentic "
        "AI: deploy AI to govern AI. Brand-control and tone-of-voice agents can enforce "
        "standards at scale, evaluator agents and human sense-checking can contain "
        "hallucination, and benchmarking AI output against a human baseline converts risk "
        "management into a measurable quality process (Sections 4.4.3 and 4.5). Because the "
        "harms of agentic AI are a form of value destruction to be actively managed rather "
        "than merely avoided (Doshi & Hauser, 2024), oversight should be calibrated to the "
        "cost of error and the difficulty of evaluating the output, rather than directed at "
        "eliminating error altogether."
    ]),
    # ---------------- §5.2.5 ----------------
    ("Two resourcing decisions recur", [
        "Two resourcing decisions recur. First, treat AI budgeting as a strategic act: even "
        "in AI-forward organizations, securing budget remained difficult despite reported "
        "returns as high as a tenfold ROI (Section 4.4.1), and where the upside is large but "
        "uncertain and the time to return is variable, conventional business-case discipline "
        "can systematically under-fund experimentation — which is why centralizing or "
        "absorbing the cost of early work, as some leaders did, both resolves the tension "
        "and signals commitment. Second, manage the build-buy-dependence trade-off: external "
        "experts and agencies offer a fast route around scarce internal capacity and multi-"
        "year backlogs (Section 4.2.1), but externally sourced momentum is fragile and over-"
        "reliance can leave the AI knowledge built for an organization owned by its agency. "
        "Because durable capability rests on internalizing the complementary assets around "
        "the technology, managers should use external help to accelerate while deliberately "
        "retaining and building that capability in-house."
    ]),
    # ---------------- §5.2.6 ----------------
    ("Finally, managers should look outward", [
        "Finally, managers should look outward as well as inward. Several participants "
        "anticipated agents of consumers acting as a new intermediary between seller and "
        "buyer, and began building connectors so that their products remain reachable by "
        "such agents and visible within AI-mediated search (Sections 4.1.2 and 4.3.1) — "
        "an early, practical instance of the value co-creation in which technology becomes "
        "an active participant in the exchange between firm and customer (Vargo & Lusch, "
        "2017; Leone et al., 2021). At the same time, deploying AI first on junior tasks "
        "risks eroding the pipeline that develops juniors into seniors (Section 4.5.4). "
        "Managers should weigh short-term efficiency against the longer-term cost to "
        "capability and brand distinctiveness, neither of which is captured by efficiency "
        "metrics alone."
    ]),
    # ---------------- §5.3: split last paragraph into limitation + future research ----------
    ("The study relies exclusively on interview data", [
        "Finally, the study relies exclusively on interview data. No documentary analysis of "
        "actual AI deployments, no observation of workflows in practice, and no performance "
        "audit was conducted. This is consistent with the constructivist grounded theory "
        "design and with the early, exploratory stage of the phenomenon: organizations are "
        "themselves still assembling the evidence base, and independent performance data is "
        "rarely available. It means, however, that the study cannot adjudicate between "
        "participants who report high returns and those who report difficulty; both accounts "
        "are taken at face value.",

        "Several directions for future research follow. First, and most important, research "
        "should move below the high-level treatment typical of non-technical AI studies to "
        "examine, for a given use case, which specific configuration, implementation, and "
        "resourcing choices most shape the value created, since the present findings suggest "
        "that outcomes are differentiated by context and implementation detail rather than "
        "by the use case itself. Second, longitudinal designs could track initiatives from "
        "first experiment to operational scale, testing where the implementation paradox is "
        "overcome and where it is not. Third, triangulating interview accounts with workflow "
        "documentation, direct observation, or objectively measured performance would test "
        "how far the managerial work identified here actually produces the value it is "
        "credited with. Fourth, the emerging agentic demand side — consumers acting "
        "through their own agents — and its implications for the junior talent pipeline "
        "both warrant dedicated study as they mature, taking up in turn the broader calls "
        "for research into agentic AI in marketing (Kim, 2025; Mogaji & Jain, 2024)."
    ]),
    # ---------------- §6 headline ----------------
    ("This thesis asked how marketing managers create value with agentic AI", [
        "This thesis asked how marketing managers create value with agentic AI. Drawing on "
        "seventeen interviews with marketing managers and AI experts, analyzed through "
        "constructivist grounded theory, it concludes that value is created not by adopting "
        "agentic AI but by the managerial work that surrounds it: observing a volatile "
        "environment, building the conditions for change, steering the organization, "
        "designing how the technology is applied, and managing the portfolio of value that "
        "results. The study’s central contribution is a process model of this work "
        "(Figure 1); the technology is necessary but, on its own, far from sufficient."
    ]),
    # ---------------- §6 contribution close ----------------
    ("Empirically, this study answers recent calls for research", [
        "Empirically, this study answers recent calls for research into agentic AI in "
        "marketing (Kim, 2025; Mogaji & Jain, 2024; Jain & Eastman, 2024): it provides one "
        "of the first grounded accounts of how marketing managers create value with agentic "
        "AI in practice, moving beyond the field’s prevailing focus on content "
        "generation. Its contribution is a grounded account of the managerial work through "
        "which agentic AI is turned into value — a process model linking observing, "
        "steering, applying, and the management of a value portfolio, together with the "
        "analytical vocabulary (the repertoire of reshaping, leveraging, and navigating; the "
        "harness; and value as a managed portfolio) through which that work can be "
        "understood. The empirical specifics reported here are snapshots of a fast-moving "
        "technology and will date quickly; the higher-order categories, which describe "
        "managerial responses to a moving target rather than the target itself, should prove "
        "more durable. For marketing managers living, as one participant put it, through "
        "both “an era of change” and “a change of era,” the practical message "
        "coincides with the theoretical one: the value of agentic AI will be determined less "
        "by the models they adopt than by the organizations they build around them."
    ]),
]


def main():
    shutil.copy(DOCX_PATH, BACKUP)
    doc = Document(str(DOCX_PATH))

    for anchor, new_texts in REPLACEMENTS:
        el = find_elem(doc, anchor)
        assert el is not None, f"anchor not found: {anchor!r}"
        insert_before(el, [clean_body(t) for t in new_texts])
        el.getparent().remove(el)
        print(f"ok ({len(new_texts)}): {anchor[:60]}")

    doc.save(str(DOCX_PATH))
    print(f"\nSaved: {DOCX_PATH}\nBackup: {BACKUP}")


if __name__ == "__main__":
    main()
