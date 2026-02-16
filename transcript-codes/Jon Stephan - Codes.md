# Transcript Coding: Jon Stephan

**Interview Date:** Feb 13  
**Participant Role:** AI Specialist / Strategist, Digital Marketing  
**Organization:** Merck KGaA (sigmaaldrich.com — life sciences ecommerce, ~300,000 products)  
**Interview Duration:** ~55 minutes  

---

## Participant Profile

Jon Stephan is an AI specialist strategist within digital marketing at Merck KGaA. He works on the ecommerce platform sigmaaldrich.com, focusing on evaluating, developing, and deploying AI tooling and solutions. His background is unusual: he started as an R&D scientist (bacteriology, proteomics, genomics) and transitioned into digital marketing through bioinformatics work. He has no formal marketing education but learned on the job. He has been deeply engaged with AI since ChatGPT's launch in November 2022.

---

## 1. AI Applications & Use Cases

### 1.1 Data Analysis Agent
**Code:** `AI-APPLICATION:DATA-ANALYSIS`

Jon describes developing a data agent that can query tables and find insights from ad performance and product sales data. The agent functions as a "data scientist" that non-technical marketers can interact with instead of requiring SQL skills.

> "We want to create quicker and newer insights using a data agent to be able to go through this information and say, hey. Why did sales go up this day? Why did they go down? [...] not everyone who is a marketer, knows SQL, and is a data scientist and can find statistical relevancy but agents who can make decisions can query tables and do things like that, that really would be powerful to us in the sense that we have agent who is a data scientist." (line 32)

### 1.2 Content Generation at Scale
**Code:** `AI-APPLICATION:CONTENT-GENERATION-SCALE`

An AI workflow generates ad copy (headlines and descriptions for Google Search) for ~300,000 products. What would have taken a year with human writers was completed in approximately one week.

> "How do we create 300,000 ads at scale? [...] With an AI work you basically, you know, send it the product information over and over and over again. And you can generate ads for all of our products within, think, think it was a week is all it really took." (line 50)

### 1.3 Content Evaluation (Agentic)
**Code:** `AI-APPLICATION:CONTENT-EVALUATION`

An agentic workflow evaluates social media images for emotional appropriateness, assigning safety ratings and making decisions about image suitability through a decision tree.

> "We wanna make sure all of our images won't cause any emotional feelings within our constituency. [...] Is this image safe or purposeful for social media? We made an agentic workflow around that as well." (line 50)

> "The emotional decision was more agentic in the sense that it would give ratings to things for social media. Rate this one out of 10 in safety scale [...] would make a decision tree of where to bucket these types of images." (line 52)

### 1.4 Product Knowledge Chatbot (RAG)
**Code:** `AI-APPLICATION:PRODUCT-CHATBOT`

A chatbot using vector database search helps both salespeople and marketers understand complex scientific products. It bridges the knowledge gap between scientific product complexity and marketing/sales needs.

> "An LLM chatbot that uses a vector database to find the product information and look through it and say, hey, yeah, this would be compatible with the scientific experiment you would want to do." (line 34)

> "Not our digital marketers have a scientific background. So this really helps explain the products to them as well." (lines 34–36)

### 1.5 AI Image Generation
**Code:** `AI-APPLICATION:IMAGE-GENERATION`

The team has begun exploring AI image generation, particularly after quality improvements (Gemini "Nano Banana" models) enabled accurate depictions of scientists in lab settings.

> "When Nano Banana came out, that was a huge game changer for us because it could finally generate images that were, you accurate towards scientists in the lab." (line 116)

### 1.6 AI Video Generation (Exploratory)
**Code:** `AI-APPLICATION:VIDEO-GENERATION`

Jon is experimenting with video generation tools (Sora, VO 3.2, Seed Dance 2.0) for potential CTV/video advertising. This is still in buy-in phase.

> "Seed Dance 2.0 [...] That is unbelievably great for video generation. I've messed around with Sora and, VO 3.2. I've done some example ads. Nothing has really launched yet because we have to get a lot of buy in to do something like that." (line 154)

### 1.7 Market Intelligence / Deep Research
**Code:** `AI-APPLICATION:MARKET-INTELLIGENCE`

Using LLM deep research capabilities to identify market trends, portfolio gaps, and expansion opportunities.

> "You can really find out through, a deep research capabilities within them to see where the market's going, where our gaps are, and then move towards them." (line 46)

---

## 2. Benefits

### 2.1 Improved Ad Spend Efficiency (ROAS)
**Code:** `BENEFIT:AD-EFFICIENCY`

A measurable 0.5 ROAS uplift, which Jon considers "phenomenal." Efficiency means spending money better, not necessarily spending less.

> "We've seen a point five ROAS increase which is pretty good. So, like, a three ROAS would be 300% return. We've seen a point five uplift within that. And I think that's phenomenal." (line 80)

> "Efficiency doesn't really mean spend less money. It means spend it better. So if an ad is underperforming, how do you fix it? Then use that saved money for another ad." (line 42)

