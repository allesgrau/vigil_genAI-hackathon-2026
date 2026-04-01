# Vigil — Find. Warn. Protect.

> The first AI compliance agent that doesn't wait for you to come to it.
> It finds your business, warns you before a deadline hits, and protects your code and documents from regulatory risk — automatically.

---

## The Story

Every year, European SMEs spend billions on legal fees just to understand what EU regulations mean for their business. GDPR, AI Act, DORA, NIS2 — the landscape is vast, constantly shifting, and written in language that's completely inaccessible to non-lawyers.

But here's the real problem: **most founders don't even know they're non-compliant until it's too late.** They don't track regulatory changes. They don't have in-house legal teams. They don't read EUR-Lex over breakfast. They find out when the fine arrives.

Vigil was built on a simple belief: **compliance shouldn't require effort.** Not "less effort." Zero effort. The AI should find you, warn you, and protect you — before you even know there's a problem.

We designed Vigil around one observation from watching hundreds of AI products fail: **people don't want tools, they want outcomes.** They don't want a compliance dashboard. They want to not get fined. They don't want to read regulatory updates. They want someone to tell them exactly what to do, right now, for their specific business.

So we built an agent that does exactly that.

---

## The Pipeline: Find → Warn → Protect

Vigil operates as a three-stage autonomous pipeline. Each stage delivers standalone value; together, they form a closed loop that acquires users, retains them, and continuously reduces their compliance risk.

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   ┌──────────┐       ┌──────────┐       ┌──────────────┐           │
│   │          │       │          │       │              │           │
│   │   FIND   │ ───►  │   WARN   │ ───►  │   PROTECT    │           │
│   │          │       │          │       │              │           │
│   └──────────┘       └──────────┘       └──────────────┘           │
│                                                                     │
│   Scrape registries   Call with personalized `/vigil` Claude Skill    │
│   + regulations.      compliance briefing. scans code & documents   │
│   Match companies     Always follow up     for compliance issues.   │
│   to upcoming risks.  with email. 3mo cool. Web platform access.   │
│                                                                     │
│   CAC = ~0            Conversion trigger   Retention engine         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Stage 1 — FIND

Vigil autonomously discovers companies that are at risk of non-compliance.

**What happens:**
1. Apify scrapers monitor 30+ regulatory sources across 18 EU countries (EUR-Lex, EDPB, national DPAs, sector regulators). This already exists and works.
2. A second set of scrapers pulls company data from public business registries — KRS (Poland), Handelsregister (Germany), Companies House (UK), Infogreffe (France), and equivalent registers across the EU.
3. Claude classifies each company by industry, jurisdiction, and applicable regulations — based on registry data (legal form, SIC/NACE codes, registered activities).
4. A matching engine cross-references upcoming regulatory deadlines with each company's profile: *which regulations apply to this company, and which deadlines are approaching?*
5. Companies with a match enter the **outreach queue**, prioritized by deadline urgency and estimated regulatory exposure.

**Output:** A ranked list of companies + their specific compliance risks + contact details, ready for Stage 2.

**What makes this novel:** No compliance startup does outbound. Every single player in the market — Clausematch, Hyperproof, Drata, Vanta — waits for companies to find them. Vigil flips the model: **the compliance tool finds the company.** Customer acquisition cost approaches zero.

---

### Stage 2 — WARN

Vigil reaches out to at-risk companies with a personalized, actionable compliance alert.

**What happens:**
1. For each company in the outreach queue, Claude generates a short, plain-language briefing tailored to their specific situation: what regulation applies, what changed, what the deadline is, and what 2-3 concrete steps they should take.
2. **Twilio Voice call.** An AI agent calls the company's public phone number. The agent delivers the personalized briefing conversationally and offers to send a full report by email.
3. **Follow-up email (always).** Whether the company answers the call or not, they receive a follow-up email (SendGrid) with the full compliance briefing, a link to the report, and an option to subscribe to the Vigil platform.
4. **If the company does not engage, Vigil enters a strict 3-month cooldown** — zero contact for 3 months. After that, one more attempt if a new relevant deadline is approaching. No spam, no pressure, ever.

**For subscribers (after purchasing via email link), Warn becomes continuous:**
- Monthly automated digests with all regulatory changes relevant to their profile.
- Push alerts for critical deadlines (30-day, 14-day, 7-day warnings).
- Email notifications for high-severity regulatory changes.

