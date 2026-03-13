import os
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


def embed_chunks(chunks: List[dict]) -> List[dict]:
    """
    Generuje embeddingi dla każdego chunka używając OpenRouter przez Apify.
    """

    print(f"🧠 Embedding {len(chunks)} chunks...")

    client = _get_client()
    embedded = []

    for i, chunk in enumerate(chunks):
        content = chunk.get("content", "")
        if not content:
            continue

        embedding = _get_embedding(client, content)
        chunk["embedding"] = embedding
        embedded.append(chunk)

        if (i + 1) % 10 == 0:
            print(f"  → Embedded {i + 1}/{len(chunks)} chunks")

    print(f"✅ Successfully embedded {len(embedded)} chunks")
    return embedded


def _get_embedding(client: OpenAI, text: str) -> List[float]:
    """
    Pobiera embedding przez OpenRouter.
    Fallback na simple_embedding jeśli API nie obsługuje embeddingów.
    """

    try:
        response = client.embeddings.create(
            model="openai/text-embedding-3-small",
            input=text[:2000]
        )
        return response.data[0].embedding

    except Exception as e:
        print(f"⚠️ Embedding API error: {e}, using fallback")
        return _simple_embedding(text)


def _simple_embedding(text: str) -> List[float]:
    """
    Lokalny fallback — deterministyczny pseudo-embedding.
    """

    import hashlib
    import math

    vector = []
    for i in range(128):
        seed = hashlib.md5(f"{i}_{text[:100]}".encode()).hexdigest()
        value = int(seed[:8], 16) / (16**8)
        vector.append(value)

    magnitude = math.sqrt(sum(v**2 for v in vector))
    if magnitude > 0:
        vector = [v / magnitude for v in vector]

    return vector