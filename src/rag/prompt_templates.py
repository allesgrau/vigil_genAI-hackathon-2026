def get_digest_prompt(company_profile: dict, context: str) -> str:
    from datetime import datetime, timedelta
    today = datetime.now()
    today_str = today.strftime("%B %d, %Y")
    one_month_ago = (today - timedelta(days=30)).strftime("%B %d, %Y")

    company = company_profile.get("company_name", "the company")
    industry = company_profile.get("industry", "general")
    country = company_profile.get("country", "EU")
    areas = ", ".join(company_profile.get("areas_of_concern", []))

    return f"""You are Vigil, an expert regulatory intelligence assistant for European SMEs.
Today's date is {today_str}.

CRITICAL TIME RULES:
- Only include regulatory developments published or effective AFTER {one_month_ago}
- Ignore anything older than 30 days — it is NOT news
- Only flag deadlines that are in the FUTURE (after {today_str})
- Never return deadlines from the past
- If a document contains no recent changes (post {one_month_ago}), skip it entirely

COMPANY PROFILE:
- Company: {company}
- Industry: {industry}
- Country: {country}
- Regulatory areas of concern: {areas}

RECENT REGULATORY DOCUMENTS:
{context}

YOUR TASK:
Generate a monthly regulatory digest. Structure your response as follows:

## URGENT – Action required this month
List regulations with imminent deadlines or immediate action required.
If none, write "Nothing urgent this month."

## MONTHLY DIGEST – what changed?
ONLY include changes from the last 30 days (after {one_month_ago}).
For each relevant recent change:
- **What changed**: Plain language summary (max 2 sentences)
- **Why it matters for you**: Specific impact for this company
- **What to do**: Concrete next step
- **Source**: URL

If no recent changes found, write "No new regulatory changes in the past 30 days."

## STRATEGIC INSIGHTS
2-3 forward-looking observations based on recent developments.

## UPCOMING DEADLINES
Only list deadlines after {today_str} and within the next 90 days.

IMPORTANT RULES:
- Write in plain, jargon-free English
- Be specific to this company's profile
- Never fabricate deadlines – only use what's in the documents
- Keep each section concise and scannable
"""


def get_alert_prompt(company_profile: dict, context: str) -> str:
    from datetime import datetime
    today = datetime.now().strftime("%B %d, %Y")

    company = company_profile.get("company_name", "the company")
    industry = company_profile.get("industry", "general")
    country = company_profile.get("country", "EU")

    return f"""You are Vigil, a regulatory compliance assistant.
Today's date is {today}. Only flag deadlines that are in the FUTURE relative to today.
Never return deadlines from the past (before {today}).
Analyze the following regulatory documents and identify URGENT items only.

COMPANY PROFILE:
- Company: {company}
- Industry: {industry}
- Country: {country}

REGULATORY DOCUMENTS:
{context}

YOUR TASK:
Identify regulations that require action within the next 30 days from today ({today}).
For each urgent item output ONLY a JSON array like this:

[
  {{
    "title": "Short title of the regulation",
    "deadline": "YYYY-MM-DD or 'Immediate'",
    "action_required": "One sentence — exactly what the company must do",
    "severity": "critical" or "high" or "medium",
    "source_url": "URL of the regulation"
  }}
]

If nothing is urgent, return an empty array: []
Return ONLY the JSON array, no other text.
"""


def get_plain_language_prompt(regulation_text: str, company_profile: dict, mode: str = "change") -> str:
    from datetime import datetime, timedelta
    today = datetime.now()
    today_str = today.strftime("%B %d, %Y")
    one_month_ago = (today - timedelta(days=30)).strftime("%B %d, %Y")
    industry = company_profile.get("industry", "general")
    country = company_profile.get("country", "EU")

    if mode == "explainer":
        return f"""You are a regulatory educator. Today is {today_str}.
Explain this regulation in plain English for a non-lawyer business owner
at a {industry} company based in {country}.

REGULATION TEXT:
{regulation_text}

Write 3 sentences:
1. What this regulation is and what it covers (broad overview)
2. Why it matters for a {industry} business in {country}
3. The single most important thing to do to stay compliant

Use simple words. No jargon. Write as if explaining to a smart friend.
"""

    return f"""You are a regulatory translator. Today is {today_str}.
Your job is to explain a SPECIFIC RECENT REGULATORY CHANGE in plain language.
Only describe changes that occurred after {one_month_ago}.

CONTEXT: This is for a {industry} company based in {country}.

REGULATORY CONTENT:
{regulation_text}

Explain in 3 sentences:
1. What SPECIFICALLY changed recently (be concrete — if nothing changed in the last 30 days, say so)
2. What it means specifically for a {industry} business in {country} RIGHT NOW
3. What ONE concrete action the company should take

Rules:
- Focus ONLY on recent changes (post {one_month_ago}), not historical background
- Never say "The GDPR is a law that..." — assume they know what GDPR is
- If the content describes old rules with no recent updates, say "No recent changes — this regulation has been stable"
- Use simple words, no legal jargon
"""