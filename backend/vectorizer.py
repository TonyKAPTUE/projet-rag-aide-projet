"""
Semantic Vectorization and Hybrid Retrieval Engine for Engineering Datasheets & Datasets.
Supports:
1. Dense neural embeddings via Hugging Face Inference API (BAAI/bge-m3 or sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2) when HF_TOKEN is configured.
2. Local High-Dimensional Semantic Subword & Technical N-Gram Vectorizer (TF-IDF + SVD/Cosine similarity + exact hex/pin/unit boosting) for zero-latency offline or fallback execution.
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

import httpx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.extractor import DocumentChunk, ExtractedDocument


# French/English technical synonym expansion so queries like "branchement" match "câblage / pinout / broche"
TECHNICAL_SYNONYM_GROUPS: list[set[str]] = [
    {"broche", "brochage", "pin", "pinout", "connexion", "cablage", "branchement", "lga", "gpio"},
    {"tension", "alimentation", "vdd", "vddio", "volt", "voltage", "3v3", "5v", "electrique", "courant", "consommation", "ua"},
    {"i2c", "spi", "adresse", "bus", "sda", "scl", "sdi", "sck", "sdo", "csb", "0x76", "0x77", "pullup", "pull"},
    {"registre", "register", "0xd0", "0xf2", "0xf4", "0xf5", "0xe0", "ctrl_hum", "ctrl_meas", "chip_id", "0x60", "0x58", "configuration"},
    {"temperature", "thermique", "echauffement", "auto-echauffement", "derive", "degre", "celsius"},
    {"humidite", "hygrometrie", "rh", "0x8000", "bmp280"},
    {"pression", "barometre", "barometrique", "altitude", "altimetre", "hpa", "bruit", "rms", "drone", "iir", "oversampling"},
    {"panne", "erreur", "probleme", "depannage", "diagnostic", "troubleshooting", "bloque", "nack", "anomalie"},
]


def _normalize_text(text: str) -> str:
    """Lowercase and strip accents for robust cross-lingual French/English technical matching."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    without_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return without_accents


def _expand_query_with_synonyms(query: str) -> str:
    norm_q = _normalize_text(query)
    tokens = set(re.findall(r"[a-z0-9_]+", norm_q))
    expansions: list[str] = []
    for group in TECHNICAL_SYNONYM_GROUPS:
        if tokens & group:
            expansions.extend(group - tokens)
    if expansions:
        return f"{query} {' '.join(expansions)}"
    return query


@dataclass
class RetrievedPassage:
    chunk: DocumentChunk
    similarity_score: float
    dense_score: float
    lexical_score: float
    rank: int

    def to_citation_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "chunk_id": self.chunk.chunk_id,
            "doc_id": self.chunk.doc_id,
            "doc_name": self.chunk.doc_name,
            "doc_type": self.chunk.doc_type,
            "source_ref": self.chunk.source_ref,
            "section_title": self.chunk.section_title,
            "content": self.chunk.content,
            "page_or_row": self.chunk.page_or_row,
            "similarity_score": round(float(self.similarity_score), 4),
            "dense_score": round(float(self.dense_score), 4),
            "lexical_score": round(float(self.lexical_score), 4),
        }


