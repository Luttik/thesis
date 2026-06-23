# LinkedIn Series — "What 17 marketing leaders taught me about agentic AI"

Based on the MBA thesis *How do marketing managers create value with agentic AI?* (Daan Luttik).

**How to run it:** Post 1–2x/week over ~4–5 weeks. Lead with Post 1 (it sets up the series). Each post is copy-paste ready and built around a concrete method, not just a hook. Suggested visuals are noted per post; a single branded template (your photo + one accent color + post number "1/8") makes the series recognizable in-feed.

---

## Post 1 — Audit the organization before the tools

I interviewed 17 marketing leaders and AI experts for my MBA thesis on agentic AI. The clearest finding: the same use case can create real value in one company and stall in another — running on the same models.

Two companies, same goal: let the team query its own analytics through an agent.
- One had its data connected to the agent. Reporting that used to need a whole analytics team came back in ~10 minutes.
- The other hit a 30MB ceiling and went back to manual exports. Its data layer, in the interviewee's words, "wasn't there yet."

Same models. Different plumbing. As I wrote it up: "The models were equivalent. The connectivity was not."

The implication is practical: value comes from the organization around the tool, so that's what to assess first. Before comparing vendors, audit five things:

1. Data — does it exist, and can an agent actually reach it?
2. Integration — are your systems connected, or siloed?
3. Talent — do you have people who can build, integrate, and maintain this, not just prompt it?
4. Direction — is there a clear goal and senior backing, or just enthusiasm?
5. Governance — what will compliance allow, and where can people experiment safely?

Score those honestly and you can usually predict the outcome before you've signed a contract.

Over the next few weeks I'll unpack each — data, talent, governance, the CTO's role, and where the durable advantage actually is.

Which of the five is the real bottleneck in your organization?

#AgenticAI #AIinMarketing #MarketingLeadership #DigitalTransformation

*Visual: the two-company split — "10 minutes" vs "stuck on a 30MB upload" — or the 5-point readiness checklist.*

---

## Post 2 — Turn brand risk into a validation system

A common worry about AI in marketing is brand damage: off-brand copy, wrong tone, content that feels a little too "AI." It's a real risk — one CMO told me plainly, "It's going to say some stupid stuff."

But the most interesting teams I interviewed had turned that risk into a system. The pattern, concretely:

1. Codify the brand. Take your guidelines, tone of voice, and key personas and turn them into an explicit spec an agent can read.
2. Build a validation agent. It doesn't write — it reviews. Every asset is checked against that spec before it ships.
3. Score it. One leader logs a brand-quality score on every piece, AI-generated or not.
4. Benchmark against humans. He scores human-made content the same way — "because otherwise it's just a feeling" — and his early read is that the agent is often more consistent than people.

Two things stand out.

First, the validation layer matters more than the generation layer. Generating content is easy; reliably catching what's off-brand at scale is the hard part — and it's where agentic AI earns its place.

Second, this governance is what lets you scale safely. Without it, one interviewee shipped AI content customers "saw through pretty quickly." With it, others ran modular, brand-checked content pipelines across markets.

The question isn't whether AI touches your brand. It's whether you've built the layer that keeps it on-brand — for people and machines alike.

How would your brand guidelines hold up if you had to hand them to an agent tomorrow?

#AgenticAI #AIinMarketing #BrandSafety #MarTech

*Visual: a content pipeline with a "brand validation agent" gate before publish.*

---

## Post 3 — Marketing leaders, engage the technical decisions

One CMO I interviewed said the most important relationship for her AI ambitions wasn't with an agency — it was with her CTO. "The CMO should be the CTO's best friend," because without his cooperation, her roadmap simply couldn't ship.

As a CTO at a digital marketing agency, I see both sides. Agentic AI runs on foundations most marketing teams don't fully control: accessible data, connected systems, and people who can build and maintain the integrations.

The lesson from my research isn't "marketers should learn to code." It's that marketing leaders need to engage with technical decisions instead of outsourcing them. The leaders creating value were doing four things:

1. Co-owning the data conversation. They knew what data existed, where it lived, and whether an agent could reach it — and pushed for infrastructure when it couldn't.
2. Negotiating resources, not requesting them. Rather than filing tickets, they sat with technology leadership to prioritize the roadmap together.
3. Using external help deliberately. Agencies "give you a kickstart," as one put it — but several warned about dependency: "too many companies make themselves dependent on external workforce" and keep no internal understanding. Retain the knowledge in-house even when you outsource the build.
4. Building the analytical capability. The scarce skill isn't prompting; it's being able to look at a process or a data landscape and see what can realistically be automated.

