# Transcript Coding: Georgio Mosis

**Interview Date:** Feb 17  
**Participant Role:** Associate Partner, consulting firm (pensions, asset management, digital transformation)  
**Organization:** Consulting firm (primarily pension funds, asset management, risk management, digital transformation)  
**Interview Duration:** ~45 minutes  

---

## Participant Profile

Georgio Mosis is an associate partner at a consulting firm that advises organizations in pensions, asset management, and digital transformation. He is also a scientist: a clinical epidemiologist and medical informatician. He previously served as principal scientist at Philips Healthcare, working in Boston and China on healthcare AI, IoT, and digital society topics. He teaches at Nyenrode and the University of Amsterdam. He has a pending patent on agents (with Wageningen University / GrowNext for controlled agriculture). He has been in the AI field since 1997 (Deep Blue vs. Kasparov). He is based in the Netherlands. His perspective combines deep technical AI expertise with practical consulting experience in highly regulated industries (healthcare, finance).

---

## 1. AI Applications & Use Cases

### 1.1 Recruitment Agent (Full Pipeline)
**Code:** `AI-APPLICATION:RECRUITMENT-AGENT`

A fully agentic recruitment pipeline: takes a job description, transforms it into a LinkedIn-ready posting, posts it, collects engagement/applicant data, pre-matches candidates, and ranks them for human interview. Reduced time-to-hire KPI. The agent does not make final hiring decisions — it ranks.

> "They wanted to automate their recruitment process. So basically a agent that you made it totally agentic. The only thing they had to do was give a job description and then we had an agent that could turn that into a job description that would fit on LinkedIn, and they even posted it. And they even collect the data of who watched it, who was interesting, etcetera. [...] They would also do the pre matching and give an idea of who might be the best in to interview first." (line 75)

### 1.2 Market Research Agent (PROBE)
**Code:** `AI-APPLICATION:MARKET-RESEARCH-AGENT`

A multi-agent system for continuous market intelligence with five specialized agents: Plan (define scope), Research (find and pull competitor data), Organize (segment by geography/category), Evaluate (determine competitive segment), Build (create dashboard). Produces a live competitive intelligence dashboard.

> "We call it probe. [...] You plan. You do the research. You organize. [...] And then we evaluate. [...] And then the last part of it is built. You build the report or the dashboard to show us every day what's the competitive situation look like. [...] These are multi agent networks. Right? So we have a purpose agent, a research agent, an organizing agent, an evaluation agent, and a build agent." (line 95)

### 1.3 Campaign Agent (Human-AI Interaction)
**Code:** `AI-APPLICATION:CAMPAIGN-AGENT`

An event campaign workflow for a "Knowledge Festival": CRM evaluation agent checks if contact data is still current (job changes, etc.), email blasting, and then a human-AI handoff for follow-up when attendees have questions or need workshop assignments.

> "We also agentize that by we look at our own CRM system [...] who came last year, who didn't come, who changed their jobs, all these things. Like, is the CRM system still up to date? That is what we call a eval agent. [...] When people respond, there is a human AI interaction because we cannot agentize everything. So a human really looks at who responded. And if there are questions, then we put it the next agent to do the follow-up." (line 95)

### 1.4 Voice Agents (Inquisitive)
**Code:** `AI-APPLICATION:VOICE-AGENTS`

Voice agents with text-to-speech/speech-to-text capabilities, connected to an agentic knowledge base. Designed as inquisitive agents that ask questions rather than provide information — reduces error risk. Can proactively call people for follow-up.

> "Voice agents. [...] There is a text to speech, speech to text, then we have that agentic knowledge base, so the know how, know what, nowhere, know why. You plug it in there, everything that has to do with pension. These agents know. You just call him, and he will talk to you." (line 97)

> "They are inquisitive, so they ask questions. And make less mistakes. [...] Just inquisitive agents, not talking agents who give info." (lines 101–105)

### 1.5 Controlled Agriculture Agent (Non-Marketing, Illustrative)
**Code:** `AI-APPLICATION:AGRICULTURE-AGENT`

