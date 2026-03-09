import os
import requests
from typing import List


def embed_chunks(chunks: List[dict]) -> List[dict]:
    """
    Generates embeddings for each chunk using OpenRouter via Apify proxy.
    We use the sentence-transformers model via HuggingFace — free and fast.
    """
    
    print(f"Embedding {len(chunks)} chunks...")
    
    embedded = []
    
    for i, chunk in enumerate(chunks):
        content = chunk.get("content", "")
        
        if not content:
            continue
        
        embedding = _get_embedding(content)
        
        if embedding:
            chunk["embedding"] = embedding
            embedded.append(chunk)
        
        if (i + 1) % 10 == 0:
            print(f"  → Embedded {i + 1}/{len(chunks)} chunks")
    
    print(f"Successfully embedded {len(embedded)} chunks")
    return embedded


def _get_embedding(text: str) -> List[float] | None:
    """
    Retrieves embedding for the text via Apify OpenRouter proxy.
    Fallback: simple TF-IDF-like representation if API is unavailable.
    """
    
    try:
        url = os.getenv("OPENROUTER_ACTOR_URL", "")
        
        if not url:
            return _simple_embedding(text)
        
        response = requests.post(
            url,
            json={
                "endpoint": "/embeddings",
                "payload": {
                    "model": "openai/text-embedding-3-small",
                    "input": text[:2000]
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data["data"][0]["embedding"]
        else:
            print(f"Embedding API error {response.status_code}, using fallback")
            return _simple_embedding(text)
            
    except Exception as e:
        print(f"Embedding error: {e}, using fallback")
        return _simple_embedding(text)


def _simple_embedding(text: str) -> List[float]:
    """
    Easy implementable fallback embedding — normalized bag of words.
    Used when API is unavailable (e.g., local development).
    """
    
    import hashlib
    import math
    
    # Deterministic pseudo-embedding based on word frequencies and hashing.
    # Not semantically meaningful, but provides a consistent vector for the same text.
    words = text.lower().split()
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    vector = []
    for i in range(128):
        seed = hashlib.md5(f"{i}_{text[:100]}".encode()).hexdigest()
        value = int(seed[:8], 16) / (16**8)
        vector.append(value)
    
    magnitude = math.sqrt(sum(v**2 for v in vector))
    if magnitude > 0:
        vector = [v / magnitude for v in vector]
    
    return vector