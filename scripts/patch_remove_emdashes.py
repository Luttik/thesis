# -*- coding: utf-8 -*-
"""
Remove every em dash (—) from the sections we wrote and replace it with a
context-appropriate construction (parentheses, comma, colon, or semicolon).
Clean prose -> clean replace; the two §2 tracked paragraphs -> tracked re-insert;
reference titles -> surgical colon/comma. En dashes (– page ranges) are untouched.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

from patch_sec44_inside_out import find_elem, insert_before, _used_ids
from patch_sec51_discussion import clean_body, ins_body_nocolor

P = Path(r"C:\workspace\thesis\Thesis Draft - Daan Luttik - MBA.docx")

# (anchor, new text)  — clean (non-tracked) prose paragraphs
CLEAN = [
    ("This study advances that agenda in three ways",
     "This study advances that agenda in three ways. First, where prior work could assert "
     "the situated, managerial character of AI value largely in principle, the present "
     "findings give it empirical content: the process model specifies what that managerial "
     "process consists of; observing the environment, steering the organization by "
     "reshaping, leveraging, and navigating its conditions, and applying agentic AI, and so "
     "renders the *translation work* the literature names (Enholm et al., 2022) as a "
     "concrete repertoire of managerial behaviors. Second, it shifts the analytical weight "
     "from the technology to the manager. Influential AI-in-marketing frameworks are "
     "organized around types of AI and their task capabilities (Huang & Rust, 2021), "
     "locating value in what the technology can do; the present account locates it instead "
     "in this managerial work (it is by observing, steering, and applying that managers "
     "drive and mediate value) and treats the agentic system as a resource they configure "
     "rather than as the source of value itself. Third, it widens the conception of "
     "marketing value beyond the efficiency-and-content lens that dominates the "
     "generative-AI literature (Wahid et al., 2023; Grewal et al., 2025; Kumar et al., "
     "2025) to a managed portfolio in which benefits, sacrifices, and risks are produced "
     "together and value destruction is actively governed. The result is one of the first "
     "grounded answers to the field’s call: an account in which marketing managers, "
     "prompted by an external environment they observe rather than by an opportunity they "
     "invent, steer and apply agentic AI to create value."),

    ("The model’s first stage locates value creation before any technology",
     "The model’s first stage locates value creation before any technology is deployed, in "
     "how managers observe a fast-moving environment. Across the data, managers attended to "
     "three external signals: the rapid progression of AI capability (Section 4.1.1), market "
     "pressure from competitors and, increasingly, from consumers acting through their own "
     "agents (Section 4.1.2), and the roadmaps communicated by their software suppliers "
     "(Section 4.1.3). Reading these signals corresponds closely to what the "
     "dynamic-capabilities literature calls *sensing*, the identification of opportunities "
     "and threats in a changing environment (Teece, 1997, 2007). In answering the calls for "
     "research into agentic AI in marketing (Kim, 2025; Mogaji & Jain, 2024), the study’s "
     "first observation is that managers are, on the whole, competent sensors: the arrival "
     "and relevance of agentic AI was widely and similarly perceived."),

    ("The contribution lies in what this reveals about where managerial differentiation",
     "The contribution lies in what this reveals about where managerial differentiation "
     "begins. Because sensing was broadly shared, it was not the scarce capability; what "
     "distinguished managers was a more skeptical, evaluative form of observation. "
     "Participants who created value treated reported use cases as claims to be tested "
     "rather than facts to be adopted, distinguishing what is operationally running from "
     "what is merely announced: the *optics-versus-reality* discipline visible throughout "
     "the data (Section 4.3.1), and a necessary response to a category that one participant "
     "judged to have “become almost a marketing term” (Section 4.1.2). Observing, in this "
     "setting, is thus not only the perception of opportunity but the disciplined separation "
     "of genuine capability from hype, and it is the first point at which the manager’s "
     "judgment, rather than the technology, begins to shape the value that will follow."),

    ("If observing identifies the opportunity, steering is where value",
     "If observing identifies the opportunity, steering is where value is won or lost. "
     "Section 5.1.1 established that the organizational conditions surrounding agentic AI "
     "(literacy, data and infrastructure, leadership, and governance) matter even more than "
     "in earlier waves of digital transformation; the present contribution concerns how "
     "managers act on those conditions. The study identifies a three-part repertoire: "
     "managers *reshape* conditions they control, *leverage* conditions that are already "
     "favorable, and *navigate* conditions they cannot change by working within them. This "
     "gives microfoundational, marketing-specific content to the *seizing* and "
     "*reconfiguring* activities that dynamic-capabilities theory names but tends to treat "
     "at the level of the firm (Teece, 1997, 2007; Hanelt et al., 2021)."),

    ("Two features of how the repertoire is used are analytically central",
     "Two features of how the repertoire is used are analytically central. The first is a "
     "systematic *navigation bias*: managers reshaped conditions internal to their own teams "
     "(educating differentially by level, running experiments, bringing people along, "
     "providing clarity, and championing the work) but defaulted to navigating conditions "
     "that originated elsewhere in the organization, most clearly the restrictive governance "
     "documented in Section 5.1.1 and the scarce technical resources of Section 4.2.3; no "
     "instance of reshaping the governance regime itself was observed. This marks a boundary "
     "to managerial agency that the firm-level literature underplays, and it resonates with "
     "work on resistance to change and AI readiness (Cieslak & Valor, 2025; Li et al., 2023) "
     "and the organizational-capability view of AI adoption (Romeo & Lacko, 2026; Weber et "
     "al., 2023). The second is the disproportionate role of the AI champion, an actor "
     "combining technical and business fluency who converts leadership backing into "
     "organization-wide change (Section 4.2.2) and who is largely absent from the firm-level "
     "account."),

    ("This stage is also where the study departs most sharply",
     "This stage is also where the study departs most sharply from any account that locates "
     "value in the technology, or even its configuration, alone. Value did not follow from "
     "procuring or configuring a capable system; it followed from managerial work that is "
     "easy to underestimate. A well-built system that no one is brought along to use creates "
     "no value, and an initiative that never starts, because it remains caught in legal or "
     "procurement review, forgoes value entirely. This is the substance of the "
     "implementation paradox (Section 4.5.3): agentic tools are unusually easy to begin "
     "with, yet operationalizing them at organizational scale is slow and effortful, a "
     "mismatch one participant captured as technology that changes exponentially meeting "
     "organizations that change logarithmically. The managerial task that steering names is "
     "precisely the closing of that gap: protecting and funding experimentation so that "
     "initiatives actually start, and then doing the unglamorous work of embedding a proven "
     "prototype into routine practice."),

    ("Steering creates the conditions; applying is the act of putting",
     "Steering creates the conditions; applying is the act of putting agentic AI to work, "
     "and the study’s central observation here is that this is a deliberate act of design "
     "rather than a purchase. Managers did not adopt agentic AI as a finished capability; "
     "they assembled it, beginning from a marketing problem rather than from the technology "
     "and building around the agent a *harness* (the data it can reach, its memory, the "
     "tools it can call, its instructions, and its guardrails), together with the "
     "surrounding data infrastructure and system integration on which it depends (Sections "
     "4.3.1 and 4.3.2). The study’s most technically experienced participants treated this "
     "harness, rather than the choice of model, as the real object of design."),

    ("Theoretically, this stage gives empirical specificity to the practice-lens",
     "Theoretically, this stage gives empirical specificity to the practice-lens claim that "
     "a technology’s effects are emergent in its use rather than fixed in the artifact "
     "(Orlikowski, 2000), and it aligns the findings with value co-creation accounts in "
     "which technology actively participates in resource integration rather than serving as "
     "a passive instrument (Vargo & Lusch, 2017; Kaartemo & Helkkula, 2018; Leone et al., "
     "2021). The study’s addition is to specify the configurational elements (the harness "
     "and its technical surround) through which an agentic system becomes a value-creating "
     "actor. This configuration is one component of value creation rather than its sole "
     "determinant: as the preceding stage made clear, the most carefully engineered harness "
     "yields nothing if the organization is not steered to adopt it. Applying and steering "
     "are complementary managerial acts, and value emerges from their combination."),

    ("The model’s final stage concerns the value that results",
     "The model’s final stage concerns the value that results, and the study’s contribution "
     "here is to show that this value is not a single quantity but a portfolio that managers "
     "must actively compose. Participants described benefits (efficiency, scale, extension "
     "of skill, and quality), sacrifices (cost and the displacement or reshaping of roles), "
     "and risks (hallucination, security and privacy violation, and brand degradation) as "
     "produced together rather than traded one for another (Section 4.4). Read through value "
     "theory, these outcomes span the operational, customer, and strategic levels "
     "distinguished in Section 2.3, and they expose a distinction that efficiency-centred "
     "accounts of AI obscure: value *created* for the customer is not the same as value "
     "*captured* by the firm, and an organization can capture cost savings while destroying "
     "customer value through lost trust or authenticity. The manager’s task at this stage "
     "is therefore one of choice and measurement: deciding which value to pursue and "
     "benchmarking AI output against a human baseline so that improvement, rather than mere "
     "novelty, can be demonstrated."),

    ("The clearest evidence that this value is managerially mediated",
     "The clearest evidence that this value is managerially mediated rather than "
     "technologically determined is that comparable use cases produced divergent outcomes "
     "across organizations (Section 4.4.4; Table 4): the same analytics, content, or "
     "customer-facing use case proved transformative in one organization and stalled in "
     "another, and the difference lay in the managerial work and the configuration around "
     "it, not in the technology, which was largely shared. Crucially, this work responds to "
     "an externally sensed impulse rather than an internally generated one: managers do not "
     "invent the opportunity but observe it in the changing environment (Section 5.1.3), and "
     "then steer the organization, reshaping, leveraging, and navigating its conditions, and "
     "apply agentic AI to turn that opportunity into value. It is in this sense, through "
     "these interventions, that the manager rather than the agentic system is the central "
     "actor in value creation."),

    ("The most distinctive finding at this stage concerns how the portfolio",
     "The most distinctive finding at this stage concerns how the portfolio’s negative terms "
     "are contained. Rather than treating value destruction (Doshi & Hauser, 2024) as a side "
     "effect to be avoided, managers managed it recursively, deploying agentic AI to govern "
     "the very risks that agentic AI creates: brand-control and tone-of-voice agents police "
     "brand risk (Section 4.5.1), while evaluator agents and human sense-checking limit the "
     "impact of hallucination (Section 4.5.2). Because human work carries its own error and "
     "bias, the operative standard is *comparative* rather than absolute: the question is "
     "not whether the agent errs but whether it errs less than the process it replaces. This "
     "reframes value destruction in the AI context as a condition that is actively and "
     "increasingly self-governed, and it carries a corollary: the organizations most exposed "
     "to AI-driven value destruction also have the strongest incentive, and the readiest "
     "means, to invest in AI-driven control."),

    ("One outcome, however, resists this containment",
     "One outcome, however, resists this containment and points beyond the firm. Deploying "
     "agentic AI first on junior tasks threatens the pipeline through which juniors become "
     "seniors (Section 4.5.4), and the threat is sharpened by an inversion the data record: "
     "the juniors whose work is most exposed are often the most AI-native, more fluent with "
     "the tools than the senior practitioners who lead, a pattern consistent with evidence "
     "that the productivity gains from generative AI accrue most to less-experienced workers "
     "(Brynjolfsson et al., 2025). Thinning that layer trades a near-term operational gain "
     "for a longer-term erosion of capability that no efficiency metric records. This "
     "tension between operational and strategic value, like the emergence of consumers’ own "
     "agents as a new intermediary, is not resolved within the present data and is taken up "
     "again as a direction for future research in Section 5.3."),

    ("Because value creation with agentic AI is the product of managerial work",
     "Because value creation with agentic AI is the product of managerial work across the "
     "process the model describes (building the conditions, steering the organization, "
     "designing how the technology is applied, and managing the value that results) rather "
     "than of the procurement decision alone, the practical implications of this study "
     "concern how marketing managers do that work. The guidance below follows the stages of "
     "the model developed in Chapter 4; an operational checklist of these implications, "
     "organized by those stages, is provided in Appendix B."),

    ("The most consistent obstacle to value was organizational",
     "The most consistent obstacle to value was organizational rather than technical "
     "(Section 4.2.1): limited AI literacy, resistance to change, and an inability to think "
     "in systems. Managers should therefore treat adoption as a change program rather than a "
     "procurement, which is the practical counterpart to the long-established finding that "
     "the value of a digital technology is realized only through the complementary assets "
     "(skills, structure, leadership, and culture) that surround it (Ancillai et al., 2023; "
     "Enholm et al., 2022; Holmström, 2022). In practice this means investing in the "
     "enabling conditions and leading the change directly: educating in a way that is "
     "differentiated by level; making data and tooling accessible enough for an agent to "
     "act within the organization’s systems (Section 4.2.3); stating clearly where the "
     "organization is going with AI and what success looks like; bringing people along so "
     "that the resistance which otherwise stalls adoption is reduced; and identifying, "
     "empowering, and protecting the AI champions whose visible prototypes attract backing "
     "and scale into organization-wide initiatives (Section 4.2.2). Above all, managers "
     "should create protected, funded space for experimentation (accepting that early "
     "learning does not always produce immediate returns) because tangible value is most "
     "reliably discovered by doing rather than planning, and because senior leaders who "
     "absorb or centralize that cost remove one of the most powerful brakes on adoption."),

    ("The findings imply a strategic choice between two postures",
     "The findings imply a strategic choice between two postures. Much adoption is "
     "essentially AI hygiene (executing proven use cases efficiently to reach parity), and "
     "because competitors will inevitably pursue the same efficiency gains, these are "
     "unlikely to confer durable advantage; indeed, where every firm adopts similar systems "
     "the result can be a homogenization of output that erodes distinctiveness (Doshi & "
     "Hauser, 2024). Pursuing outsized returns instead requires differentiation: finding "
     "novel use cases, experimenting to learn what works, and assembling the skills to "
     "implement them well; this is the strategic, rather than merely operational, register "
     "of value (Section 2.3). The data suggest the default drift runs toward following "
     "rather than differentiating: participants reported abundant efficiency gains (doing "
     "the “faster same”) but comparatively little vision for the “different and better” "
     "applications that genuine differentiation requires (Section 4.1). Neither posture is "
     "inherently wrong, but they demand different investments, and because the pull is "
     "toward parity, managers should choose consciously rather than drift; for a "
     "structurally resistant organization, even disciplined following may be the "
     "value-maximizing option."),

    ("Value was most reliably created when managers began from a marketing",
     "Value was most reliably created when managers began from a marketing problem or "
     "workflow and inserted AI where they trusted its performance, rather than adopting AI "
     "for its own sake (Section 4.3.1); a practical method evident in the data is to "
     "decompose a process into its constituent steps and apply agentic AI only to the steps "
     "where it is reliable, retaining human judgment elsewhere. Because the result depends "
     "on how the agent is embedded, managers should treat the configuration as a real object "
     "of design: the harness around the agent (accessible data, memory, tool access, a clear "
     "system prompt, and guardrails) together with the surrounding data infrastructure and "
     "integration with existing systems (Section 4.3.2). This is the *translation work* "
     "through which a broad technological possibility becomes a bounded, governable use case "
     "(Enholm et al., 2022; Kitsios & Kamariotou, 2021); doing it deliberately lowers risk "
     "and makes the specific contribution of AI measurable."),

    ("Two resourcing decisions recur",
     "Two resourcing decisions recur. First, treat AI budgeting as a strategic act: even in "
     "AI-forward organizations, securing budget remained difficult despite reported returns "
     "as high as a tenfold ROI (Section 4.4.1), and where the upside is large but uncertain "
     "and the time to return is variable, conventional business-case discipline can "
     "systematically under-fund experimentation, which is why centralizing or absorbing the "
     "cost of early work, as some leaders did, both resolves the tension and signals "
     "commitment. Second, manage the build-buy-dependence trade-off: external experts and "
     "agencies offer a fast route around scarce internal capacity and multi-year backlogs "
     "(Section 4.2.1), but externally sourced momentum is fragile and over-reliance can "
     "leave the AI knowledge built for an organization owned by its agency. Because durable "
     "capability rests on internalizing the complementary assets around the technology, "
     "managers should use external help to accelerate while deliberately retaining and "
     "building that capability in-house."),

    ("Finally, managers should look outward",
     "Finally, managers should look outward as well as inward. Several participants "
     "anticipated agents of consumers acting as a new intermediary between seller and buyer, "
     "and began building connectors so that their products remain reachable by such agents "
     "and visible within AI-mediated search (Sections 4.1.2 and 4.3.1), an early, practical "
     "instance of the value co-creation in which technology becomes an active participant in "
     "the exchange between firm and customer (Vargo & Lusch, 2017; Leone et al., 2021). At "
     "the same time, deploying AI first on junior tasks risks eroding the pipeline that "
     "develops juniors into seniors (Section 4.5.4). Managers should weigh short-term "
     "efficiency against the longer-term cost to capability and brand distinctiveness, "
     "neither of which is captured by efficiency metrics alone."),

    ("Several directions for future research follow",
     "Several directions for future research follow. First, and most important, research "
     "should move below the high-level treatment typical of non-technical AI studies to "
     "examine, for a given use case, which specific configuration, implementation, and "
     "resourcing choices most shape the value created, since the present findings suggest "
     "that outcomes are differentiated by context and implementation detail rather than by "
     "the use case itself. Second, longitudinal designs could track initiatives from first "
     "experiment to operational scale, testing where the implementation paradox is overcome "
     "and where it is not. Third, triangulating interview accounts with workflow "
     "documentation, direct observation, or objectively measured performance would test how "
     "far the managerial work identified here actually produces the value it is credited "
     "with. Fourth, the emerging agentic demand side (consumers acting through their own "
     "agents) and its implications for the junior talent pipeline both warrant dedicated "
     "study as they mature, taking up in turn the broader calls for research into agentic AI "
     "in marketing (Kim, 2025; Mogaji & Jain, 2024)."),

    ("Empirically, this study answers recent calls for research",
     "Empirically, this study answers recent calls for research into agentic AI in marketing "
     "(Kim, 2025; Mogaji & Jain, 2024; Jain et al., 2024): it provides one of the first "
     "grounded accounts of how marketing managers create value with agentic AI in practice, "
     "moving beyond the field’s prevailing focus on content generation. Its contribution is "
     "a grounded account of the managerial work through which agentic AI is turned into "
     "value: a process model linking observing, steering, applying, and the management of a "
     "value portfolio, together with the analytical vocabulary (the repertoire of "
     "reshaping, leveraging, and navigating; the harness; and value as a managed portfolio) "
     "through which that work can be understood. The empirical specifics reported here are "
     "snapshots of a fast-moving technology and will date quickly; the higher-order "
     "categories, which describe managerial responses to a moving target rather than the "
     "target itself, should prove more durable. For marketing managers living, as one "
     "participant put it, through both “an era of change” and “a change of era,” the "
     "practical message coincides with the theoretical one: the value of agentic AI will be "
     "determined less by the models they adopt than by the organizations they build around "
     "them."),
]

# (anchor, new text) — the two §2 tracked insertions (re-inserted tracked)
TRACKED = [
    ("Value is also not delivered by a firm to a passive recipient",
     "Value is also not delivered by a firm to a passive recipient but co-created. "
     "Service-dominant logic holds that value emerges through the integration of resources "
     "among actors, with operant resources (knowledge and skills applied to other resources) "
     "as the true source of advantage (Vargo & Lusch, 2017). Within this view, AI is "
     "increasingly understood not as a passive instrument but as an active participant in "
     "value co-creation: Kaartemo and Helkkula’s (2018) review positions AI and robots as "
     "actors in the co-creation process, and Leone et al. (2021) show AI enabling and "
     "enhancing co-creation among providers, customers, and end users in industrial markets. "
     "This perspective grows more relevant as consumers begin to act through their own AI "
     "agents, introducing a new actor into the exchange."),

    ("These managerial roles are given a sharper theoretical foundation",
     "These managerial roles are given a sharper theoretical foundation by the "
     "dynamic-capabilities perspective. Teece et al. (1997) define dynamic capabilities as a "
     "firm’s ability to integrate, build, and reconfigure internal and external competences "
     "in response to a changing environment, and Teece (2007) disaggregates them into the "
     "microfoundations of *sensing* opportunities, *seizing* them, and *transforming* "
     "(reconfiguring) the resource base, coordinated through what he terms *asset "
     "orchestration*. This framework has already been carried into the digital-transformation "
     "field, where Hanelt et al. (2021) describe the more malleable organizational designs "
     "that continuous digital adaptation demands, though it is typically applied at the level "
     "of the firm rather than the individual manager. It offers a useful lens for agentic AI "
     "because it frames value creation as an act of managerial capability: sensing where the "
     "technology applies, seizing the opportunity by building the conditions for it, and "
     "reconfiguring how work is organized around it, all in response to an external "
     "technological shift. Section 5.1 develops this mapping from the empirical data."),
]

# (anchor, old substring, new substring) — reference titles, surgical
REFS = [
    ("Acharya, D. B., Kuppan", "complex goals—A comprehensive survey",
     "complex goals, a comprehensive survey"),
    ("Vaid, S., Puntoni", "all marketers need—Artificial intelligence",
     "all marketers need: Artificial intelligence"),
    ("Weber, M., Engert", "AI implementation—Coping with inscrutability",
     "AI implementation: Coping with inscrutability"),
]


def main():
    shutil.copy(P, P.with_name("Thesis Draft - Daan Luttik - MBA.emdash-backup.docx"))
    doc = Document(str(P)); used = _used_ids(doc)

    for anchor, text in CLEAN:
        el = find_elem(doc, anchor); assert el is not None, anchor
        assert "—" not in text, anchor
        insert_before(el, [clean_body(text)]); el.getparent().remove(el)
    print(f"clean: {len(CLEAN)} paragraphs rewritten")

    for anchor, text in TRACKED:
        el = find_elem(doc, anchor); assert el is not None, anchor
        assert "—" not in text, anchor
        insert_before(el, [ins_body_nocolor(text, used)]); el.getparent().remove(el)
    print(f"tracked: {len(TRACKED)} §2 paragraphs re-inserted")

    for anchor, old_s, new_s in REFS:
        el = find_elem(doc, anchor); assert el is not None, anchor
        hit = False
        for t in el.iter(qn("w:t")):
            if t.text and old_s in t.text:
                t.text = t.text.replace(old_s, new_s); hit = True; break
        assert hit, anchor
    print(f"refs: {len(REFS)} reference titles de-dashed")

    doc.save(str(P))
    print("saved")


if __name__ == "__main__":
    main()
