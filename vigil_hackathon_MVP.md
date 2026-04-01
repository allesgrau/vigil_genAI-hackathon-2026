# Vigil — Hackathon Schedule (1-2 April 2026)

> Plan dopasowany do grafiku hackathonu.
> Referencja: pełny action plan w `vigil_action_plan.md` — ten dokument to wersja z timingiem i mockupami.

---

## Zasada nadrzedna

**Na hackathonie budujesz DEMO, nie produkt.** Wszystko, co nie jest widoczne na demo, może być zmockupowane. Demo ma 3 momenty, które MUSZĄ działać na żywo:

1. Telefon dzwoni (Twilio Voice)
2. `/vigil` skanuje repo (Claude Skill)
3. Landing page / Streamlit wygląda profesjonalnie

Cała reszta to mock data, hardcoded JSON, i seedowany SQLite.

---

## Co jest mockupowane (nie implementowane na hackathonie)

| Element | Mock | Czemu |
|---|---|---|
| Scraping rejestrów firm | 1 firma hardcoded w SQLite (`demo/seed_db.py`) | Rejestry trudne do scrapowania, na demo i tak 1 firma |
| Company-risk matching | 1 alert hardcoded w JSON (`demo/mock_alert.json`) | Na demo mówisz "Vigil found this company" — nikt nie weryfikuje matchera |
| Subscription flow | Przycisk w emailu linkuje do Streamlit app | Brak Stripe, brak payment — na demo nie potrzebne |
| Subscriber monitoring | Nie istnieje — wspomniany słownie | Miesięczne digesty to feature post-hackathonowy |

---

## Noc przed hackathonem (31 marca, hotel w Zurychu)

**Phase 0.3 — Pre-scrape regulatory data**

| Czas | Co | Ref | Status |
|---|---|---|---|
| Wieczór | Odpal Vigil pipeline w full mode dla fintech/DE | `vigil_action_plan.md` Phase 0.3 | ✅ |
| | Zapisz fakty do `demo/pre_scraped_facts.json` | | ✅ |
| | Przygotuj `demo/mock_alert.json` z jednym realnym alertem z tych faktów | | ✅ |
| | Zaloguj się na v0.dev (GitHub) | Phase 0.1 | ✅ |

```json
// demo/mock_alert.json — przykład
{
  "regulation": "AI Act",
  "article": "Art. 52",
  "days_remaining": 28,
  "action_required": "Register AI systems used in credit scoring and implement transparency disclosures",
  "severity": "critical"
}
```

---

## Dzień 1 — 1 kwietnia

### 09:00–10:30 — Fundament (1.5h)

Cel: FastAPI server odpowiada na webhook, telefon dzwoni.

| Czas | Zadanie | Ref w action plan | Mockup? | Status |
|---|---|---|---|---|
| 09:00 | **1.1 SQLite database** — `src/database/db.py` + `demo/seed_db.py` z Twoim numerem i mailem | Phase 1.1 | Seed data = mock | ✅ |
| 09:30 | **1.2 Call script generator** — `src/outreach/script_generator.py`, test standalone | Phase 1.2 | — | ✅ |
| 10:00 | **1.3 FastAPI webhook server** — `server.py` + `src/outreach/webhook_server.py`, tylko `/webhook/voice` + `/webhook/gather-response` | Phase 1.3 | — | ✅ |
| 10:20 | Odpal `uvicorn` + `ngrok`, zaktualizuj `SERVER_URL` w `.env` | Phase 1.3 | — | ✅ |

**Checkpoint 10:30:** `curl -X POST localhost:8000/webhook/voice?company_id=test-001` zwraca TwiML XML. ✅

### 10:30–11:30 — Telefon dzwoni! (1h)

Cel: Twój telefon dzwoni z compliance briefingiem.

