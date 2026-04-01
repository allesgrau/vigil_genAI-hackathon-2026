# Vigil — Vision Post-Feedback (Science Fair, 1 April 2026)

> Updated after judge feedback: "Too split between engineers and compliance lawyers.
> Make it 4 steps. The email report is the most important part — it must be
> legally specific but business-friendly."

---

## The 4-Step Pipeline: Find → Warn → Report → Protect

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  1. FIND     │ ──► │  2. WARN     │ ──► │  3. REPORT   │ ──► │  4. PROTECT  │
│  Regulations │     │  Phone call  │     │  For lawyers │     │  For devs    │
│  + Companies │     │  (automated) │     │  & business  │     │  /vigil scan │
└─────────────┘     └─────────────┘     └──────────────┘     └──────────────┘
   Apify crawl         Twilio Voice       Email with full       Claude Code
   Claude extract      15-sec alert       compliance report     Skill
   Claude match        "Press 1"          + action items        Code scanner
```

### Step 1: FIND (unchanged)
- Scrape EU regulatory sources (EUR-Lex, EDPB, national regulators) via Apify
- Extract structured compliance facts with Claude
- Scrape business registries to identify affected companies
- Match companies to risks with Claude LLM

### Step 2: WARN (shortened — 15 seconds)
- Automated phone call: "This is an automated compliance alert from Vigil."
- **Max 3 sentences**: regulation, deadline, "press 1 for full report"
- NOT a conversation — a push notification via voice
- If unanswered → automatic email fallback

### Step 3: REPORT (NEW — the key differentiator)
**Audience: Compliance officers, legal teams, and business leadership**

The email report must be:
- **Legally specific** — cite exact articles, not just "GDPR"
- **Business-friendly** — explain "supply chain" means software dependencies, not trucks
- **Actionable** — what exactly was violated, what exactly to do, who will audit this
- **Structured** for non-technical readers:

```
VIGIL COMPLIANCE REPORT
═══════════════════════

Company: TechStartup GmbH
Report date: 1 April 2026
Risk level: CRITICAL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINDING 1: AI Act — High-Risk AI System Not Registered
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Regulation:   EU AI Act (Regulation 2024/1689)
Article:      Article 6(1), Annex III
Deadline:     2 August 2026 (123 days remaining)
Severity:     CRITICAL

What was found:
  Your credit scoring system uses automated AI-based decision-making.
  Under the AI Act, this classifies as a "high-risk AI system" (Annex III,
  point 5b: "AI systems intended to be used to evaluate the creditworthiness
  of natural persons").

What this means for your business:
  Without registration, your company cannot legally deploy this system
  in the EU after the enforcement date. Fines up to EUR 35 million or
  7% of global annual turnover.

Who will audit this:
  National market surveillance authority (in Germany: BNetzA/BfDI).
  They can request conformity documentation at any time after Aug 2026.

What you must do:
  1. Conduct a conformity assessment per Article 43
  2. Register the system in the EU AI database (Article 49)
  3. Implement a risk management system (Article 9)
  4. Ensure human oversight mechanism (Article 14)

Estimated effort: 2-4 weeks with legal support
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[... additional findings ...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECOMMENDED NEXT STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Priority 1 (this week): Register AI systems — Art. 6 deadline approaching
Priority 2 (this month): Implement transparency disclosures — Art. 52
Priority 3 (ongoing): Monthly compliance monitoring via Vigil subscription

Want automated technical scanning? Install /vigil:
  → https://vigil-demo.streamlit.app (tab: /vigil Skill)
```

**Post-hackathon additions:**
- Auto-generate Jira/Linear tickets from findings
- Slack integration for real-time alerts
- PDF export of full legal report

### Step 4: PROTECT (for engineering teams)
- `/vigil` Claude Code skill scans the codebase
- Finds compliance issues at code level (PII in logs, missing encryption, etc.)
- Returns actionable fixes with file paths and line numbers
- This is the developer counterpart to Step 3's legal report

---

## Target Audience (clarified after feedback)

**Primary buyer: Head of Compliance / Legal at SMEs (10-500 employees)**
- They receive the WARN call and the REPORT email
- They decide to subscribe
- They forward the technical findings to engineering

**Secondary user: Engineering team lead / CTO**
- They receive forwarded findings + /vigil skill
- They run the code scan
- They implement the fixes

**The handoff:** Vigil bridges compliance → engineering automatically.

---

## Pricing (revised — based on actual costs)

### Cost per company (monthly):
| Component | Cost per company |
|---|---|
| Apify scraping (regulations, 10 pages/mo) | ~$0.05 |
| Claude fact extraction (20 chunks) | ~$0.02 |
| Claude risk matching (1 call) | ~$0.01 |
| Claude script generation (1 call) | ~$0.01 |
| Claude report generation (1 report) | ~$0.03 |
| Twilio voice call (1 min) | ~$0.10 |
| SendGrid email (1 email) | ~$0.001 |
| **Total marginal cost per company** | **~$0.22/month** |

### Pricing tiers:
| Tier | Price | What you get |
|---|---|---|
| **Free alert** | EUR 0 | 1 phone call + 1 email report (acquisition tool) |
| **Starter** | EUR 19/month | Monthly digest, deadline alerts, email reports |
| **Pro** | EUR 39/month | Everything + /vigil skill + priority monitoring |
| **Enterprise** | Custom | API access, Jira/Slack integration, dedicated support |

**Unit economics at Pro tier:**
- Revenue: EUR 39/month = ~$42/month
- Cost: ~$0.22/month
- Gross margin: **99.5%**
- CAC (Twilio call + email): ~$0.12

---

## Next 3 Steps Post-Hackathon (for pitch)

1. **Jira/Slack integration** — Auto-create tickets from compliance findings.
   Turn a report into a sprint. Compliance officers assign, engineers fix,
   Vigil tracks resolution. "From regulation to pull request in one click."

2. **Multi-jurisdiction expansion** — Add UK (FCA), Switzerland (FINMA),
   US (SOC2, CCPA). Same pipeline, different sources. Each country = new market.

3. **Compliance-as-Code SDK** — CI/CD integration. Run `/vigil` on every
   pull request. Block merges that introduce compliance violations.
   "Vigil becomes your compliance linter."

---

## Tech Stack (for pitch — keep it simple)

```
Apify ──── web scraping + OpenRouter LLM gateway
Claude ─── fact extraction, risk matching, script gen, code scanning
Twilio ─── automated voice calls
SendGrid ─ compliance report emails
Streamlit ─ subscriber dashboard
SQLite ──── company + outreach data
```

One sentence: "Apify scrapes the web, Claude thinks, Twilio calls, SendGrid emails."
