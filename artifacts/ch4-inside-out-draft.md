# Chapter 4 — "inside-out" passage (draft for review)

*Conventions followed: third person / passive; gerund category names in italic; **bold** only for inline Heading-4-style demarcation; interviewee numbering; proprietary/company names redacted in brackets; omissions marked `[...]`.*

---

## EDIT 1 — §4.3.1 intro (foreshadow the variance)

Add one sentence to the end of the existing 4.3.1 introductory paragraph (after "…stood out as an infrequent but relevant use case."):

> Notably, these use cases did not produce uniform results: as Section 4.4 shows, comparable deployments diverged sharply across organizations, tracking the conditions described in Section 4.2 rather than the choice of model.

---

## EDIT 2 — §4.4 opening (replace the two asserted paragraphs with evidenced ones)

*Keep the existing first paragraph (the benefit / sacrifice / risk definitions) unchanged. Replace the current "Notably, even for similar use cases…" paragraph **and** the "This is the chapter's central finding…" paragraph with the following.*

A pattern cuts across these outcomes: comparable use cases did not produce comparable results. The same broad application — an analytics agent, a content pipeline, a customer-facing assistant — was reported as transformative in one organization and as marginal, stalled, or actively counter-productive in another. Because participants drew on the same generation of widely available models, this variance is not well explained by the underlying technology; it tracked instead the organizational conditions described in Section 4.2 and the configuration in which the technology was applied. Table 4 summarizes the contrast for the three most frequently reported use cases.

*(Note: the existing Findings code-table caption was corrected from "Table 2" to "Table 3" to match the in-text references, so this new comparison table is numbered **Table 4**.)*

**Table 4**

*Comparable use cases, divergent outcomes*

| Use case | Where it created value | Where it stalled or fell short | The condition that differed |
|---|---|---|---|
| Self-service analytics | Data sources connected directly to the agent; a reporting request answered in minutes (Interviewees 15, 4) | A capacity-limited tool and a manual upload workaround (Interviewee 3) | Data infrastructure and connectivity (Interviewee 16: a multi-year data-governance track as a precondition) |
| Content and campaigns | Modular, validated, brand-governed pipelines (Interviewees 6, 9, 16) | Outreach that customers "see through" (Interviewee 15) | Validation and brand governance; output worked only where "very standardized" (Interviewee 11) |
| Customer-facing agents | A deployed chatbot driving retention and upsell (Interviewee 6) | Early or experimental deployments; withheld in a regulated sector (Interviewees 2, 15; 7) | A pre-existing baseline, leadership backing, experimentation, and proving commercial value first |

**Analytics.** Self-service analytics was the most common use case, yet the experience of it diverged with the data infrastructure behind it. Interviewee 15 described a near-frictionless setup: "with Claude you just connect those data sources directly to Claude [...] then everyone can really do self-service [...] Because it's just a question and answer and you get insight." Interviewee 4 reported a comparable result after connecting an agent to live data sources, turning reporting that once occupied a "giant analytics team" into a prompt answered "within ten minutes." Interviewee 3, pursuing the identical goal, met the opposite experience: her tool "can only digest so much data [...] if I try to dump anything over, like, 30 [megabytes], it [...] doesn't do it," forcing a manual workaround — "I pull the data from [the warehouse] myself, dump it in, and then have it analyzed" — because the organization's data layer was, in her words, "not there yet." The models were equivalent; the connectivity was not.

**Content generation.** The same divergence appeared within a single organization. Interviewee 11 automated "about thousand web pages fully automated" for one client and judged it a success — "in that use case, it worked. Because it was very standardized." Confronted with creative, brand-led work, the same operator using the same tools reached the opposite verdict: "once you have to have more creativity in the output and also if it needs to be on brand [...] AI still falls very very short." Where other participants sustained content quality, they did so by configuring the work around the model — validation, brand and tone-of-voice governance, and human oversight (Interviewees 6, 9, and 16). Where that scaffolding was absent, the output failed in front of customers; Interviewee 15 recalled an experiment "generating emails from a BDR to customers" in which "the customer sees through that pretty quickly [...] just a bit too much of a shortcut."

Read together, these contrasts point to the chapter's central finding: value creation with agentic AI is an *inside-out* process, shaped more by what an organization does with the technology than by which technology it adopts. Participants located the decisive difference in organizational conditions and managerial behaviour — Interviewee 9's image of an undertaking that succeeds only as "a whole operational model," "like a pie" in which "you have to have all these pieces in order for it to be successful"; Interviewee 13's caution that "GenAI can't solve any of your problems [...] if you [...] dump any [...] AI tool on a company who has no [...] clue about what they want to do [...] then it will fail." Where they could articulate it more precisely, participants located the difference in the configuration — the "harness" around the model (Interviewee 5). The benefit, sacrifice, and risk families detailed below should be read in this light; their cross-cutting implications are taken up in Chapter 5.

---

## EDIT 3 — §5 intro (scope the claim, fix capitalization)

*Replace the existing "similar use cases…" sentence and the one following it.*

Similar use cases — creating a content-generation pipeline, an analytics agent, or customer-service assistance — were reported to produce different outcomes across organizations. That variance was attributable to organizational conditions, managerial behaviour and, where participants could articulate it, the configuration (the "harness") in which the technology was applied, rather than to the underlying model.

