import json
import os
import requests
from typing import List
from datetime import datetime, timedelta
from apify_client import ApifyClient
from rag.prompt_templates import get_alert_prompt
from datetime import datetime


def generate_alerts(chunks: List[dict], company_profile: dict) -> List[dict]:
    """
    Analyzes chunks and generates urgent alerts —
    when the deadline is before the next weekly digest.
    """

    if not chunks:
        return []

    print("Scanning for urgent alerts...")

    # Method 1: Keyword-based detection (fast, without LLM)
    keyword_alerts = _detect_keyword_alerts(chunks, company_profile)

    # Method 2: LLM-based detection (more accurate)
    llm_alerts = _detect_llm_alerts(chunks, company_profile)

    # Join and deduplicate
    all_alerts = _merge_alerts(keyword_alerts, llm_alerts)

    # Sort by severity: critical > high > medium
    severity_order = {"critical": 0, "high": 1, "medium": 2}
    all_alerts.sort(key=lambda x: severity_order.get(x.get("severity", "medium"), 2))

    print(f"Found {len(all_alerts)} alerts ({len([a for a in all_alerts if a.get('severity') == 'critical'])} critical)")
    return all_alerts


def _detect_keyword_alerts(chunks: List[dict], company_profile: dict) -> List[dict]:
    """
    Fast alert detection via keyword matching.
    Looks for keywords suggesting urgent deadlines.
    """

    urgent_keywords = [
        "immediately", "urgent", "by end of", "no later than",
        "deadline", "expires", "expiry", "must comply by",
        "enforcement date", "entry into force", "takes effect",
        "penalty", "fine", "infringement", "non-compliance",
        "within 30 days", "within 7 days", "within 14 days",
    ]

    # Keywords suggesting dates in the next 90 days
    date_keywords = _get_upcoming_date_keywords()
    alerts = []
    today = datetime.now()

    for chunk in chunks:
        content = chunk.get("content", "").lower()
        title = chunk.get("title", "Unknown")
        url = chunk.get("url", "")

        matched_keywords = []
        for keyword in urgent_keywords:
            if keyword.lower() in content:
                matched_keywords.append(keyword)

        date_matched = any(dk in content for dk in date_keywords)

        if matched_keywords or date_matched:
            severity = _determine_severity(matched_keywords, content)
            deadline = _extract_deadline(content) or "Check source"

            # ← NOWE: pomiń jeśli deadline jest w przeszłości
            if deadline and deadline != "Check source":
                try:
                    import re
                    year_match = re.search(r'\b(20\d{2})\b', deadline)
                    if year_match:
                        year = int(year_match.group(1))
                        if year < today.year:
                            continue
                        elif year == today.year:
                            month_match = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-]', deadline)
                            if month_match:
                                month = int(month_match.group(1))
                                if month < today.month:
                                    continue
                except Exception:
                    pass

            alerts.append({
                "title": title,
                "deadline": deadline,
                "action_required": _extract_action(content, chunk),
                "severity": severity,
                "source_url": url,
                "source": chunk.get("source", ""),
                "detection_method": "keyword",
                "matched_keywords": matched_keywords[:3],
            })

    return alerts


def _detect_llm_alerts(chunks: List[dict], company_profile: dict) -> List[dict]:
    """
    LLM-based detekcja alertów — dokładniejsza ale wolniejsza.
    Używa top 5 chunków żeby oszczędzać kredyty.
    """

    try:
        from openai import OpenAI

        openai_client = OpenAI(
            base_url="https://openrouter.apify.actor/api/v1",
            api_key="no-key-required-but-must-not-be-empty",
            default_headers={
                "Authorization": f"Bearer {os.getenv('APIFY_TOKEN', '')}"
            }
        )

        top_chunks = chunks[:5]
        context = "\n\n".join([
            f"Title: {c.get('title', '')}\n{c.get('content', '')[:500]}"
            for c in top_chunks
        ])

        prompt = get_alert_prompt(company_profile, context)

        response = openai_client.chat.completions.create(
            model="anthropic/claude-3-haiku",
            max_tokens=800,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        raw_content = response.choices[0].message.content
        alerts = _parse_llm_alerts(raw_content)
        for alert in alerts:
            alert["detection_method"] = "llm"

        return alerts

    except Exception as e:
        print(f"⚠️ LLM alert detection failed: {e}")
        return []


def _parse_llm_alerts(raw_content: str) -> List[dict]:
    """
    Parses JSON from LLM response.
    Handles cases where LLM adds extra text.
    """

    try:
        # Try to parse directly as JSON first
        return json.loads(raw_content)
    except json.JSONDecodeError:
        pass

    # If direct parsing fails, try to extract JSON array from the text
    try:
        start = raw_content.find("[")
        end = raw_content.rfind("]") + 1
        if start != -1 and end > start:
            json_str = raw_content[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    print("Could not parse LLM alerts JSON")
    return []


def _merge_alerts(keyword_alerts: List[dict], llm_alerts: List[dict]) -> List[dict]:
    """
    Join and deduplicate alerts from both methods, prioritizing LLM alerts when there's a duplicate title.
    """

    merged = {alert["title"]: alert for alert in keyword_alerts}

    # LLM alerts can overwrite keyword alerts if they have the same title, as they are more accurate
    for alert in llm_alerts:
        merged[alert["title"]] = alert

    return list(merged.values())


def _determine_severity(matched_keywords: List[str], content: str) -> str:
    """
    Determines alert severity based on keywords and content.
    """

    critical_indicators = [
        "immediately", "within 7 days", "penalty", "fine",
        "infringement", "enforcement", "non-compliance"
    ]

    high_indicators = [
        "within 14 days", "within 30 days", "urgent",
        "deadline", "expires", "must comply"
    ]

    content_lower = content.lower()

    if any(ind in content_lower for ind in critical_indicators):
        return "critical"
    elif any(ind in content_lower for ind in high_indicators):
        return "high"
    elif matched_keywords:
        return "medium"

    return "medium"


def _extract_deadline(content: str) -> str | None:
    """
    Tries to extract a deadline date from the content.
    Simple heuristic — looks for date patterns.
    """

    import re

    # Wzorce dat: 2025-01-01, 01/01/2025, January 1, 2025
    patterns = [
        r"\d{4}-\d{2}-\d{2}",
        r"\d{2}/\d{2}/\d{4}",
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2},?\s+\d{4}",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(0)

    return None


def _extract_action(content: str, chunk: dict) -> str:
    """
    Generates a short description of the required action based on the content.
    """

    title = chunk.get("title", "this regulation")

    # Look for sentences containing action keywords in the first 10 sentences of the content
    sentences = content.split(".")
    action_keywords = ["must", "shall", "required", "obliged", "need to", "comply"]

    for sentence in sentences[:10]:
        sentence_lower = sentence.lower()
        if any(kw in sentence_lower for kw in action_keywords):
            cleaned = sentence.strip()
            if len(cleaned) > 20:
                return cleaned[:200]

    return f"Review and ensure compliance with {title}"


def _get_upcoming_date_keywords() -> List[str]:
    """
    Generates keywords for dates in the next 90 days.
    """

    keywords = []
    today = datetime.now()

    for days_ahead in range(90):
        future_date = today + timedelta(days=days_ahead)
        keywords.append(future_date.strftime("%Y-%m-%d"))
        keywords.append(future_date.strftime("%B %Y").lower())

    return keywords