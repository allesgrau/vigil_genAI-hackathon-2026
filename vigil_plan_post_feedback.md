# Vigil — Action Plan Post-Feedback (1 April, afternoon + 2 April)

> Based on science fair judge feedback. Ordered by IMPACT on demo + pitch.
> Time available: ~3h today (15:00-18:00+) + ~4h tomorrow (09:00-13:00)

---

## What's already DONE

- [x] Live Apify scraping (regulations + registry) — `orchestrator.py`
- [x] Claude LLM alert matching — `orchestrator.py`
- [x] Twilio Voice call + webhook — `voice_agent.py`, `webhook_server.py`
- [x] SendGrid email from vigilcompliance@gmail.com — `email_sender.py`
- [x] `/vigil` Claude Code skill — `skill/vigil-compliance.md`
- [x] Demo sample app with 8 bugs — `demo/sample_app/`
- [x] Streamlit dashboard (3 tabs: Digest, Regulation Library, /vigil Skill) — `app.py`
- [x] Landing page v1 on Vercel — `v0-vigil-landing-page-eight.vercel.app` (3-step, needs update to 4-step)
- [x] Orchestrator MVP (fallback) + LIVE (zero mocks)
- [x] Pitch deck (8 slides, Google Slides — needs update to 4-step)
- [x] Hub page v1 — `landing/index.html` (local only, not deployed)

## What's NOT ready yet

