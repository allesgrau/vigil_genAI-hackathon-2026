import os
import requests
import json
from typing import List
from apify_client import ApifyClient
from rag.prompt_templates import get_digest_prompt, get_plain_language_prompt


def generate_digest(chunks: List[dict], company_profile: dict, client: ApifyClient) -> dict:
    """
    Generates a weekly regulatory digest using LLM via OpenRouter.
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

    # Generate plain language summaries for top relevant chunks
    plain_summaries = []
    for chunk in chunks[:5]:
        # Dla faktów używamy "claim", dla chunków "content"
        text_to_summarize = chunk.get("claim") or chunk.get("content", "")
        title = chunk.get("title") or chunk.get("regulation", "Unknown")
        url = chunk.get("source_url") or chunk.get("url", "")
        
        plain_prompt = get_plain_language_prompt(
            text_to_summarize[:1000],
            company_profile
        )
        summary = _call_llm(plain_prompt, client, max_tokens=300)
        if summary:
            plain_summaries.append({
                "title": title,
                "url": url,
                "source": chunk.get("source", chunk.get("regulation", "")),
                "plain_summary": summary,
                "relevance_score": chunk.get("relevance_score", 0)
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
    """
    Builds a context string from chunks for the LLM.
    Each chunk is separated by a delimiter with metadata.
    """

    context_parts = []

    for i, chunk in enumerate(chunks):
        title = chunk.get("title", "Unknown Document")
        url = chunk.get("url", "")
        source = chunk.get("source", "")
        content = chunk.get("content", "")[:800]  # limit per chunk

        context_parts.append(
            f"--- Document {i+1}: {title} ---\n"
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
            f"## Weekly Digest for {company_profile.get('company_name', 'Your Company')}\n\n"
            "No regulatory updates found for your profile this week. "
            "This may indicate no changes in your monitored areas, "
            "or that the sources were temporarily unavailable.\n\n"
            "**Recommendation:** Check back next week or broaden your areas of concern."
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
        f"## Weekly Digest for {company_profile.get('company_name', 'Your Company')}\n\n"
        f"**Note:** AI summary unavailable. Showing raw regulatory updates.\n\n"
        f"### Recent Updates Found:\n\n" +
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