| Czas | Zadanie | Ref | Mockup? | Status |
|---|---|---|---|---|
| 10:30 | **1.4 Twilio Voice call** — `src/outreach/voice_agent.py`, zadzwoń do siebie | Phase 1.4 | — | ✅ |
| 11:00 | Debug + iteracja (voice, tempo, treść skryptu) | Phase 1.4 | — | ✅ |
| 11:15 | **1.5 SendGrid email** — `src/outreach/email_sender.py`, wyślij testowy email do siebie | Phase 1.5 | — | ✅ |

**Checkpoint 11:30:** Telefon dzwoni. Słyszysz briefing. Naciskasz 1. Email przychodzi. ✅

### 11:30–12:30 — Skill + demo repo (1h)

Cel: `/vigil` działa i znajduje bugi compliance.

| Czas | Zadanie | Ref | Mockup? | Status |
|---|---|---|---|---|
| 11:30 | **2.1 Write `/vigil` skill** — `skill/vigil-compliance.md` | Phase 2.1 | — | ✅ |
| 11:45 | **2.2 Install skill** na swoim komputerze | Phase 2.2 | — | ✅ |
| 11:50 | **2.3 Create demo repo** — `demo/sample_app/` z plantowanymi bugami | Phase 2.3 | Mock app | ✅ |
| 12:10 | Test: `cd demo/sample_app` → `/vigil` → czy raport wygląda dobrze? | Phase 2.3 | — | ✅ |
| 12:20 | Iteracja na prompcie skilla jeśli trzeba | — | — | ✅ |

**Checkpoint 12:30:** `/vigil` w demo repo zwraca raport z min. 3 findings. ✅

### 12:30–13:00 — Przygotowanie do mentoring pitch (30min)

Cel: Mieć co pokazać jury o 13:00.

| Czas | Zadanie |
|---|---|
| 12:30 | Przygotuj 4-minutowy pitch: problem → FIND (mock) → WARN (live call) → PROTECT (live /vigil) → business model |
| 12:40 | Dry run: odpal telefon + /vigil, upewnij się że działa |
| 12:50 | Otwórz Streamlit app w przeglądarce jako backup "subscriber platform" |

### 13:00–~15:00 — Science Fair Mentoring

**Co pokazujesz jury (4 minuty):**

1. **(30s) Problem + vision:** "EU SMEs spend billions on lawyers. Vigil finds them, warns them, protects them."
2. **(15s) FIND:** "Vigil scraped business registries and found TechStartup GmbH — fintech in Berlin, AI Act deadline in 28 days." ← pokaż terminal/Streamlit z info o firmie (mock, ale wygląda real)
3. **(60s) WARN — live:** Triggerujesz call. Telefon dzwoni. Odbierasz na głośniku. Jury słyszy briefing. "Press 1 for a full report." Naciskasz. "Check your email." Pokazujesz email na ekranie.
4. **(60s) PROTECT — live:** Otwierasz Claude Code w `demo/sample_app/`. Wpisujesz `/vigil`. Raport się generuje. Pokazujesz findings.
5. **(15s) Business model:** "First alert free. 49 EUR/month. CAC = 50 cents."

**Zbieraj feedback.** Notuj WSZYSTKO co jury mówi. To definiuje priorytet na resztę hackathonu.

### 15:00–18:00+ — Polerowanie na podstawie feedbacku (3h+)

Priorytet zależy od feedbacku jury. Ale defaultowy plan:

| Priorytet | Zadanie | Ref | Czas |
|---|---|---|---|
| 1 | Fix cokolwiek co jury skrytykował | — | ? |
| 2 | **Landing page** — v0.dev → `landing/index.html` | Phase 4.1-4.2 | 1h |
| 3 | **Report viewer** — `landing/report.html`, strona na którą linkuje email | Post-hackathon → MVP | 30min |
| 4 | **Wire up cascade** — `/webhook/call-status` auto-triggery email po nieodebraniu | Phase 1.6 | 30min | ✅ |
| 5 | **Orchestrator** — `src/outreach/orchestrator.py`, jeden przycisk odpala cały flow | Phase 1.6 | 30min | ✅ |
| 6 | Nagraj backup video całego demo (na wypadek awarii) | Phase 5.3 | 20min |

