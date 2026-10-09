import os
import math
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()
logger = logging.getLogger(__name__)

# Primary supported embedding model in installed google-genai SDK
PRIMARY_EMBEDDING_MODEL = "gemini-embedding-001"
FALLBACK_EMBEDDING_MODELS = ["gemini-embedding-001", "gemini-embedding-2-preview", "text-embedding-004"]

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)

def chunk_evidence_items(organic_results: List[Dict[str, Any]], chunk_size: int = 250) -> List[Dict[str, Any]]:
    """
    Chunks retrieved search evidence items into passage units while preserving source URLs and metadata.
    """
    chunks = []
    chunk_counter = 1
    
    for item in organic_results:
        title = item.get("title", "Untitled Result")
        url = item.get("link", "#")
        snippet = item.get("snippet", "No snippet available.")
        source = item.get("source", "")
        query_origin = item.get("query_origin", "")
        
        # If snippet is short, keep as 1 chunk
        if len(snippet) <= chunk_size:
            chunks.append({
                "chunk_id": f"C{chunk_counter}",
                "title": title,
                "link": url,
                "snippet": snippet,
                "source": source,
                "query_origin": query_origin,
                "verified_full_page": False
            })
            chunk_counter += 1
        else:
            # Split longer text into windowed passages
            words = snippet.split()
            current_passage = []
            current_len = 0
            
            for w in words:
                current_passage.append(w)
                current_len += len(w) + 1
                if current_len >= chunk_size:
                    p_text = " ".join(current_passage)
                    chunks.append({
                        "chunk_id": f"C{chunk_counter}",
                        "title": title,
                        "link": url,
                        "snippet": p_text,
                        "source": source,
                        "query_origin": query_origin,
                        "verified_full_page": False
                    })
                    chunk_counter += 1
                    current_passage = current_passage[-3:]  # Overlap 3 words
                    current_len = sum(len(x) + 1 for x in current_passage)
                    
            if current_passage and current_len > 20:
                p_text = " ".join(current_passage)
                chunks.append({
                    "chunk_id": f"C{chunk_counter}",
                    "title": title,
                    "link": url,
                    "snippet": p_text,
                    "source": source,
                    "query_origin": query_origin,
                    "verified_full_page": False
                })
                chunk_counter += 1

    return chunks


class InMemoryVectorStore:
    """
    In-memory vector store for embedding, indexing, and ranking search evidence passages.
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = PRIMARY_EMBEDDING_MODEL):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name
        self.indexed_passages: List[Dict[str, Any]] = []
        self.embeddings: List[List[float]] = []

    def _embed_text(self, text: str) -> Optional[List[float]]:
        """Generates embedding vector for a single string using google-genai SDK."""
        if not self.api_key or not text.strip():
            return None
            
        client = genai.Client(api_key=self.api_key)
        candidate_models = [self.model_name] + [m for m in FALLBACK_EMBEDDING_MODELS if m != self.model_name]
        
        for current_model in candidate_models:
            try:
                resp = client.models.embed_content(
                    model=current_model,
                    contents=text
                )
                if resp.embeddings and len(resp.embeddings) > 0:
                    return resp.embeddings[0].values
            except Exception as e:
                logger.warning(f"Embedding API warning on model '{current_model}': {e}")
                
        return None

    def index_evidence(self, organic_results: List[Dict[str, Any]]) -> bool:
        """
        Chunks and indexes evidence items into the vector store.
        Returns True if embedding indexing succeeded, False if fallback is required.
        """
        if not organic_results or not self.api_key:
            return False
            
        chunks = chunk_evidence_items(organic_results)
        if not chunks:
            return False
            
        indexed_passages = []
        vectors = []
        
        for c in chunks:
            vec = self._embed_text(c["snippet"])
            if vec is not None:
                indexed_passages.append(c)
                vectors.append(vec)
                
        if not vectors:
            logger.warning("RAG Pipeline: Embedding generation failed for all chunks. Using fallback.")
            return False

        self.indexed_passages = indexed_passages
        self.embeddings = vectors
        logger.info(f"RAG Pipeline: Successfully indexed {len(vectors)} passage vectors.")
        return True

    def retrieve_relevant_passages(self, query: str, top_k: int = 8) -> List[Dict[str, Any]]:
        """
        Retrieves top-k most semantically relevant passages for a query using cosine similarity.
        Annotates each returned passage with `similarity_score`.
        """
        if not self.embeddings or not self.indexed_passages:
            return []
            
        query_vec = self._embed_text(query)
        if query_vec is None:
            # Fallback to returning initial passages with neutral similarity score
            return [dict(p, similarity_score=0.500) for p in self.indexed_passages[:top_k]]
            
        scored_passages = []
        for idx, passage in enumerate(self.indexed_passages):
            passage_vec = self.embeddings[idx]
            sim = cosine_similarity(query_vec, passage_vec)
            # Clamp similarity between 0.0 and 1.0
            sim_clamped = max(0.0, min(1.0, float(sim)))
            scored_item = dict(passage)
            scored_item["similarity_score"] = round(sim_clamped, 3)
            scored_passages.append(scored_item)

        # Sort descending by similarity_score
        scored_passages.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored_passages[:top_k]


def format_rag_context(top_passages: List[Dict[str, Any]]) -> str:
    """Formats RAG retrieved passages into grounded context string with source URLs and similarity scores."""
    if not top_passages:
        return "No RAG evidence passages retrieved."
        
    formatted_sources = []
    for idx, item in enumerate(top_passages, start=1):
        sim_score = item.get("similarity_score", 0.500)
        formatted_sources.append(
            f"[Source {idx}]\n"
            f"Title: {item.get('title', 'N/A')}\n"
            f"URL: {item.get('link', 'N/A')}\n"
            f"Snippet: {item.get('snippet', 'N/A')}\n"
            f"Retrieval Similarity Score: {sim_score:.3f} (Vector Search Match)\n"
            f"Evidence Scope: Search Snippet (Not Full Page Rendered)\n"
        )
    return "\n---\n".join(formatted_sources)
