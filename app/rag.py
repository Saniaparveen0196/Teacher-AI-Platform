# app/rag.py
"""
Lightweight RAG layer: chunks the parsed document, builds a TF-IDF index,
and retrieves the most relevant chunks for a given query.

Uses TF-IDF/cosine similarity (scikit-learn) rather than dense embeddings
(sentence-transformers + a vector DB) deliberately — dense embedding models
pull in PyTorch, a large dependency that risks the same free-tier deployment
issues already hit once with an oversized requirements.txt. TF-IDF is
lightweight, dependency-cheap, and well-suited to single-document retrieval
at chapter scale, where lexical overlap is a strong relevance signal.
"""
from dataclasses import dataclass
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class Chunk:
    chunk_id: str
    section: str
    text: str


def chunk_document(parsed_doc: dict, max_chunk_chars: int = 1200) -> List[Chunk]:
    """
    Chunks by section first (sections are already meaningful boundaries from
    Stage 1's structural parse), then sub-splits any section that's still
    too large for a single chunk.
    """
    chunks = []
    chunk_counter = 0

    for section in parsed_doc["sections"]:
        heading = section["heading"]
        text = section["text"].strip()
        if not text:
            continue

        if len(text) <= max_chunk_chars:
            chunks.append(Chunk(chunk_id=f"c{chunk_counter}", section=heading, text=text))
            chunk_counter += 1
        else:
            # Sub-split long sections on paragraph boundaries where possible
            paragraphs = text.split("\n")
            buffer = ""
            for para in paragraphs:
                if len(buffer) + len(para) > max_chunk_chars and buffer:
                    chunks.append(Chunk(chunk_id=f"c{chunk_counter}", section=heading, text=buffer.strip()))
                    chunk_counter += 1
                    buffer = ""
                buffer += para + "\n"
            if buffer.strip():
                chunks.append(Chunk(chunk_id=f"c{chunk_counter}", section=heading, text=buffer.strip()))
                chunk_counter += 1

    return chunks


class DocumentIndex:
    """A TF-IDF index over a document's chunks, built once and queried
    multiple times (e.g. once per pipeline stage that needs grounded context)."""

    def __init__(self, chunks: List[Chunk]):
        self.chunks = chunks
        self._vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
        if chunks:
            self._matrix = self._vectorizer.fit_transform([c.text for c in chunks])
        else:
            self._matrix = None

    def retrieve(self, query: str, top_k: int = 6) -> List[Chunk]:
        """Returns the top_k most relevant chunks for the query, ranked by
        TF-IDF cosine similarity. Falls back to returning all chunks (in
        original order) if the index is empty or too small to be useful."""
        if not self.chunks or self._matrix is None:
            return []
        if len(self.chunks) <= top_k:
            return self.chunks

        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix)[0]
        ranked_indices = scores.argsort()[::-1][:top_k]
        return [self.chunks[i] for i in ranked_indices]


def build_index(parsed_doc: dict) -> DocumentIndex:
    chunks = chunk_document(parsed_doc)
    return DocumentIndex(chunks)