The old advice was that digital leaders must become business leaders. The mirror is now just as true: marketing leaders must become digital leaders.

If you lead marketing — when did you last sit down with whoever owns your data and actually plan together?

#CMO #CTO #AIinMarketing #MarketingLeadership #DigitalTransformation

*Visual: CMO + CTO planning together; or "request over the wall" vs "negotiate together."*

---

## Post 4 — Efficiency is the entry fee; here's where the edge is

Efficiency was the most common benefit marketing leaders reported in my research — analysis that took a week done in hours, one leader estimating 10x ROI. It's real. But it isn't where the lasting advantage sits.

As one interviewee put it: "It's not a competitive advantage, not in the long term. Everybody is going to get the efficiency benefit from AI."

If everyone gets faster, faster becomes the baseline. Three areas showed up as harder to copy:

1. Skill extension. AI lets people do work outside their usual range — a social media manager producing design and app concepts, a junior delivering senior-level output. Invest here by widening what each role can own, not just speeding up what it already does.
2. Net-new use cases. Not "the old process, faster," but things that were impossible before: thousands of personalized variations, always-on competitor monitoring, customer-facing agents that act. These change what you offer, not just your cost base.
3. Customer experience. Spend the capacity AI frees up on the customer — faster, more relevant, more helpful — rather than pocketing all of it as margin.

Two habits separated the teams pulling ahead:
- They measured the value (time saved, quality, conversion) — not to justify one project, but to unlock budget for the next.
- They chose consciously between parity ("keep up with competitors") and differentiation ("do something they can't"), instead of drifting into efficiency by default.

Efficiency buys your ticket. It doesn't win the race.

Is your AI roadmap mostly "same work, cheaper," or "work we couldn't do before"?

#AIStrategy #AIinMarketing #MarketingLeadership #AgenticAI

*Visual: ladder — "efficiency (everyone)" at the base, "skill extension / new use cases / CX" above.*

---

## Post 5 — You can't automate a process you can't explain

The most practical lesson from my thesis: you can't delegate a process to an agent if you can't explain the process.

Interviewees kept describing "AI failures" that were really process failures. A team wants AI to "understand their marketing data," but they have 20 disconnected sources and no one knows how they fit. Another said it's often clear what the output is, but how people get there is a black box — "so how on earth can you decide what to automate?"

There's a name for this: process debt — the undocumented steps and tacit knowledge AI exposes the moment you try to hand work over. And it's the bigger half of the work: one leader estimated only ~30% of an AI initiative is technology; 60–70% is people and process.

The method that worked, drawn straight from the interviews:

1. Map the workflow into steps. One interviewee: "If work is a stack of workflows, most processes split into six or eight steps."
2. Separate art from science. Decouple the repeatable, rule-able parts (the "science") from judgment, taste, and relationships (the "art").
3. Insert AI only where you trust it. Hand the science to the agent; keep humans on the art and on high-stakes steps.
4. Calibrate oversight to the cost of error. Keep a human in the loop where mistakes are expensive or output is hard to evaluate — and don't over-engineer review for low-stakes tasks.

The uncomfortable part: most teams have never written their real workflow down. Doing that is often the actual AI project — the automation is the easy bit afterward.

Could your team map one core workflow into its real steps this week?

#AgenticAI #MarketingOps #ProcessAutomation #AIinMarketing

*Visual: a 6–8 step workflow with two steps tagged "AI" and the rest "human."*

---

## Post 6 — Build the talent, not just the tooling

One leader described his AI setup as "whole armies of super interns." Another warned: "You no longer develop juniors into seniors — that's a major risk, no new talent pipeline." Both are right, and the gap between them is a leadership problem, not a technology one.

In my research, the teams adopting agentic AI well treated people and skills as the main event. A few concrete practices stood out:

1. Educate by level. One interviewee used a three-tier model:
- Leadership learns where AI is heading, to set strategic direction.
- Middle management learns to facilitate and structure experimentation (this is where most friction sits).
- Employees learn that AI is far more than writing emails.
One generic training for everyone is the common mistake.

2. Bring people along, explicitly. Resistance dropped when leaders made people feel valued through the change — "they need to hear their work matters" — and got concrete: "this is what it is, this is how you use it in your day-to-day." Abstract enthusiasm moves no one.

3. Spread it with peer coaching. Several ran hands-on sessions where colleagues built their own agents, so the skill spread laterally instead of top-down.

