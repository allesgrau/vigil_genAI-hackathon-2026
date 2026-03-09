import math
from typing import List


class VectorStore:
    """
    In-memory vector store for the RAG pipeline.
    Stores chunks with embeddings and allows for similarity search.
    """

    def __init__(self):
        self.chunks = []
        print("Vector store initialized")

    def add_chunks(self, chunks: List[dict]) -> None:
        """
        Adds chunks with embeddings to the store.
        """
        added = 0
        for chunk in chunks:
            if chunk.get("embedding"):
                self.chunks.append(chunk)
                added += 1

        print(f"Added {added} chunks to vector store (total: {len(self.chunks)})")

    def similarity_search(self, query_embedding: List[float], top_k: int = 5) -> List[dict]:
        """
        Finds the top_k most similar chunks to the query.
        Uses cosine similarity.
        """

        if not self.chunks:
            print("Vector store is empty")
            return []

        if not query_embedding:
            print("No query embedding provided")
            return []

        # Calculate similarity scores for each chunk
        scored = []
        for chunk in self.chunks:
            chunk_embedding = chunk.get("embedding", [])
            if chunk_embedding:
                score = _cosine_similarity(query_embedding, chunk_embedding)
                scored.append((score, chunk))

        # Sort by score and return top_k results
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [chunk for score, chunk in scored[:top_k]]

        return results

    def keyword_search(self, keywords: List[str], top_k: int = 5) -> List[dict]:
        """
        Fallback search based on keyword matching in content and title.
        """

        scored = []
        for chunk in self.chunks:
            content = chunk.get("content", "").lower()
            title = chunk.get("title", "").lower()
            score = 0

            for keyword in keywords:
                kw = keyword.lower()
                score += content.count(kw) * 1.0
                score += title.count(kw) * 2.0

            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [chunk for score, chunk in scored[:top_k]]

    def __len__(self):
        return len(self.chunks)


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Calculates cosine similarity between two vectors.
    """

    if len(vec_a) != len(vec_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    magnitude_a = math.sqrt(sum(a ** 2 for a in vec_a))
    magnitude_b = math.sqrt(sum(b ** 2 for b in vec_b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)