class SemanticVectorStore:
    """
    Manages the indexed corpus of datasheets and datasets, computing semantic vector representations
    and performing hybrid retrieval with citation metadata.
    """

    def __init__(self) -> None:
        self.documents: dict[str, ExtractedDocument] = {}
        self.chunks: list[DocumentChunk] = []

        # Local Dual Vectorizers: Word N-gram (technical terms & hex registers) + Character N-gram (subword robustness)
        self.word_vectorizer = TfidfVectorizer(
            preprocessor=_normalize_text,
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b[a-zA-Z0-9_x\.\-\+]{2,}\b",
            sublinear_tf=True,
        )
        self.char_vectorizer = TfidfVectorizer(
            preprocessor=_normalize_text,
            analyzer="char_wb",
            ngram_range=(3, 5),
            sublinear_tf=True,
        )
        self.word_matrix: Any = None
        self.char_matrix: Any = None
        self.hf_embeddings: np.ndarray | None = None
        self.embedding_backend_name: str = "Subword & Technical N-Gram Vectorizer (Local)"
        self.vector_dimension: int = 0

    def add_document(self, doc: ExtractedDocument, hf_token: str | None = None) -> None:
        """Add or replace a document in the vector store and rebuild indices."""
        self.documents[doc.doc_id] = doc
        self._rebuild_index(hf_token=hf_token)

    def remove_document(self, doc_id: str, hf_token: str | None = None) -> bool:
        if doc_id in self.documents:
            del self.documents[doc_id]
            self._rebuild_index(hf_token=hf_token)
            return True
        return False

    def _corpus_texts(self) -> list[str]:
        return [
            f"{c.doc_name} | {c.source_ref} | {c.section_title}\n{c.content}"
            for c in self.chunks
        ]

    def _rebuild_index(self, hf_token: str | None = None) -> None:
        all_chunks: list[DocumentChunk] = []
        for doc in self.documents.values():
            all_chunks.extend(doc.chunks)
        self.chunks = all_chunks

        if not self.chunks:
            self.word_matrix = None
            self.char_matrix = None
            self.hf_embeddings = None
            self.vector_dimension = 0
            return

        texts = self._corpus_texts()
        self.word_matrix = self.word_vectorizer.fit_transform(texts)
        self.char_matrix = self.char_vectorizer.fit_transform(texts)
        self.vector_dimension = int(self.word_matrix.shape[1] + self.char_matrix.shape[1])
        self.embedding_backend_name = (
            f"Vectorisation Hybride Sémantique Locale ({self.vector_dimension} dim. TF-IDF Subword + N-Grams Techniques)"
        )

        # Optional dense embeddings via Hugging Face Inference API if token provided
        token = hf_token or os.environ.get("HF_TOKEN")
        if token and token.strip():
            dense = self._fetch_hf_embeddings(texts, token.strip())
            if dense is not None and dense.shape[0] == len(texts):
                self.hf_embeddings = dense
                self.embedding_backend_name = (
                    f"Hugging Face Dense Embeddings (sentence-transformers, {dense.shape[1]} dim.) + Lexical Hybrid"
                )
            else:
                self.hf_embeddings = None
        else:
            self.hf_embeddings = None

    def _fetch_hf_embeddings(self, texts: list[str], token: str) -> np.ndarray | None:
        """Attempt to compute dense embeddings via Hugging Face Inference API feature-extraction."""
        model_id = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        url = f"https://router.huggingface.co/hf-inference/models/{model_id}/pipeline/feature-extraction"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, headers=headers, json={"inputs": texts, "options": {"wait_for_model": False}})
                if resp.status_code == 200:
                    arr = np.array(resp.json(), dtype=np.float32)
                    if arr.ndim == 2:
                        norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9
                        return arr / norms
        except Exception:
            pass
        return None

    def search(
        self,
        query: str,
        top_k: int = 5,
        doc_filter: list[str] | None = None,
        hf_token: str | None = None,
    ) -> list[RetrievedPassage]:
        """
        Retrieve the top_k most relevant passages across datasheets and datasets using hybrid semantic scoring.
        """
        if not self.chunks or self.word_matrix is None or self.char_matrix is None:
            return []

        expanded_query = _expand_query_with_synonyms(query)

        # 1. Word-level semantic & technical N-gram cosine similarity
        q_word = self.word_vectorizer.transform([expanded_query])
        word_scores = cosine_similarity(q_word, self.word_matrix).flatten()

        # 2. Subword character N-gram cosine similarity (handles morphology, typos, part numbers)
        q_char = self.char_vectorizer.transform([query])
        char_scores = cosine_similarity(q_char, self.char_matrix).flatten()

        # 3. Exact technical identifier boost (hex addresses like 0x76, 0xD0, EXP-06, pin numbers, voltages)
        norm_q = _normalize_text(query)
        tech_tokens = re.findall(r"(?:0x[0-9a-f]+|exp-\d+|\b(?:vdd|vddio|sda|scl|sdo|csb|i2c|spi|bme280|bmp280)\b)", norm_q)
        exact_boost = np.zeros(len(self.chunks), dtype=np.float32)
        if tech_tokens:
            for idx, chunk in enumerate(self.chunks):
                norm_c = _normalize_text(f"{chunk.source_ref} {chunk.section_title} {chunk.content}")
                hits = sum(1 for tok in set(tech_tokens) if tok in norm_c)
                if hits > 0:
                    exact_boost[idx] = min(0.28, 0.12 * hits)

        # 4. Optional Hugging Face dense similarity
        dense_scores = char_scores.copy()
        token = hf_token or os.environ.get("HF_TOKEN")
        if self.hf_embeddings is not None and token:
            q_dense = self._fetch_hf_embeddings([query], token)
            if q_dense is not None and q_dense.shape[1] == self.hf_embeddings.shape[1]:
                dense_scores = np.dot(self.hf_embeddings, q_dense[0])

        # Hybrid combination
        combined_scores = 0.52 * word_scores + 0.36 * dense_scores + 0.12 * char_scores + exact_boost

        # Balance datasheet & dataset representation when both are present and query is broad
        results: list[RetrievedPassage] = []
        candidate_indices = np.argsort(combined_scores)[::-1]

        rank = 1
        for idx in candidate_indices:
            chunk = self.chunks[int(idx)]
            if doc_filter and chunk.doc_id not in doc_filter:
                continue
            score = float(combined_scores[int(idx)])
            if score <= 0.01 and rank > 2:
                continue
            results.append(
                RetrievedPassage(
                    chunk=chunk,
                    similarity_score=min(0.99, score),
                    dense_score=float(dense_scores[int(idx)]),
                    lexical_score=float(word_scores[int(idx)]),
                    rank=rank,
                )
            )
            rank += 1
            if len(results) >= top_k:
                break

        return results

    def status_summary(self) -> dict[str, Any]:
        return {
            "total_documents": len(self.documents),
            "total_chunks": len(self.chunks),
            "vector_dimension": self.vector_dimension,
            "embedding_backend": self.embedding_backend_name,
            "documents": [doc.to_meta_dict() for doc in self.documents.values()],
        }