A pending-patent agent system (with Wageningen University / GrowNext) for controlled environment agriculture. Agents learn optimal growth paths for every seed type and autonomously control sensors (water, light wavelengths, wind) to optimize plant growth. Can replan when conditions change — like a navigation system recalculating a route.

> "Create an agent that learned the optimal growth path for every seat that these people grow. [...] The AI control room will make sure that the plant grows [...] It's almost like a navigating system." (line 77)

Not directly marketing, but illustrative of Georgio's definition of sophisticated agentic AI with planning, acting, and replanning capabilities.

---

## 2. Benefits

### 2.1 Top Line Growth
**Code:** `BENEFIT:TOP-LINE-GROWTH`

AI should demonstrably increase revenue — selling more of what you're selling. This is the strongest business case for AI investment.

> "One is top line growth. We need to sell more of what we're selling, then you have a business case. So if the AI help us to sell more tickets to the Kellis Festival, great." (line 113)

### 2.2 Bottom Line Efficiency
**Code:** `BENEFIT:BOTTOM-LINE-EFFICIENCY`

Doing the same things with fewer resources. Georgio is candid that the strongest AI business case is headcount reduction, even though it's uncomfortable to say.

> "Efficiency is about people losing their jobs. And that's the best use case you can make with AI. [...] We're doing the same thing, but with less cost, less time, higher quality." (lines 151, 117)

### 2.3 Quality of Outcome
**Code:** `BENEFIT:QUALITY`

In healthcare especially, AI improves the quality of service/outcome rather than just speed or cost. Doctors spend less time on computers and more on patient interaction. Diagnostic accuracy improves.

> "In health care, for example, it's not about being faster. [...] It's just that the quality of the diagnostic should be better. [...] The doctor spend less time on the computer, and he can put hand on grandma's shoulder." (line 129)

Quality is measured differently by industry: patient satisfaction in healthcare, call answer rates in insurance, and so on.

### 2.4 ROI-First Approach
**Code:** `BENEFIT:ROI-DRIVEN`

Every AI initiative must have a clear business case for the CFO. Without ROI, projects are "short pilot, you fly, you crash, and then move to the next." Three value buckets: top line growth, bottom line efficiency, vanity metrics (which rarely fly with the CFO).

> "Every investment needs to show a ROI [...] AI is also very expensive. That's something that we don't take into consideration. It's not cheap." (lines 111, 149)

---

## 3. Drawbacks & Risks

### 3.1 Job Displacement (Direct Experience)
**Code:** `RISK:JOB-DISPLACEMENT`

Georgio has direct experience: an RPA implementation in Malaysia resulted in firing half the staff. He describes not sleeping for a week. This is the most visceral account of job loss across all interviews.

> "What happened is we fired half of the people. Right? That's terrible. I I didn't sleep for a week." (line 159)

### 3.2 Fallback Scenario Risk
**Code:** `RISK:NO-FALLBACK`

After firing people, a power outage forced the organization back to analog processes — with nobody left to do them. Companies rarely plan for what happens when AI systems go down.

> "They had a power outage So you have to fall back to the old way of doing things, the analog way. That's a problem. So if you totally agentize your stuff fire all the people, you gotta have a fallback scenario. Companies usually don't think about that." (line 159)

### 3.3 Skills Deprivation
**Code:** `RISK:SKILLS-DEPRIVATION`

Professionals are losing skills they no longer practice. Like not remembering phone numbers, professionals are losing domain skills as AI handles their tasks. This is a systemic, long-term erosion.

> "Skills deprivation [...] We used to remember a lot of stuff now, I'm sure you don't remember any phone numbers. Right? So your skill in that is just deprecated and deprecating. That's something that is happening across the board with professional." (line 159)

### 3.4 Junior Jobs Disappearing
**Code:** `RISK:JUNIOR-PIPELINE`

"Agents are the new interns." Junior roles are disappearing, threatening the pipeline of future senior professionals. Georgio deliberately pushes for hiring young people in his organization to counter this.

> "The jobs for young people are disappearing. And it becomes more of a scene with highly skilled professionals with AI they don't need any juniors to help them anymore. Agents are the new interns." (line 159)