**Output:** Converted subscribers who now receive ongoing, personalized compliance monitoring.

**What makes this novel:** The proactive outreach (call + email) mirrors the pattern that won the Google DeepMind hackathon — but applied to a domain where the stakes are 1000x higher. A missing website costs nothing. A GDPR fine costs up to 4% of global annual revenue.

---

### Stage 3 — PROTECT

Vigil actively checks subscribers' code and documents for compliance violations — before regulators do. No uploads, no dashboards, no context-switching. Just `/vigil` in your terminal.

**The `/vigil` Claude Skill:**

Subscribers get access to a **Claude Code Skill** — a slash command that works directly in the developer's terminal. The skill has full access to the current working directory, just like Claude Code itself.

```
Developer types /vigil
    ↓
Skill reads the codebase (Glob, Read, Grep — full file access)
    ↓
Claude analyzes code + documents against subscriber's regulatory profile
    ↓
Returns structured compliance report directly in the terminal
```

**What the skill checks:**

- **Source code** — PII storage without encryption, cross-border data transfers, automated decision-making without human-in-the-loop, missing consent mechanisms, logging of sensitive data, non-compliant data retention logic.
- **Documents in the repo** — privacy policies, terms of service, DPAs, consent forms. Completeness checks against regulation requirements (e.g., GDPR Art. 13/14 required disclosures), outdated references, missing sections mandated by recent regulatory guidance.
- **Configuration & infrastructure** — Dockerfiles, cloud configs, CI/CD pipelines for data residency issues, unencrypted storage, missing access controls.

**What the skill returns:**

Each finding includes: the specific regulation and article, what the issue is in plain language, why it matters (potential fine, enforcement precedent), and a concrete recommended fix. Findings are ranked by severity: critical (immediate legal risk), high (upcoming deadline), medium (best practice gap).

**Why a Claude Skill, not a web upload?**

- **Zero friction.** The developer never leaves their terminal. No file picker, no drag-and-drop, no browser tab. Just `/vigil`.
- **Full context.** The skill sees the entire repo — code, configs, docs, `.env.example`, Docker setup — exactly the way Claude Code does. A web upload would require the user to decide what to upload. The skill decides what to read.
- **Instant.** No upload time, no server processing queue. Claude reads the files locally and returns findings in seconds.

**Subscriber web platform (complementary):**

Alongside the skill, subscribers also get access to the Vigil web platform:
- **Regulation library** — browse current regulatory frameworks with plain-language summaries (already built).
- **Regulatory digest on demand** — generate a detailed compliance digest at any time (existing Vigil functionality).
- **Alert preferences** — configure notification channels (email) and severity thresholds.
- **Compliance history** — track issues found and resolved over time.

**Output:** Actionable compliance feedback that prevents violations before they happen — delivered where the developer already works.

**What makes this novel:** Compliance checking today is post-factum — audits, legal reviews, incident response. Vigil shifts compliance left: the same way linters catch bugs before deployment, Vigil catches regulatory risk before it becomes a violation. And it does it as a single slash command — no new tool to learn, no new tab to open. It's **Grammarly for compliance, built into your IDE** — except instead of fixing your grammar, it prevents a fine that could bankrupt your company.

---

## Target Functionality

### Core (Find → Warn → Protect)

| Feature | Stage | Description |
|---|---|---|
| Regulatory monitoring | Find | 30+ EU sources, 18 countries, 6 regulation families. Fact-based RAG pipeline with hybrid retrieval. Already built. |
| Business registry scraping | Find | Automated discovery of EU companies from public registries (KRS, Handelsregister, Companies House, etc.) with industry/jurisdiction classification. |
| Company-risk matching | Find | Cross-reference company profiles with approaching deadlines to identify at-risk businesses. |
| AI voice outreach | Warn | Twilio Voice agent delivers personalized compliance briefing via phone call. |
| Follow-up email (always) | Warn | After every call (answered or not), company receives email with full briefing, report link, and subscription option. 3-month cooldown for non-responders. |
| Subscriber monitoring | Warn | Monthly digests, deadline alerts, email notifications for regulatory changes. |
| `/vigil` Claude Skill | Protect | Subscribers run `/vigil` in their terminal — Claude reads the entire repo and returns a compliance report. |
| Web platform | Protect | Regulation library, on-demand digests, alert preferences, compliance history. |