### 2.2 Better Conversion Rates
**Code:** `BENEFIT:CONVERSION-RATES`

More specific and relevant content leads to better conversion rates, reducing wasted clicks (e.g., non-scientists accidentally reaching the site).

> "Better conversion rates with better content. You know? It's very specific to what a user is looking for, that really helps. It brings them into the website. They buy it." (line 70)

### 2.3 Speed & Scale
**Code:** `BENEFIT:SPEED-AND-SCALE`

Dramatic reduction in time-to-market for content creation (from 1 year to 1 week for 300K product ads).

> "If we, you know, got some of the scientists from the lab to help us write ad copy, it would take probably about a year. With an AI work [...] within, think, think it was a week is all it really took." (line 50)

### 2.4 Democratization of Data Insights
**Code:** `BENEFIT:DATA-DEMOCRATIZATION`

AI enables marketers without SQL or data science skills to access insights that previously required specialized expertise.

> "Not everyone who is a marketer, knows SQL, and is a data scientist and can find statistical relevancy but agents who can make decisions can query tables [...] that really would be powerful." (line 32)

### 2.5 Employee Elevation
**Code:** `BENEFIT:EMPLOYEE-ELEVATION`

AI is positioned as an elevator for existing employees rather than a replacement. Best employees become even better.

> "We see it as more of an elevator. In other words, we wanna eat put these tools in place to make our best employees even better. We're not looking at we look at efficiencies so that we can expand, not so that we can draw back." (line 90)

---

## 3. Drawbacks & Risks

### 3.1 Brand Risk / Hallucination
**Code:** `RISK:HALLUCINATION`

LLMs can generate inaccurate content that could damage the brand. Example: the system generated "free shipping" as a headline when the company does not offer free shipping.

> "One time [...] It said free shipping as one of the headlines. And that was like, wow. Okay. That's a pretty good headline. If we had free shipping. We do not have free shipping." (line 94)

### 3.2 Non-Determinism
**Code:** `RISK:NON-DETERMINISM`

The non-deterministic nature of LLMs confuses stakeholders and creates trust issues. The team addresses this by lowering temperature settings for scientific products.

> "LLMs are nondeterministic. So people give, at least at first [...] They're very confused how you can ask an LLM a question five times in a row and possibly get, you know, different answers each time." (line 88)

> "Temperature is more how you can make it more deterministic, you just lower that number. And we want that number as low as possible because we sell scientific products." (line 94)

### 3.3 Corporate Fear / Job Anxiety
**Code:** `RISK:JOB-FEAR`

Employees fear AI as a job eliminator, particularly in the US where employment protections are weaker. This creates resistance and slows adoption.

> "There is within corporations [...] an insane amount of fear. [...] Will this take my job? I'm like, not today." (line 82)

> "People can be let go in The US for any reason and that they are." (line 88)

### 3.4 Model Deprecation Risk
**Code:** `RISK:MODEL-DEPRECATION`

Rapid model iteration means workflows break when models are deprecated. Requires constant retesting and migration.

> "What I am more concerned about now is, model, deprecation and them turning it off, because I know four o is being turned off soon. And I have some, you know, workflows and agents out there that are, you know, using four o." (line 110)

### 3.5 Incremental (Not Transformative) Results
**Code:** `RISK:INCREMENTAL-RESULTS`

Results so far have been incremental rather than transformative, which fuels skepticism among some stakeholders.

> "We've never seen, like, a home run. [...] We've seen incremental increases in improvements. So corporate fear, I it's a combination of things." (line 88)

---

## 4. Organizational Enablers

### 4.1 Supportive Immediate Management
**Code:** `ENABLER:MANAGEMENT-BUY-IN`

Jon's manager gave him full autonomy to explore AI from the start. This was described as "pivotal."

> "The courage of my manager right when ChatGPT came out was just unbelievable. It's like, you what you need to do. That's what she told me. And that was just great. And she just let me go and run." (line 136)

### 4.2 Free API Access (Corporate Strategy)
**Code:** `ENABLER:FREE-API-ACCESS`

The corporation provided free API access (not charged to individual cost centers) to accelerate AI adoption across the organization.

> "They gave AP access so that we could call AI at scale to any group for free. [...] We can scale this for free? Let's do this." (line 110)

> "They expand it as quickly as they can. They get as many people on board as they can. And once they hit a threshold of users, then they start tightening up on cost." (line 130)

### 4.3 Internal AI Community
**Code:** `ENABLER:AI-COMMUNITY`

AI specialists are distributed throughout the corporation and collaborate informally when developing solutions.

> "We don't have an AI group [...] we have probably AI strategists and specialists all throughout the corporation. So whenever we're developing something, that's when we reach out to each other." (line 98)

### 4.4 Human-in-the-Loop
**Code:** `ENABLER:HUMAN-IN-LOOP`

All AI outputs go through human evaluation before deployment, ensuring brand safety while still benefiting from automation.

> "Like everything agentic in the corporate world, there almost always needs to be a human evaluator at one point." (line 52)

### 4.5 Personal Drive / Evangelism
**Code:** `ENABLER:PERSONAL-DRIVE`