### 3.5 AI Credibility Loss / Stigma
**Code:** `RISK:AI-STIGMA`

Using AI can damage professional credibility. Colleagues may dismiss AI-assisted work ("that's AI generated"), similar to doping accusations in sports. Especially prevalent in academia.

> "If you're an academic, and you say you write your paper with AI, people will looking at you like, oh my god. What kind of academic are you? [...] There is a shame that comes with oh, you used AI. And it's almost like, yeah, you're using doping in a realtor." (line 199)

### 3.6 Unrealistic Expectations
**Code:** `RISK:UNREALISTIC-EXPECTATIONS`

Organizations set expectations so high that AI can only disappoint. The gap between the market promise ("AI will solve cancer") and realistic outcomes creates disillusionment.

> "You put so high expectation on the AI that it could only fail." (line 197)

---

## 4. Organizational Enablers

### 4.1 Board Champion
**Code:** `ENABLER:BOARD-CHAMPION`

Having a champion at the board level (not just CTO, but a board-level decision) is the most important tailwind. Without it, initiatives stall.

> "You see Tailwind in adoption and transformation where there is a champion in the board. That really pushes for AI. Typically, it's not only the CTO, but it's a board decision." (line 175)

### 4.2 Paid AI Infrastructure
**Code:** `ENABLER:PAID-TOOLS`

Companies that only provide free-tier AI tools handicap their employees. Paid tools provide a year's advantage over free versions.

> "Not all companies give their employees paid version of AI tools. [...] If you work with a paid version of a AI tool that's like you move one year ahead of those who." (line 175)

### 4.3 Training and Education
**Code:** `ENABLER:TRAINING`

Proper training on prompting and AI usage is essential. Autodidactic use (treating AI like Google) produces inferior results.

> "Training and education. Sometimes people wanna do it, They really are engaged, but they don't know how. [...] Prompting is is really different than just asking using it like a Google." (line 175)

### 4.4 Culture of Innovation
**Code:** `ENABLER:INNOVATION-CULTURE`

The most important enabler is culture, characterized along two axes: speed (fast vs. slow) and approach (planned vs. experimental). The optimal culture is fast and experimental, celebrating failure as learning.

> "Culture. A culture of innovation culture, forgiving. Like, when you pioneer, you break things fast [...] And when you break, we'll pay for the damage." (line 175)

> "Speed [...] On the other axis, I would put planned or experimental." (line 183)

### 4.5 Quick Wins with Impact
**Code:** `ENABLER:QUICK-WINS`

Start with simple, high-impact use cases that build confidence. Don't begin with the most complex international multi-language campaign. Celebrate even small successes.

> "Quick wins gives a lot of confidence. Even if it's a campaign on, on LinkedIn [...] And if you fail, you celebrate failure." (line 175)

### 4.6 High-Impact Use Cases
**Code:** `ENABLER:HIGH-IMPACT-CASES`

Invest in projects where the outcome matters to stakeholders. Low-impact demos produce indifference, not adoption.

> "Having good use cases where the impact matters. You don't wanna spend a lot of time doing a project, and you present it, and anybody's okay. Yeah. Right." (line 185)

---

## 5. Organizational Obstacles

### 5.1 Board-Level Fear and Restrictive Policies
**Code:** `OBSTACLE:BOARD-FEAR`

Boards create blanket AI prohibition policies driven by fear of hacks, data sovereignty concerns, and geopolitical anxiety (e.g., "what if Trump shuts down American cloud").

> "The board. Then you'll have a bunch of people that will come up with blight, some sort of a policy. We have a policy here that we forbid AI. [...] The fear of even touching anything." (line 195)

### 5.2 Punishing Failure
**Code:** `OBSTACLE:PUNISHING-FAILURE`

Making an example of the first person whose AI pilot fails destroys innovation culture. It breaks the spirit of young people who want to experiment.

> "If there is a problem you highlighted, and you break the spirit of all the young people who wanna do cool stuff. The first mistake of, okay, Dan. You wanna do AI? Go and do AI. [...] If you fail, oh my goodness. And they'll make an example out of you." (line 195)

