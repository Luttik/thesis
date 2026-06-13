<!--
DRAFT v4: reframed §4.3.5, one integrated story, grounded quote-first, TIGHT.
~520 words (was 762 in v3). NO em-dashes. Further cuts vs v3: dropped Int 1 "invoke
certain things" (thinnest), trimmed the Int 5 / Int 14 / Int 16 quotes to sharpest
fragments, folded the light-end Int 4 cross-ref into the persona sentence, compressed
the closing tie-back to the divergence payoff.

Quotes: ~11 verbatim across 8 interviewees (3,5,6,11,13,14,15,16).
STRANDS: Frame (Int 5 harness) · Reach/tool-calling (Int 13,6; Int 3→§4.3.1) ·
Grounding/context (Int 14,16,11) · Shaping persona+bounds (Int 3,6,14,6) ·
Sourcing build-vs-market (Int 15,5 → ties §4.2.2).
TITLE: "Fitting agents to the organization" (gerund; matches "fit their needs").
-->

### 4.3.5 Fitting agents to the organization

The interviews located the value of an agent not in the model but in the work of fitting it to the organization. Interviewee 5 named it the *harness*: "the big change of agentic AI right now is \[...\] very depending on who finds what they call the harness \[...\] around the AI." The harness is the configuration that makes a general-purpose model specific to one company: its systems, its data, its language, and its limits. Off the shelf an agent knows none of these, and this fitting work, more than the model, separated an agent that transformed a task from one that disappointed.

The first move is giving the agent *reach* into the systems where the work happens, the pattern of tool calling. Interviewee 13 drew the line that makes reach genuinely agentic rather than a one-off lookup: "It would be really agentic if I tell the tool to get something from there, do something with it, and then push it further out." Reach also changes what an agent knows; Interviewee 6 contrasted her customer-service agent with the outsourced staff it replaced: "they are not always as aware as a database \[...\]. They don't have the whole database in their head." Without that connection the agent is effectively blind, which is why an equivalent model failed Interviewee 3 once her data outgrew what her tooling could ingest (Section 4.3.1).

Reach delivers raw access, but the harder move is *grounding* the agent in context the organization can trust. Interviewee 14 placed this at the centre: "everything revolves around \[...\] knowing which data you use and what you can do with it \[...\] so creating the context." The obstacle is that organizational knowledge is rarely clean enough to hand over. Interviewee 16 found that "add to cart" carried "five different definitions" across the business, "a problem if you want to feed it to AI," and only once the definitions were agreed and given "a technical lineage" was it "pretty easy \[...\] to start the LLM wrapper." Interviewee 11 put the cost in a sentence: "building a right context model is superhard."

Participants then shaped how the agent *behaves*, both widening and narrowing it. Widening ranges from self-service configuration, as when Interviewee 3 "created one agent" of her own, to a deliberate persona: Interviewee 6 ran two customer-facing variants, "Power \[...\] a hardcore, diehard power guy" and "Vibe \[...\] way more on the flow and making you feel relaxed." Yet several participants treated constraint as the real source of quality. Interviewee 14 argued that bounding is often what lets a specialized tool beat a general one: once you "put fences around \[it\] and ensure it acts within a certain bandwidth," "a certain tool is all at once better than the generic tools \[...\] like a ChatGPT or a Claude." Interviewee 6 likewise made "a strict cut into what conversations can be agentic and what conversations cannot" to govern risk and cost.

These moves are cumulative, and whether a manager can assemble them in-house depends on the team's technical capacity (Section 4.2.2). Interviewee 15 collapsed a post-acquisition data bottleneck by building the connection herself: "I'm just going to connect it myself to Claude \[...\]. It actually removes the entire bottleneck." Interviewee 5, by contrast, stayed in some domains "pretty dependent on what the market does." An agent's value is configured into it, not shipped with it, which is why the same use case diverges so sharply between organizations: the difference lies less in the technology than in how completely it has been fitted to the organization.