Jon's personal obsession with AI since ChatGPT's launch is a critical driver. He actively evangelizes through training sessions.

> "I've been trying to evangelize this as well by going through training sessions with my coworkers, showing them the agents [...] developed or that they themselves can develop." (line 120)

---

## 5. Organizational Obstacles

### 5.1 Corporate Politics & Silos
**Code:** `OBSTACLE:CORPORATE-POLITICS`

Credit attribution, territorial behavior, and organizational silos slow down cross-group AI initiatives.

> "If I'm in control of x at a corporation, and someone in group y says, hey. I have this really cool idea. They're afraid that I'm gonna get credit for it, and I'm going to somehow one up them." (line 162)

> "Management and upper management [...] they're playing the game." (line 162)

### 5.2 Uneven Adoption Across Team
**Code:** `OBSTACLE:UNEVEN-ADOPTION`

Large gaps exist between early adopters (like Jon) and most team members who still only use AI for basic tasks like email generation.

> "Some people are still at to the point where, like, well, I just use ChatGPT to generate emails for me. [...] I think it's, you know, people finding the time to find the utility of it." (line 120)

### 5.3 External Partner Resistance
**Code:** `OBSTACLE:PARTNER-RESISTANCE`

External partners (e.g., a film studio) refuse to use any AI tools, creating friction in collaborative workflows.

> "We work with a film studio [...] and they're anti AI. To a large degree. Like, they even use AI within Adobe [...] They refuse to touch anything about AI." (line 122)

### 5.4 European Regulation / Workers' Council
**Code:** `OBSTACLE:REGULATION`

German labor laws and workers' council agreements impose restrictions such as prohibiting sharing personal information with LLMs.

> "No sharing of personal information with an LLM like a person's name. Not that I would be doing that, but I just find little odd quirks like that." (line 136)

---

## 6. Agentic vs. Workflow Distinction

**Code:** `CONCEPT:AGENTIC-VS-WORKFLOW`

Jon draws a clear distinction: content generation is a "pure workflow with LLM" (filtering steps, no real decisions), while content evaluation is "more agentic" because it involves rating, bucketing, and decision-making.

> "The workflow for the, content generation, it was mostly a peer workflow with LLM [...] The, emotional decision was more agentic in the sense that it would give ratings to things [...] making more of a decision step." (line 52)

Jon also defines agentic AI as:

> "Something where it can evaluate a space and make decisions upon it. [...] There needs to be a decision point where previously there was a person." (line 28)

---

## 7. Future Outlook

### 7.1 AI Mode in Search Engines
**Code:** `FUTURE:AI-SEARCH`

Google's AI mode is changing the advertising landscape, reducing advertiser control and analytics visibility.

> "With AI mode right now, you don't even know when customers are coming to your website through AI mode in Google. Nor do you even control the AI advertising within there." (line 164)

### 7.2 Continuous Technology Improvement
**Code:** `FUTURE:TECH-IMPROVEMENT`

Jon holds a "just wait" philosophy — technology always improves faster than skeptics expect.

> "People don't think it will get better. Which I always find odd. [...] It will get better, and then it does." (line 154)

### 7.3 Undisclosed Recent Launch
**Code:** `FUTURE:NEW-INITIATIVE`

A new AI-driven initiative was launched the same week, described as "solving a decade-old problem," but Jon could not share details.

> "We just launched one this week. I really can't talk about it. It's a type of content that we will have on our website. [...] It's really cool, and it solves a decade old problem." (line 150)

---

## 8. Dynamic Capabilities Mapping

| Capability | Evidence |
|---|---|
| **Sensing** | Deep research for market gaps; testing every new model/tool on release; personal drive to evaluate new technologies within days |
| **Seizing** | Rapid prototyping of agents and workflows; leveraging free API access; building cross-group coalitions by sharing credit |
| **Transforming** | Evangelizing through training sessions; building internal chatbots to bridge knowledge gaps; shifting marketing workflows from manual to AI-assisted at scale |

---

## Key Takeaways for Thesis

1. **Scale as differentiator:** The real value of AI in marketing emerges at scale (300K products), where manual approaches become impossible — not just slower.
2. **Agentic = decision-making:** Jon's practical definition of agentic AI centers on decision points that replace human judgment, distinct from workflow automation.
3. **Human-in-the-loop is non-negotiable (for now):** Corporate brand risk concerns require human evaluation, but this may evolve over time.
4. **Incremental gains, not home runs:** Real-world AI results are incremental (0.5 ROAS uplift), which creates a narrative challenge for advocates.
5. **Adoption is champion-driven:** A single passionate individual with management support can drive organization-wide AI adoption.
6. **Cost strategy accelerates adoption:** Making AI "free" (absorbing costs centrally) removes barriers and enables experimentation.
7. **Model deprecation is an operational risk:** The rapid pace of AI model evolution creates ongoing maintenance burden for production workflows.
8. **Corporate politics > technical barriers:** The main obstacles are organizational (silos, credit, fear), not technical.