### 5.3 Unrealistic Expectations (as Obstacle)
**Code:** `OBSTACLE:EXPECTATION-MANAGEMENT`

Expectations set so high that AI can only disappoint. Organizations expect AI to "solve all our problems" rather than solve specific, bounded problems.

> "You put so high expectation on the AI that it could only fail." (line 197)

### 5.4 Wrong Infrastructure
**Code:** `OBSTACLE:INFRASTRUCTURE`

Working on outdated hardware and without proper cloud infrastructure prevents getting the best results from AI.

> "Not having the right infrastructure, working on a bunch of old PCs, with Pentium one, And then the you'll now get the best out of the AI." (line 197)

### 5.5 Generational / Cultural Clash
**Code:** `OBSTACLE:GENERATIONAL-CLASH`

A knowledge pyramid inversion: young people enter with AI skills, but power sits with senior people who distrust the technology. Senior professionals cite security, privacy, and prompt injection risks to block young people's initiatives. This creates a cultural clash that prevents AI from moving from pilot to production.

> "Young people thrive in young AI native companies, not in the old school ones where you need to change the way of the old people. [...] The young people come with a lot of skills and knowledge, and the more you move up, the less they know about AI. And you can imagine that tension is very difficult." (line 165)

### 5.6 AI Credibility Gap
**Code:** `OBSTACLE:CREDIBILITY-GAP`

People who are highly efficient with AI face resentment from those who are not. The gap between "flyers" and non-users widens over time, creating two diverging worlds within the same organization.

> "Those who are really flying with AI [...] While they're seeing AI as a separate thing. Like, the AI did it. I didn't do it. [...] The two worlds are moving away from each other slowly and slowly." (line 203)

---

## 6. Conceptual Codes

### 6.1 Intelligence as Multifaceted
**Code:** `CONCEPT:MULTIFACETED-INTELLIGENCE`

Georgio frames AI through the lens of multiple intelligences: linguistic, logical-mathematical, spatial, interpersonal, intrapersonal. Generative AI maps to linguistic intelligence (NLP). This framing helps non-technical audiences understand what AI can and cannot do.

> "Intelligence is not one thing. It's a multifacet thing. You have linguistic intelligence [...] logical, mathematical intelligence [...] spatial intelligence [...] interpersonal intelligence [...] intrapersonal intelligent." (line 37)

### 6.2 Agent as Know-Everything Entity
**Code:** `CONCEPT:AGENT-KNOWLEDGE-STRUCTURE`

An agent is defined by six knowledge dimensions: know how, know what, know where, know why, know when, know who. This makes prompting fundamentally different from chatbot interactions.

> "An agent has know how, know what, no where, no why, no when, and no who. That's what the agentic AI does is to me." (line 57)

### 6.3 Memory Structure as Key Differentiator
**Code:** `CONCEPT:AGENT-MEMORY`

Good agents require memory: long-term, short-term, and working memory. Without memory, an agent doesn't become intelligent over time.

> "They also have a memory structure. [...] You have a long term memory. [...] Short term memory, but also working memory. And, yeah, not all so called agents have that." (line 59)

### 6.4 ROI as Gatekeeper
**Code:** `CONCEPT:ROI-GATEKEEPER`

In the corporate world, AI initiatives live or die by ROI. The CFO is the ultimate gatekeeper. Three value categories exist (top line, bottom line, vanity), and only the first two survive boardroom scrutiny.

> "The chief marketing needs to say, why are we creating all this stuff? Because it costs money. [...] Our CFO call it vanity metrics. Beauty stuff, makeup. Yeah. We don't pay for makeup." (line 111)

### 6.5 Era of Change / Change of Era
**Code:** `CONCEPT:DUAL-CHANGE`

Quoting the Pope: "We're living in an era of change and a change of era simultaneously." This captures the tension between incremental adoption (change within the era) and fundamental disruption (a new era entirely).

> "We're living in an error of change and we're living in a change of error. Simultaneously." (line 167)