**Checkpoint koniec dnia 1:** Masz działający call + email + skill + landing page. Demo gotowe w 80%.

---

## Dzień 2 — 2 kwietnia

### 09:00–11:00 — Polish & deliverables (2h)

| Czas | Zadanie |
|---|---|
| 09:00 | **2-minutowy demo video** — nagraj screen recording z narracją: problem → call → /vigil → business model |
| 09:30 | **1-slide PDF** (16:9) — "Vigil: Find. Warn. Protect." + 3-step diagram + business model |
| 09:45 | **One-pager** — update Devpost project z nowym opisem (Find→Warn→Protect) |
| 10:00 | **README.md update** — dodaj nowe features, zaktualizuj architecture diagram |
| 10:30 | **Landing page deploy** — GitHub Pages jeśli jeszcze nie |
| 10:45 | **Team photo** |

### 11:00–12:30 — Stretch goals LUB safety (1.5h)

**Jeśli wszystko działa stabilnie — stretch goals:**

| Zadanie | Ref | Czas |
|---|---|---|
| **Registry scraper** (KRS API lub Companies House) | Phase 3.1 | 45min |
| **Industry classifier** (NACE mapping) | Phase 3.2 | 15min |
| **Risk matcher** (basic: industry + country filter na pre-scraped facts) | Phase 3.3 | 30min |

**Jeśli coś jest niestabilne — safety:**

| Zadanie | Czas |
|---|---|
| Nagraj backup video z działającym demo | 20min |
| Przygotuj screenshots jako fallback | 10min |
| Rehearse pitch 3x | 30min |
| Fix bugs | reszta |

### 12:30–13:00 — Final prep

| Czas | Zadanie |
|---|---|
| 12:30 | Final dry run demo (live call + /vigil) |
| 12:40 | Upewnij się, że: repo jest public, video uploaded, Devpost updated, slide ready |
| 12:50 | Oddech. |

### 13:00 — Submission

Deliverables:
- [x] GitHub repo (public)
- [x] Working prototype (call + skill + Streamlit)
- [x] One-pager (Devpost)
- [x] 2-min video
- [x] Landing page
- [x] 1 slide PDF (16:9)
- [x] Team photo

---

## Podsumowanie: co kiedy jest gotowe

```
                        31 marca    1 kwietnia   1 kwietnia    2 kwietnia   2 kwietnia
                        (wieczór)   (09-13:00)   (15-18:00)   (09-11:00)   (11-13:00)
                        ─────────   ──────────   ──────────   ──────────   ──────────
Pre-scraped data        ████████
SQLite + seed data                  ████
Script generator                    ████
FastAPI + webhook                   ████████
Twilio Voice call                   ████████
SendGrid email                      ████
/vigil skill                        ████████
Demo sample app                     ████
                                                 ▼ FEEDBACK ▼
Landing page (v0.dev)                            ████████
Cascade wiring                                   ████
Orchestrator                                     ████
Backup video                                     ████
                                                              ▼ DELIVERABLES ▼
Demo video (2min)                                             ████
1-slide PDF                                                   ████
One-pager update                                              ████
README update                                                 ████
Registry scraper                                                           ████████
Risk matcher                                                               ████████
Final rehearsal                                                            ████
```

---

## Backup plan

| Jeśli... | To... |
|---|---|
| Twilio Voice nie działa (sieć, trial limit) | Pokaż pre-recorded video z działającym callem |
| ngrok jest niestabilny | Deploy webhook server na Railway (free tier, 5 min) |
| `/vigil` jest za wolny na demo | Pokaż screenshot outputu, wytłumacz na żywo |
| Internet pada | Cały demo z pre-recorded video + local landing page HTML |
| Jury mówi "fajne, ale gdzie jest FIND?" | "We hardcoded one company for demo. In production, we scrape registries — here's the architecture." Pokaż `vigil_architecture.md` |
| Jury pyta o dodatkowe kanały kontaktu | "In production, we'd add WhatsApp Business API and local EU numbers for higher answer rates." |