### Conversion funnel

```
FIND                    WARN                         PROTECT
────                    ────                         ───────
Scrape registries  ──►  Call (Twilio Voice)
                        │                             Subscriber gets:
                        ├─ Answered or not ──►        • /vigil Claude Skill
                        │   Follow-up email    ──►    • Web platform access
                        │   with briefing +           • Monthly digests
                        │   report link +             • Deadline alerts
                        │   subscription option
                        │
                        └─ No engagement ──► 3-month cooldown
                                             Then retry once if
                                             new deadline approaching
```

---

## Business Model

```
FREE (outreach)                    SUBSCRIBER (49 EUR/month)
───────────────                    ─────────────────────────
One call + follow-up email         /vigil Claude Skill (unlimited scans)
  with personalized briefing       Regulation library (web platform)
                                   Regulatory digest on demand
                                   Monthly automated monitoring
                                   Email deadline alerts
                                   Compliance history
```

**Unit economics:**
- Cost per outreach (call + email): ~0.50 EUR
- Cost per compliance scan (LLM + embeddings): ~0.30 EUR
- Cost per monthly digest (full pipeline): ~2.00 EUR
- **Subscriber LTV at 12-month retention:** 588 EUR
- **CAC:** ~0.50 EUR (the cost of the initial outreach call)
- **LTV:CAC ratio:** ~1,176:1

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Scraping | Apify (website-content-crawler) | Regulatory sources + business registries |
| LLM | Claude (via OpenRouter) | Fact extraction, digest generation, compliance analysis, voice agent script |
| Embeddings | text-embedding-3-small (OpenRouter) | Semantic search over regulatory facts |
| Voice | Twilio Voice + TwiML | AI-powered outreach calls |
| Email | SendGrid | Follow-up emails with briefing, report link, and subscription option |
| Compliance Skill | Claude Code Skill (`.claude/skills/`) | `/vigil` — scans repo for compliance issues |
| Frontend | Streamlit (current) → Next.js (production) | Subscriber web platform |
| Backend | Python + FastAPI | API layer for subscriber management + digests |
| Storage | PostgreSQL + Pinecone/Qdrant | Company profiles, compliance history, vector store |
| Scheduling | Apify Scheduler / cron | Monthly regulatory scans + outreach runs |

---

## Demo Script (3 minutes)

**[0:00–0:15] Hook**
"Last year, EU regulators issued 2.1 billion euros in GDPR fines alone. Most of those companies didn't even know they were non-compliant. What if an AI agent could warn them before the fine arrives — and then actually help them fix the problem?"

**[0:15–1:15] Act 1 — FIND + WARN**
Live demo: Vigil has scraped the German business registry. It found a fintech startup in Berlin. AI Act Article 52 deadline is in 28 days. Watch what happens.
→ Twilio call rings on stage. AI agent delivers a 30-second personalized briefing.
→ Call goes to voicemail. An email with the full briefing and report link fires automatically.
→ "That company just got warned — for free — about a deadline they didn't know existed. Vigil found them. They didn't find Vigil."
→ "Whether they pick up or not, they get an email with a full briefing, a compliance report, and a link to subscribe. If they don't engage — we respect that. Zero contact for 3 months."

**[1:15–2:15] Act 2 — PROTECT**
"Now let's say they subscribed. Their CTO opens the terminal and types one command."
→ Live terminal: `/vigil`
→ Claude reads the codebase — Python files, configs, privacy policy in the repo.
→ Report appears in terminal: "3 compliance issues found. #1: You're storing user email addresses in plaintext logs — GDPR Article 32 requires encryption of personal data at rest. Here's the fix."
→ "And look — it also found the privacy policy markdown in the repo. Missing section: automated decision-making disclosure required by GDPR Article 22."
→ "One command. Full compliance scan. No uploads, no dashboards, no context-switching."

**[2:15–2:50] Act 3 — Business model**
"The first alert — the call and the email — that's free. Subscription: 49 EUR/month. That gives you `/vigil` for your codebase, the regulation library, monthly digests, deadline alerts. Less than one coffee a day. The average GDPR fine is 1.4 million euros. Our customer acquisition cost is 50 cents — because Vigil finds the customers, not the other way around. We don't do marketing. We do compliance."

**[2:50–3:00] Close**
"Vigil. Find. Warn. Protect. Stop paying lawyers to tell you what an AI agent already knows."