### 6.6 Dark Patterns and Persuasive Technology
**Code:** `CONCEPT:DARK-PATTERNS`

Post-formal-interview discussion: AI-powered apps optimize for engagement through persuasive messaging, leading to addiction. Chatbots always end with a question to keep users talking. Regulators haven't caught up.

> "Persuasive messaging that is also in these chatbots. [...] They optimize the [...] things like oh, it's so persuasive." (line 241)

---

## 7. Agentic vs. Chatbot Distinction

**Code:** `CONCEPT:AGENTIC-VS-CHATBOT`

Georgio draws a clear line: a chatbot reflexively answers questions ("What is the capital of France?"). An agent has knowledge dimensions (know how/what/where/why/when/who), can plan, act, and has memory. The agent can handle complex, multi-step instructions.

> "If you can ask an agent to say, I want you to look at Don's, master thesis and I want you to look at the business model of the project that he's doing and break that down into the value proposition [...] They just can do that because they have a know how, nowhere, know what, know how." (line 57)

He also adds memory structure as a critical differentiator that is often missing from so-called agents.

---

## 8. Regulated Industries Perspective

**Code:** `CONCEPT:REGULATED-INDUSTRIES`

Georgio brings a unique perspective from healthcare and finance — the most regulated AI environments. Errors are "super expensive." This makes him more cautious than practitioners in less regulated industries and shapes his insistence on ROI, fallback scenarios, and staged adoption.

> "I'm from the health care space and the financial space where errors are super expensive. So we are a little bit more careful." (lines 69–71)

> "You can't just build a chatbot and throw it in healthcare. It needs to go through a lot of scrutiny." (line 51)

---

## 9. Dynamic Capabilities Mapping

| Capability | Evidence |
|---|---|
| **Sensing** | Strategy-first approach: examines workflows for automation candidates before building; evaluates ethical considerations and risk; assesses people's knowledge of agent management; multiple intelligence framing helps clients understand AI potential |
| **Seizing** | Multi-agent market research system (PROBE); recruitment pipeline agent; campaign agents; voice agents; controlled agriculture patent (GrowNext); quick wins strategy to build organizational confidence |
| **Transforming** | Insistence on culture change (speed + experimental axes); training/education at all levels; deliberately hiring young people to counter junior pipeline erosion; "don't do the old thing with new tools" philosophy; redefining what quality means per industry context |

---

## Key Takeaways for Thesis

1. **ROI is the ultimate gatekeeper:** Unlike other interviewees who focus on capabilities and possibilities, Georgio centers on the business case. AI initiatives without clear ROI "fly, crash, and move to the next." This grounds the value discussion in financial reality.
2. **Three value buckets are explicit:** Top line growth, bottom line efficiency, and vanity metrics — with only the first two surviving CFO scrutiny. Quality is a fourth bucket relevant in healthcare/regulated industries.
3. **"Don't do the old thing with new tools":** This echoes Maarten's "moving radio" concept but from a transformation consultant's perspective. Both consultants independently warn against retrofitting AI onto existing processes.
4. **Junior pipeline risk confirmed by second voice:** Georgio independently raises the same concern as Maarten: "agents are the new interns." This strengthens the theme across both consultant participants.
5. **Fallback scenarios are overlooked:** The Malaysia power outage story is a concrete, visceral example of what happens when organizations automate without planning for failure. No other interviewee raised this.
6. **Skills deprivation is a systemic concern:** Beyond losing junior jobs, the skills of existing professionals atrophy when AI handles their work. This is distinct from the junior pipeline issue and represents a parallel long-term risk.
7. **Culture is the primary enabler:** Georgio explicitly ranks culture above technology, infrastructure, and use cases. The speed/experimental matrix provides a practical framework for assessing organizational readiness.
8. **Generational clash is a structural obstacle:** The inverted knowledge pyramid (young people with AI skills, power with senior people who distrust it) creates a dynamic not easily resolved by training or policy alone.
9. **Regulated industry lens adds nuance:** The healthcare/finance perspective emphasizes quality over efficiency, cautious adoption over speed, and the cost of errors — a counterweight to the "move fast" narrative from other participants.
