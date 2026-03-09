from typing import List


def chunk_documents(documents: List[dict], chunk_size: int = 500, overlap: int = 50) -> List[dict]:
    """
    Divides documents into smaller chunks based on the specified chunk size and overlap.
    """
    
    chunks = []
    
    for doc in documents:
        content = doc.get("content", "")
        
        if not content:
            continue
        
        # Divide content into paragraphs
        paragraphs = content.split("\n\n")
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # If adding the paragraph doesn't exceed chunk_size — add it
            if len(current_chunk) + len(paragraph) <= chunk_size:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
            
            else:
                # Save the current chunk if it's not empty
                if current_chunk:
                    chunks.append(_make_chunk(doc, current_chunk, chunk_index))
                    chunk_index += 1
                
                # Start a new chunk with the current paragraph
                words = current_chunk.split()
                overlap_text = " ".join(words[-overlap:]) if len(words) > overlap else current_chunk
                current_chunk = overlap_text + "\n\n" + paragraph
        
        # Save the last chunk
        if current_chunk:
            chunks.append(_make_chunk(doc, current_chunk, chunk_index))
    
    print(f"Created {len(chunks)} chunks from {len(documents)} documents")
    return chunks


def _make_chunk(doc: dict, content: str, index: int) -> dict:
    """
    Creates a structured chunk object with metadata.
    """
    
    return {
        "chunk_id": f"{doc.get('url', 'unknown')}#{index}",
        "content": content,
        "url": doc.get("url", ""),
        "title": doc.get("title", ""),
        "source": doc.get("source", ""),
        "crawled_at": doc.get("crawled_at", ""),
        "chunk_index": index,
    }