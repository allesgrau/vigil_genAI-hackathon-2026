import os
import requests
import json
from typing import List
from apify_client import ApifyClient
from rag.prompt_templates import get_digest_prompt, get_plain_language_prompt

from datetime import datetime
import re


def generate_digest(chunks: List[dict], company_profile: dict, client: ApifyClient) -> dict:
    """
    Generates a monthly regulatory digest using LLM via OpenRouter.
    """

    if not chunks:
        return _empty_digest(company_profile)

    # Build context from retrieved chunks
    context = _build_context(chunks)
    print(f"Building digest from {len(chunks)} chunks ({len(context)} chars of context)")

    # Generate digest through LLM
    prompt = get_digest_prompt(company_profile, context)
    digest_text = _call_llm(prompt, client, max_tokens=2000)

    if not digest_text:
        print("LLM returned empty digest, using fallback")
        return _fallback_digest(chunks, company_profile)
    
    # Post-process: delete deadlines that are already past (if any)
    if digest_text and "UPCOMING DEADLINES" in digest_text:
        today = datetime.now()
        lines = digest_text.split('\n')
        filtered_lines = []
        for line in lines:
            year_match = re.search(r'\b(20\d{2})\b', line)
            if year_match:
                year = int(year_match.group(1))
                if year < today.year:
                    continue
                elif year == today.year:
                    month_match = re.search(r'\b(\d{1,2})\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)', line, re.IGNORECASE)
                    pass
            filtered_lines.append(line)
        digest_text = '\n'.join(filtered_lines)

    # Generate plain language summary from the digest itself — not raw facts
    plain_summaries = []

    if digest_text:
        # Extract "What changed" section from digest
        what_changed_section = digest_text
        if "## MONTHLY DIGEST" in digest_text:
            start = digest_text.find("## MONTHLY DIGEST")
            end = digest_text.find("## STRATEGIC INSIGHTS")
            if end > start:
                what_changed_section = digest_text[start:end]

        plain_prompt = get_plain_language_prompt(
            what_changed_section[:2000],
            company_profile,
            mode="change"
        )
        summary = _call_llm(plain_prompt, client, max_tokens=600)
        if summary:
            plain_summaries.append({
                "title": "This month's key changes",
                "url": "",
                "source": "Vigil Analysis",
                "plain_summary": summary,
                "relevance_score": 1.0
            })

    print("Digest generated successfully")

    return {
        "digest_text": digest_text,
        "plain_summaries": plain_summaries,
        "sources_used": len(chunks),
        "company": company_profile.get("company_name", ""),
        "industry": company_profile.get("industry", ""),
        "country": company_profile.get("country", ""),
    }


def _call_llm(prompt: str, client: ApifyClient, max_tokens: int = 1000) -> str | None:
    try:
        from openai import OpenAI
        
        openai_client = OpenAI(
            base_url="https://openrouter.apify.actor/api/v1",
            api_key="no-key-required-but-must-not-be-empty",
            default_headers={
                "Authorization": f"Bearer {os.getenv('APIFY_TOKEN', '')}"
            }
        )

        response = openai_client.chat.completions.create(
            model="anthropic/claude-3-haiku",
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"⚠️ LLM call failed: {e}")
        return None


def _build_context(chunks: List[dict]) -> str:
    context_parts = []

    for i, chunk in enumerate(chunks):
        # Handling both new and old chunk formats for backward compatibility
        if chunk.get("claim"):
            # It's a fact
            content = f"{chunk.get('claim', '')}"
            if chunk.get("action_required"):
                content += f"\nAction required: {chunk.get('action_required')}"
            if chunk.get("deadline"):
                content += f"\nDeadline: {chunk.get('deadline')}"
            title = f"{chunk.get('regulation', 'Unknown')} — {chunk.get('article', '')}"
            url = chunk.get("source_url", "")
            source = chunk.get("regulation", "")
        else:
            # It's a raw chunk without structured fact fields
            content = chunk.get("content", "")[:800]
            title = chunk.get("title", "Unknown Document")
            url = chunk.get("url", "")
            source = chunk.get("source", "")

        context_parts.append(
            f"--- Fact {i+1}: {title} ---\n"
            f"Source: {source} | URL: {url}\n"
            f"{content}\n"
        )

    return "\n".join(context_parts)


def _empty_digest(company_profile: dict) -> dict:
    """
    Returns an empty digest when no documents are found.
    """

    return {
        "digest_text": (
            f"## Monthly digest for {company_profile.get('company_name', 'Your Company')}\n\n"
            "No regulatory updates found for your profile this month. "
            "This may indicate no changes in your monitored areas, "
            "or that the sources were temporarily unavailable.\n\n"
            "**Recommendation:** Check back next month or broaden your areas of concern."
        ),
        "plain_summaries": [],
        "sources_used": 0,
        "company": company_profile.get("company_name", ""),
        "industry": company_profile.get("industry", ""),
        "country": company_profile.get("country", ""),
    }


def _fallback_digest(chunks: List[dict], company_profile: dict) -> dict:
    """
    Simple fallback digest when LLM is unavailable.
    Generates a basic summary without AI.
    """

    summaries = []
    for chunk in chunks[:5]:
        summaries.append(
            f"- **{chunk.get('title', 'Unknown')}** "
            f"([source]({chunk.get('url', '#')}))\n"
            f"  {chunk.get('content', '')[:200]}..."
        )

    digest_text = (
        f"## Monthly digest for {company_profile.get('company_name', 'Your Company')}\n\n"
        f"**Note:** AI summary unavailable. Showing raw regulatory updates.\n\n"
        f"### Recent updates found:\n\n" +
        "\n".join(summaries)
    )

    return {
        "digest_text": digest_text,
        "plain_summaries": [],
        "sources_used": len(chunks),
        "company": company_profile.get("company_name", ""),
        "industry": company_profile.get("industry", ""),
        "country": company_profile.get("country", ""),
    }