---

## EDIT 4 — Appendix D (supporting quotes)

### D.1 Comparable use cases, divergent outcomes

**Analytics — created value (Interviewee 15):**
> But just reviewing our entire data infrastructure [...] you always want to go toward self-service. Yes, but with Claude you just connect those data sources directly to Claude. And then you naturally still have some governance to do, but then everyone can really do self-service with that. Because it's just a question and answer and you get insight.

**Analytics — created value (Interviewee 4):**
> I connected an [agent] to their [analytics and search-console data]. So I have direct access to that data source [...] and I can run cron jobs [...] and have an agent run reports and spit that out. And we got much better reporting [...] that, uh, was not there because you had to download [...] from two different system[s], then in Excel, you had to cross correlate.

**Analytics — friction (Interviewee 3):**
> [The internal AI tool] can only digest so much data. So if I try to dump anything over, like, 30 [megabytes], it doesn't [...] do it. So sometimes I wanna work with [...] larger datasets. So [...] they're working on layering this on top of our data lakes. It's not there yet. So in the meantime [...] I pull the data from [the warehouse] myself, dump it in, and then have it analyzed.

**Analytics — the managerial precondition (Interviewee 16):**
> conversational analytics is [...] definitely a use case that we're working on [...] but [...] I started [...] two years ago with a track on [...] data governance [...] basically describing our business definitions [...] because I believe that we needed that for the enablement of AI on conversational analytics.

**Content — worked, standardized (Interviewee 11):**
> we created content for a recruitment organization [...] everything there was fully automated. So we created [...] about thousand web pages fully automated. [...] in that use case, it worked. Because it was very standardized.

**Content — fell short, creative / brand (Interviewee 11):**
> once you have to have more creativity in the output and also if it needs to be on brand that AI still falls very very short. [...] What we really, really stepped away from is [...] that AI makes something for us without human intervention [...] we thought that was scalable, but it's not scalable.

**Content — backfire (Interviewee 15):**
> There was also an experiment done with generating emails from a BDR to customers. Well, the customer sees through that pretty quickly: nice that you still want to be personal and now you're sending me this, so, just a bit too much of a shortcut with this use case.

**Content — the configuration that held quality (Interviewee 16):**
> what we did is we gathered around all the business owners [...] one, for example, is [...] an add to cart. [...] I would assume that there's one definition of an add to cart [...] We got out five different definitions of that add to cart. So this is a problem if you want to feed it to AI [...] So we cleaned up that part with [...] agreed-on business definitions.

**Customer-facing agents — deployed, commercial (Interviewee 6):**
> we have a chatbot, she's called [Ruby], for our members. And in the chatbot, we've defined a lot of conversations where agentic takes over.
> [On return:] Yeah, I would say 10X. [...] Because it's not two and it's also not 200.
> [On the enabling baseline:] it was always based on conversational AI [...] the conversations were already built [...] And now [...] it's very much improved because it's really like agentic talk.
> [On what made it scale:] it was really because we had commercial success first [...] so now we can roll it out throughout the company to other departments.

**Customer-facing agents — withheld, regulated sector (Interviewee 7):**
> I was in [a major healthcare company], so we used to do a lot of healthcare AI [...] but that is the most [...] regulated side of things [...] you can't just build a chatbot and throw it in healthcare. It needs to go through a lot of scrutiny.

### D.2 Explaining the variance: organization over model

**Interviewee 9 (the operating model):**
> It's like a pie. It's like you have to have all these pieces in order for it to be successful. It can't just be successful because the guy at the top building it built this really cool product. The [...] people have to understand it [...] It has to be governed properly, it has to be priced properly [...] it is a whole operational model that needs to be built around it.

**Interviewee 13 (AI as a multiplier):**
> GenAI can't solve any of your problems. GenAI can scale up the concepts you have in mind, the knowledge you have, the [...] drive that is already there in the company if you use it in the right way. So [...] if you now dump any [...] AI tool on a company who has no [...] clue about what they want to do [...] then it will fail.

**Interviewee 12 (efficiency is not an advantage):**
> it's not a competitive advantage, certainly not in the long term [...] but everybody is gonna get the benefit of efficiency through AI, so it's not really gonna be a way to distinguish yourself from your competitors.

**Interviewee 17 (alignment of conditions):**
> leadership wants us to work with AI. But can employees do that too? Do they do it and do they want to? Those are basically three things. And when those three things align with each other, you get a fantastic AI implementation. But when that's not there [...] it just stops. And nothing happens.

**Interviewee 14 (the 30/70 split):**
> 30% of all AI trajectories is just technology and [...] 60% to 70% is [...] actually us as humans or as an organization and therefore also as an ecosystem.

**Interviewee 10 (same investment, same output):**
> a year later, after spending a million, everyone was still working toward exactly the same goals and producing basically the same output, just with a new system.

**Interviewee 5 (the harness):**
> the big change of agentic AI right now is [...] very depending on who finds what they call the harness [...] who finds the right harness around the AI [...] If there's a [...] party who comes up with a really great [...] wrapper around the [...] product [...] that's gonna determine a lot of what our capabilities are.
