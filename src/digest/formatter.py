from datetime import datetime
from typing import List


def format_output(digest: dict, alerts: List[dict], company_profile: dict) -> dict:
    """
    Creates a final Vigil output by combining the digest, alerts, and metadata into a cohesive, structured object.
    """

    now = datetime.now().isoformat()
    company = company_profile.get("company_name", "Your Company")
    industry = company_profile.get("industry", "")
    country = company_profile.get("country", "")

    # Format alerts to markdown for the report section
    formatted_alerts = _format_alerts(alerts)

    # Build plain language section
    plain_section = _format_plain_summaries(digest.get("plain_summaries", []))

    # Build final markdown report
    markdown_report = _build_markdown_report(
        company_profile=company_profile,
        digest_text=digest.get("digest_text", ""),
        formatted_alerts=formatted_alerts,
        plain_section=plain_section,
        sources_used=digest.get("sources_used", 0),
        generated_at=now,
    )

    # Build structured JSON output (for Apify Dataset and integrations)
    structured_output = {

        # Metadata
        "generated_at": now,
        "company_name": company,
        "industry": industry,
        "country": country,
        "areas_of_concern": company_profile.get("areas_of_concern", []),
        "sources_analyzed": digest.get("sources_used", 0),

        # Alerts
        "alerts_count": len(alerts),
        "critical_alerts": [a for a in alerts if a.get("severity") == "critical"],
        "high_alerts": [a for a in alerts if a.get("severity") == "high"],
        "medium_alerts": [a for a in alerts if a.get("severity") == "medium"],

        # Digest
        "digest_markdown": digest.get("digest_text", ""),
        "plain_summaries": digest.get("plain_summaries", []),

        # Full report
        "full_report_markdown": markdown_report,

        # Status
        "status": "success" if digest.get("digest_text") else "partial",
        "vigil_version": "0.1.0",
    }

    return structured_output


def _format_alerts(alerts: List[dict]) -> str:
    """
    Formats the list of alerts into a markdown string for the report section.
    """

    if not alerts:
        return "✅ No urgent alerts this week."

    lines = []

    severity_emoji = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
    }

    for alert in alerts:
        severity = alert.get("severity", "medium")
        emoji = severity_emoji.get(severity, "🟡")
        title = alert.get("title", "Unknown")
        deadline = alert.get("deadline", "Check source")
        action = alert.get("action_required", "Review required")
        url = alert.get("source_url", "")

        lines.append(
            f"{emoji} **{title}**\n"
            f"   - Deadline: `{deadline}`\n"
            f"   - Action: {action}\n"
            f"   - Source: {url}\n"
        )

    return "\n".join(lines)


def _format_plain_summaries(summaries: List[dict]) -> str:
    """
    Formats the plain language summaries into a markdown section for the report.
    """

    if not summaries:
        return "_No plain language summaries available._"

    lines = []

    for i, summary in enumerate(summaries, 1):
        title = summary.get("title", "Unknown")
        url = summary.get("url", "")
        text = summary.get("plain_summary", "")
        source = summary.get("source", "")

        lines.append(
            f"### {i}. {title}\n"
            f"**Source:** [{source}]({url})\n\n"
            f"{text}\n"
        )

    return "\n".join(lines)


def _build_markdown_report(
    company_profile: dict,
    digest_text: str,
    formatted_alerts: str,
    plain_section: str,
    sources_used: int,
    generated_at: str,
) -> str:
    """
    Builds the full markdown report — what the user will see.
    """

    company = company_profile.get("company_name", "Your Company")
    industry = company_profile.get("industry", "")
    country = company_profile.get("country", "")
    areas = ", ".join(company_profile.get("areas_of_concern", []))

    # Format the generated_at date for better readability
    try:
        dt = datetime.fromisoformat(generated_at)
        date_str = dt.strftime("%B %d, %Y at %H:%M UTC")
    except Exception:
        date_str = generated_at

    report = f"""# 🛡️ Vigil — Weekly Regulatory Digest

**Company:** {company}
**Industry:** {industry} | **Country:** {country}
**Monitoring:** {areas}
**Generated:** {date_str}
**Sources analyzed:** {sources_used}

---

## 🚨 ALERTS

{formatted_alerts}

---

## 📋 WEEKLY DIGEST

{digest_text}

---

## 🗣️ PLAIN LANGUAGE SUMMARIES
_What does this actually mean for your business?_

{plain_section}

---

*Vigil is an AI-powered regulatory intelligence tool built for European SMEs.*
*Always consult a qualified legal professional for compliance decisions.*
*Built at GenAI Zurich Hackathon 2026.*
"""

    return report