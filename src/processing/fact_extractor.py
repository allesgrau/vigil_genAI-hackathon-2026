import os
import json
from typing import List
from openai import OpenAI


def _get_client() -> OpenAI:
    return OpenAI(
        base_url=os.getenv("OPENROUTER_ACTOR_URL", "https://openrouter.apify.actor/api/v1"),
        api_key="no-key-required-but-must-not-be-empty",
        default_headers={
            "Authorization": f"Bearer {os.getenv('APIFY_TOKEN', '')}"
        }
    )


def extract_facts(chunks: List[dict], company_profile: dict) -> List[dict]:

    if not chunks:
        return []

    client = _get_client()
    all_facts = []
    areas = company_profile.get("areas_of_concern", [])

    # W test_mode przetwarzaj tylko pierwsze 20 chunków!
    test_mode = company_profile.get("test_mode", False)
    if test_mode:
        chunks = chunks[:20]
        print(f"⚡ TEST MODE: limiting to {len(chunks)} chunks")

    print(f"🔬 Extracting facts from {len(chunks)} chunks...")

    # Przetwarzaj po 5 chunków naraz żeby oszczędzać kredyty
    batch_size = 5
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batch_text = "\n\n---\n\n".join([
            f"SOURCE: {c.get('url', '')}\nTITLE: {c.get('title', '')}\n{c.get('content', '')[:800]}"
            for c in batch
        ])

        facts = _extract_facts_from_batch(client, batch_text, areas, batch)
        all_facts.extend(facts)

        print(f"  → Extracted facts from chunks {i+1}-{min(i+batch_size, len(chunks))}/{len(chunks)}")

    print(f"✅ Extracted {len(all_facts)} facts total")
    return all_facts


def _extract_facts_from_batch(client: OpenAI, batch_text: str, areas: List[str], batch_chunks: List[dict] = None) -> List[dict]:
    """
    Ekstrahuje fakty z batcha chunków przez LLM.
    """

    areas_str = ", ".join(areas)

    prompt = f"""You are a regulatory intelligence analyst. Extract discrete, verifiable facts from the following regulatory documents.

Focus on facts relevant to: {areas_str}

For each fact, output a JSON object. Return ONLY a JSON array, no other text.

Each fact must have:
- "claim": one clear, specific factual statement (max 2 sentences)
- "regulation": regulation name (e.g. "GDPR", "AI Act", "PSD2")  
- "article": article/section reference if available, else null
- "applies_to": list of who this applies to (e.g. ["fintech companies", "data processors"])
- "deadline": specific deadline if mentioned, else null
- "action_required": what companies must do, else null
- "severity": "critical", "high", "medium", or "low"
- "source_url": URL of the source document
- "keywords": list of 3-5 relevant keywords

DOCUMENTS:
{batch_text}

Return ONLY the JSON array. Example format:
[
  {{
    "claim": "Organizations must report data breaches to supervisory authorities within 72 hours of becoming aware.",
    "regulation": "GDPR",
    "article": "Article 33",
    "applies_to": ["all data controllers"],
    "deadline": "72 hours after breach discovery",
    "action_required": "Implement breach detection and reporting procedures",
    "severity": "critical",
    "source_url": "https://gdpr.eu/...",
    "keywords": ["data breach", "notification", "72 hours", "supervisory authority"]
  }}
]"""

    try:
        response = client.chat.completions.create(
            model="anthropic/claude-3-haiku",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.choices[0].message.content

        # Parsuj JSON
        try:
            facts = json.loads(raw)
        except json.JSONDecodeError:
            # Wyciągnij JSON z tekstu
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start != -1 and end > start:
                facts = json.loads(raw[start:end])
            else:
                return []

        # Dodaj fact_id do każdego faktu
        result = []
        for i, fact in enumerate(facts):
            if isinstance(fact, dict) and fact.get("claim"):
                fact["fact_id"] = f"fact_{hash(fact['claim'])}"
                fact["embedding"] = None
                # Jeśli LLM nie podał source_url, weź z pierwszego chunka w batchu
                if not fact.get("source_url") and batch_chunks:
                    fact["source_url"] = batch_chunks[0].get("url", "")
                    fact["title"] = batch_chunks[0].get("title", "Unknown")
                result.append(fact)

        return result

    except Exception as e:
        print(f"⚠️ Fact extraction failed: {e}")
        return []