- [ ] Call script too long (~1 min, needs 15-20 sec)
- [ ] Email is basic HTML — needs full compliance report (judge #1 feedback)
- [ ] No pipeline activity dashboard (judge feedback: "all in terminal logs")
- [ ] Vercel landing page still shows 3-step (needs 4-step: Find→Warn→Report→Protect)
- [ ] Hub page (`landing/index.html`) not deployed — local file only
- [ ] API Docs link in hub works only when server is running locally (ngrok)
- [ ] No demo video (2 min, required deliverable)
- [ ] No Devpost project description
- [ ] No PDF slide (16:9) for pitch
- [ ] Streamlit regulation library may have hardcoded descriptions
- [ ] Pitch deck needs update (4-step, pricing, next 3 steps)
- [ ] No backup video in case of demo failure

---

## PRIORITY 1: Code changes for judge feedback (today, 15:00-17:00)

### P1.1 — Shorten call script + add "automated message" (15 min)
**Why:** Call is too long (~1 min). Should be 15-20 seconds max.

- [ ] Update `src/outreach/script_generator.py`:
  - Change prompt to generate max 2 sentences (not 4)
  - Always start with: "This is an automated compliance alert from Vigil."
  - Always end with: "Press 1 to receive a detailed compliance report by email."
  - No small talk, no "I'd be happy to", no conversational tone

**Target script (entire call should sound like this):**
> "This is an automated compliance alert from Vigil.
> Your company, TechStartup GmbH, has 28 days to register AI systems
> used in credit scoring under the EU AI Act, Article 6.
> Press 1 to receive a detailed compliance report by email."

**Test:** `python demo/call_demo.py` → call should be ~15 seconds

### P1.2 — Upgrade email to full compliance report (1h) ⭐ MOST IMPORTANT
**Why:** Judge said "the email report is the most important part." Currently just a basic alert.

- [ ] Rewrite `src/outreach/email_sender.py`:
  - Use Claude to generate a rich, legally specific compliance report
  - For EACH finding include:
    - Regulation + exact article
    - What was found (plain language — "supply chain" = software deps, not trucks)
    - What this means (fines, which auditor will check)
    - What exactly to do (numbered action steps)
    - Estimated effort
  - "Recommended Next Steps" section
  - CTA: "Want automated code scanning? Install /vigil"
  - Link to hub page / landing page
- [ ] Test: `python demo/call_demo.py` → press 1 → email should be rich report

### P1.3 — Pipeline activity dashboard in Streamlit (45 min)
**Why:** Judge said "the whole action is in terminal logs — need business-friendly dashboard"

- [ ] Add new tab in `app.py`: "Pipeline Monitor" or "Vigil Activity"
- [ ] Show pipeline steps with status indicators:
  ```
  ✅ Scraping 15 regulatory sources... done
  ✅ Scraping 4 business registries... found 4 companies
  ✅ Extracting facts with Claude... 12 facts extracted
  ✅ Matching risks... 3 critical risks identified
  ✅ Outreach initiated... 2 calls placed, 1 email sent
  ```
- [ ] Can use mock data for now — the visual is what matters for demo
- [ ] Use `st.status()` or progress indicators

---

## PRIORITY 2: Deliverables (today 17:00-18:00 + tomorrow 09:00-11:00)

### P2.1 — 2-minute demo video (45 min) ⭐ CRITICAL DELIVERABLE
**Why:** Required submission. Must show system ACTUALLY WORKING.

Storyline:
1. **(0:00-0:15) Hook:** "150 billion euros spent on compliance yearly. 55% of SMEs say it's their biggest burden."
2. **(0:15-0:30) Problem:** "Most SMEs find out about regulations when the fine arrives. Meet Vigil."
3. **(0:30-0:45) FIND:** Show terminal — orchestrator scraping live.
4. **(0:45-1:15) WARN:** Phone rings on camera. Hear briefing on speaker.
5. **(1:15-1:30) REPORT:** Show email arriving. Open compliance report.
6. **(1:30-1:50) PROTECT:** Show `/vigil` in Claude Code. Show findings.
7. **(1:50-2:00) Close:** "Find. Warn. Report. Protect. Vigil."

**Tools:** OBS Studio or loom.com for screen recording + voiceover.

### P2.2 — Devpost project description (30 min)
**Why:** Required deliverable. Functions as one-pager.

Structure: Inspiration → What it does (4 steps) → How we built it → Challenges → What's next

### P2.3 — 1 PDF slide (16:9) for pitch display (20 min)
**Why:** Displayed on screen during 2-min pitch.

- [ ] Use Canva or v0.dev
- [ ] Navy theme, "Find. Warn. Report. Protect." + pipeline diagram + key stats
- [ ] Must be BEAUTIFUL

### P2.4 — Update Vercel landing page to 4-step (30 min)
**Why:** Current landing page still shows 3-step pipeline. Needs to match new 4-step vision.

- [ ] Go to v0.dev, send follow-up prompt:
  ```
  Update the pipeline to 4 steps: Find, Warn, Report, Protect.
  Add "Report" between Warn and Protect — it's a detailed compliance
  report sent to compliance officers. Update pricing to:
  Free (1 alert), Starter EUR 19/mo, Pro EUR 39/mo.
  ```
- [ ] Re-publish on Vercel

### P2.5 — Deploy hub page (15 min)
**Why:** `landing/index.html` is local only. Need it accessible.

Options (pick one):
- [ ] **GitHub Pages** — push `landing/` folder, enable Pages in repo settings
- [ ] **Vercel** — deploy `landing/` as separate project
- [ ] **Just open locally during demo** — simplest, works fine for pitch

### P2.6 — Update pitch deck (20 min)
**Why:** Current deck says 3-step. Needs 4-step + pricing + next 3 steps post-hackathon.

- [ ] Change "Find. Warn. Protect." → "Find. Warn. Report. Protect." everywhere
- [ ] Update pipeline slide to show 4 steps
- [ ] Add/update pricing slide (EUR 19/39/custom)
- [ ] Add "Next 3 Steps" slide: Jira/Slack, multi-jurisdiction, CI/CD
- [ ] Fix typo: "Build" → "Built" on last slide

---

## PRIORITY 3: Polish (tomorrow 11:00-12:30 — ONLY if P1+P2 done)

### P3.1 — Streamlit frontend improvements (30 min)
- [ ] Check regulation library — are descriptions hardcoded? Fix if yes
- [ ] Add sidebar details for business users
- [ ] Improve visual design

### P3.2 — Update hub page links (10 min)
- [ ] Update API Docs link (only works with running server — add note or remove)
- [ ] Update any placeholder links to real URLs
- [ ] Add demo video embed once video is done

### P3.3 — Scheduled orchestrator mention (5 min)
- [ ] Don't build it — just mention in pitch: "runs weekly, automatically"
- [ ] Optionally add a note in Streamlit dashboard sidebar

### P3.4 — Repo cleanup (Basia does manually)
- [ ] Clean up file structure
- [ ] Update README.md
- [ ] Remove debug prints
- [ ] Ensure `.env.example` exists (no secrets!)
- [ ] Remove `venv_old/` folder

---

## 2-Minute Pitch Script (for finals)

### [0:00-0:15] Hook + Stats
> "150 billion euros. That's what European companies spend on regulatory
> compliance every year. 55% of EU-based SMEs say compliance is their
> single biggest operational burden. My friends building startups in
> Warsaw tell me: 'I spend more time reading regulations than writing code.'"

### [0:15-0:30] Problem
> "And the worst part? New regulations keep coming. The AI Act just
> dropped with deadlines starting August 2026. Most SMEs will find out
> when the fine arrives — up to 35 million euros."

### [0:30-0:45] Solution — 4 steps
> "Vigil fixes this in 4 steps. Find — we scrape EU regulatory sources
> and business registries to identify companies at risk. Warn — an AI
> agent calls the company with a 15-second automated compliance alert.
> Report — a detailed, legally specific compliance report is sent by email.
> Protect — engineers type /vigil and their codebase is scanned for
> compliance violations."

### [0:45-1:00] Tech Stack (brief)
> "Built on Apify for web scraping, Claude for intelligence, Twilio for
> voice, SendGrid for reports. The entire pipeline runs live — zero mocks.
> Let me show you."

### [1:00-1:30] LIVE DEMO (show terminal + phone + email)
> [Trigger orchestrator → phone rings → show email report]
> "That just happened live. Real scraping, real AI matching, real phone call,
> real compliance report."

### [1:30-1:45] Business Model
> "The first alert is free — that's how we acquire customers. Subscription
> starts at 19 euros per month. Our marginal cost per customer is 22 cents.
> That's a 99% gross margin."

### [1:45-2:00] Next Steps + Close
> "Three next steps: Jira and Slack integration to turn reports into
> engineering tickets. Multi-jurisdiction expansion — UK, Switzerland, US.
> And CI/CD integration — Vigil on every pull request.
> 24 million SMEs in Europe. Vigil finds them, warns them, reports to them,
> protects them. Thank you."

---

## Schedule

### Today (1 April, afternoon)
| Time | Task | Priority | Status |
|---|---|---|---|
| 15:00-15:15 | P1.1 — Shorten call script | P1 | [ ] |
| 15:15-16:15 | P1.2 — Upgrade email to compliance report | P1 ⭐ | [ ] |
| 16:15-17:00 | P1.3 — Pipeline activity dashboard | P1 | [ ] |
| 17:00-17:30 | P2.4 — Update Vercel landing page (4-step) | P2 | [ ] |
| 17:30-17:50 | P2.6 — Update pitch deck (4-step + pricing) | P2 | [ ] |
| 17:50-18:00 | P2.5 — Deploy hub page (or decide to open locally) | P2 | [ ] |

### Tomorrow (2 April, morning)
| Time | Task | Priority | Status |
|---|---|---|---|
| 09:00-09:45 | P2.1 — Record demo video | P2 ⭐ | [ ] |
| 09:45-10:15 | P2.2 — Devpost description | P2 | [ ] |
| 10:15-10:35 | P2.3 — PDF slide for pitch | P2 | [ ] |
| 10:35-11:00 | P3.1 — Streamlit improvements | P3 | [ ] |
| 11:00-11:15 | P3.2 — Update hub page links | P3 | [ ] |
| 11:15-11:30 | P3.4 — Repo cleanup | P3 | [ ] |
| 11:30-12:00 | Rehearse pitch 3x | CRITICAL | [ ] |
| 12:00-12:30 | Final dry run (call + email + /vigil) | CRITICAL | [ ] |
| 12:30-12:50 | Buffer for fixes | | [ ] |
| 12:50-13:00 | Breathe. | | [ ] |
| 13:00 | SUBMISSION | | [ ] |

---

## What NOT to do

- Do NOT build Jira/Slack integration (just mention in pitch)
- Do NOT build payment/Stripe (just show pricing)
- Do NOT build multi-country scraping (just mention in pitch)
- Do NOT spend more than 30 min on Streamlit visual polish
- Do NOT rewrite landing page from scratch (iterate on v0.dev)
- Do NOT build scheduled orchestrator (just mention it)
- **Deliverables (video, Devpost, slide) > code improvements**
- **If you're behind schedule, cut P3 entirely and focus on deliverables**