4. Find and protect your AI champions. Momentum often came from one person with both technical and business sense. Leadership's job was to back them, fund them, and shield their early experiments from being killed for low short-term returns.

And the pipeline risk deserves a deliberate answer: if AI does the junior work, design new ways for people to grow — or you'll run short of seniors in a few years.

How is your organization growing talent when the bottom rungs of the ladder get automated?

#FutureOfWork #AIinMarketing #Leadership #AgenticAI

*Visual: three-tier pyramid (leadership / middle management / employees) with what each must learn.*

---

## Post 7 — Get ready to be chosen by your customers' agents

Several leaders pointed to the same shift as the most disruptive thing coming for marketing: customers acting through their own AI agents. As one put it, it introduces "a new intermediary between us as seller and the human buyer."

The scenario: a customer tells their assistant "reorder my usual" or "find the best option and buy it," and the agent searches, compares, and transacts — possibly without ever seeing your ad, your homepage, or your funnel.

Most of this isn't at scale yet. But a few interviewees were already making concrete, low-regret moves worth copying:

1. Make your offering machine-readable. One e-commerce CMO built a connector so a customer's AI assistant can browse and reorder directly from her shop. Exposing your catalog and key actions to agents (via connectors and emerging standards like MCP) is becoming the equivalent of having a website.
2. Optimize for AI visibility, not just Google. Interviewees see organic and paid search "becoming less and less relevant" as AI-driven discovery grows. The new question is whether an agent surfaces and recommends you — which depends on structured data, clear product information, and presence in the sources these models draw on.
3. Run small experiments now. The leaders here framed the value as learning, not revenue: "the value is in experimenting and staying ahead of the wave." Cheap pilots now buy understanding before the shift hits at scale.

The strategic question is moving from "how do we reach customers?" to "how do we get chosen by their agents?"

What would it take for an AI agent to confidently recommend and buy your product today?

#AgenticCommerce #AIinMarketing #FutureOfMarketing #AgenticAI

*Visual: human → AI agent → your store, with the connector/MCP link highlighted.*

---

## Post 8 — Build a "laboratory" so compliance stops blocking AI

Compliance used to be treated as an enabler of technology adoption — the guardrails that let you move. With agentic AI, the leaders I interviewed described it more often as the main brake.

One captured the absurdity: in many large companies it's fine to buy an unknown tool and feed it your data, "but agentic AI? Completely out of the question." The fallout was consistent: enthusiastic people get blocked and disengage, "bring your own AI" gets banned overnight, and usage goes underground as shadow IT.

What separated the teams that kept moving wasn't looser rules — it was a deliberate structure:

1. Build a "laboratory." A sanctioned space, agreed with legal and IT, where teams experiment with agentic AI under clear constraints — synthetic or non-sensitive data, defined boundaries, no production customer data. As one interviewee framed it: keep "the factory where the trains run on time," and add "the laboratory where you're allowed to experiment, fail, and break things."
2. Negotiate it, don't accept the wall. Most marketing teams treat compliance as fixed. The ones creating value sat down with legal and IT to design a compliant path to experiment — turning a blanket "no" into a bounded "yes, here."
3. Use shadow IT as evidence. Where people were already quietly using tools, leaders treated it as a "lighthouse project" — proof of demand to bring into the open and formalize, rather than just shut down.
4. Fund the experiments centrally. Early AI work "doesn't always provide immediate returns," so absorb or centralize the cost — don't penalize a team for low-return learning, or the learning stops.

—

That wraps this series on what I learned from 17 interviews for my MBA thesis. The through-line: with agentic AI, the technology is rarely the bottleneck — the organization around it is. The good news is that organizational conditions are things you can deliberately shape.

I pulled the practical guidance into a one-page manager's checklist. If that's useful, say so in the comments and I'll share it.

What's the one organizational change that would unlock AI for your team?

#AgenticAI #AIGovernance #DigitalTransformation #MarketingLeadership

*Visual: "factory" vs "laboratory" split panel.*

---

### Reusable bio line (for the comments or your About section)
"I'm a CTO at a digital marketing agency. I recently finished an MBA thesis on how marketing leaders create value with agentic AI — based on 17 interviews with marketing managers and AI experts."

### Optional extras
- **Carousel version** of any post (especially 1, 5, 7) for higher reach.
- **Dutch translations** of the strongest 2–3 for a local audience.
- A **lead-magnet post** built around the Appendix B checklist (gated by "comment + I'll DM it").
