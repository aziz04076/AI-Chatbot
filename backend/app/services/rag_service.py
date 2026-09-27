import os
import math
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from app.config import settings
from app.schemas.chat import Citation
import logging

logger = logging.getLogger("NexusAI-RAG")

class BM25Index:
    """
    Self-contained Okapi BM25 implementation for exact keyword and technical token retrieval.
    Parameter tuning: k1=1.5 (term frequency saturation), b=0.75 (document length normalization).
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = 0
        self.avgdl = 0.0
        self.doc_lengths: List[int] = []
        self.doc_term_freqs: List[Dict[str, int]] = []
        self.idf: Dict[str, float] = {}

    def fit(self, tokenized_docs: List[List[str]]):
        self.corpus_size = len(tokenized_docs)
        if self.corpus_size == 0:
            return

        self.doc_lengths = [len(doc) for doc in tokenized_docs]
        self.avgdl = sum(self.doc_lengths) / max(1, self.corpus_size)

        # Document frequencies for IDF
        df: Dict[str, int] = {}
        self.doc_term_freqs = []

        for doc in tokenized_docs:
            tf: Dict[str, int] = {}
            seen_in_doc = set()
            for token in doc:
                tf[token] = tf.get(token, 0) + 1
                if token not in seen_in_doc:
                    df[token] = df.get(token, 0) + 1
                    seen_in_doc.add(token)
            self.doc_term_freqs.append(tf)

        # Compute Robertson-Spärck Jones IDF
        self.idf = {}
        for token, doc_count in df.items():
            # Standard BM25 IDF formulation
            self.idf[token] = math.log(1.0 + (self.corpus_size - doc_count + 0.5) / (doc_count + 0.5))

    def get_scores(self, query_tokens: List[str]) -> List[float]:
        """Calculates BM25 score for all documents against query tokens."""
        scores = [0.0] * self.corpus_size
        if self.corpus_size == 0 or not query_tokens:
            return scores

        for token in query_tokens:
            if token not in self.idf:
                continue
            idf_val = self.idf[token]

            for i in range(self.corpus_size):
                tf = self.doc_term_freqs[i].get(token, 0)
                if tf == 0:
                    continue
                doc_len = self.doc_lengths[i]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / max(1.0, self.avgdl)))
                scores[i] += idf_val * (numerator / denominator)

        return scores

    def retrieve(self, query_tokens: List[str], top_k: int = 10) -> List[Tuple[float, int]]:
        """Returns sorted list of (score, doc_idx) pairs."""
        scores = self.get_scores(query_tokens)
        scored_docs = [(s, i) for i, s in enumerate(scores) if s > 0.0]
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return scored_docs[:top_k]

class RAGPipeline:
    """
    Production Hybrid RAG Pipeline combining:
    1. Okapi BM25 keyword search
    2. Dense cosine vector similarity
    3. Reciprocal Rank Fusion (RRF)
    4. Cross-Score Re-ranking step
    """
    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.vocabulary: Dict[str, int] = {}
        self.doc_vectors: List[List[float]] = []
        self.bm25_index: Optional[BM25Index] = None

    def _tokenize(self, text: str) -> List[str]:
        # Captures alphanumeric terms, hyphenated identifiers, and dotted paths
        return re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())

    def _chunk_text(self, text: str, source: str, chunk_size: int = 400, overlap: int = 50) -> List[Dict[str, Any]]:
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_len = 0

        for p in paragraphs:
            words = p.split()
            if not words:
                continue
            if current_len + len(words) > chunk_size and current_chunk:
                snippet = " ".join(current_chunk)
                chunks.append({"source": source, "content": snippet})
                # keep overlap
                current_chunk = current_chunk[-overlap:] if len(current_chunk) > overlap else []
                current_len = len(current_chunk)
            current_chunk.extend(words)
            current_len += len(words)

        if current_chunk:
            snippet = " ".join(current_chunk)
            chunks.append({"source": source, "content": snippet})
        return chunks

    def index_documents(self):
        """Indexes all documents in the knowledge base directory."""
        kb_path = Path(settings.KNOWLEDGE_BASE_DIR)
        kb_path.mkdir(parents=True, exist_ok=True)

        all_chunks = []
        for file in kb_path.glob("**/*"):
            if file.is_file() and file.suffix.lower() in [".md", ".txt", ".json"]:
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        content = f.read()
                        doc_chunks = self._chunk_text(content, file.name)
                        all_chunks.extend(doc_chunks)
                except Exception as e:
                    logger.warning(f"Could not read {file}: {e}")

        self.chunks = all_chunks
        self._build_indices()
        logger.info(f"Hybrid RAG indexed {len(self.chunks)} knowledge chunks from {kb_path}")

    def _build_indices(self):
        """Builds both dense vector space and BM25 inverted index."""
        tokenized_docs = [self._tokenize(chunk["content"]) for chunk in self.chunks]

        # 1. Build BM25 Index
        self.bm25_index = BM25Index()
        self.bm25_index.fit(tokenized_docs)

        # 2. Build TF-IDF / Normalized Vector Space
        vocab: Dict[str, int] = {}
        df: Dict[str, int] = {}
        for tokens in tokenized_docs:
            for t in set(tokens):
                df[t] = df.get(t, 0) + 1
                if t not in vocab:
                    vocab[t] = len(vocab)

        self.vocabulary = vocab
        N = max(1, len(self.chunks))
        self.doc_vectors = []

        for tokens in tokenized_docs:
            vec = [0.0] * len(vocab)
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            for t, count in tf.items():
                if t in vocab:
                    idx = vocab[t]
                    idf = math.log((N + 1) / (df.get(t, 1) + 1)) + 1.0
                    vec[idx] = count * idf
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            self.doc_vectors.append([x / norm for x in vec])

    def _build_vector_space(self):
        """Backwards compatibility alias for _build_indices."""
        self._build_indices()

    def retrieve_vector(self, query: str, top_k: int = 10, threshold: float = 0.05) -> List[Tuple[float, int]]:
        """Returns sorted list of (cosine_score, doc_idx)."""
        if not self.chunks or not self.vocabulary:
            return []

        q_tokens = self._tokenize(query)
        q_vec = [0.0] * len(self.vocabulary)
        q_tf: Dict[str, int] = {}
        for t in q_tokens:
            q_tf[t] = q_tf.get(t, 0) + 1

        for t, count in q_tf.items():
            if t in self.vocabulary:
                q_vec[self.vocabulary[t]] = count

        norm = math.sqrt(sum(x * x for x in q_vec)) or 1.0
        q_vec = [x / norm for x in q_vec]

        scores = []
        for i, doc_vec in enumerate(self.doc_vectors):
            dot_product = sum(q_vec[k] * doc_vec[k] for k in range(len(q_vec)))
            if dot_product >= threshold:
                scores.append((dot_product, i))

        scores.sort(key=lambda x: x[0], reverse=True)
        return scores[:top_k]

    def retrieve_bm25(self, query: str, top_k: int = 10) -> List[Tuple[float, int]]:
        """Returns sorted list of (bm25_score, doc_idx)."""
        if not self.bm25_index:
            return []
        q_tokens = self._tokenize(query)
        return self.bm25_index.retrieve(q_tokens, top_k=top_k)

    def reciprocal_rank_fusion(
        self,
        vector_results: List[Tuple[float, int]],
        bm25_results: List[Tuple[float, int]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Combines disparate score scales using Reciprocal Rank Fusion (RRF).
        RRF_Score(d) = 1 / (k + rank_bm25(d)) + 1 / (k + rank_vector(d))
        """
        rrf_scores: Dict[int, float] = {}
        meta: Dict[int, Dict[str, Any]] = {}

        for rank, (score, doc_idx) in enumerate(vector_results, start=1):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + (1.0 / (k + rank))
            meta[doc_idx] = meta.get(doc_idx, {})
            meta[doc_idx]["vector_rank"] = rank
            meta[doc_idx]["vector_score"] = round(score, 3)

        for rank, (score, doc_idx) in enumerate(bm25_results, start=1):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + (1.0 / (k + rank))
            meta[doc_idx] = meta.get(doc_idx, {})
            meta[doc_idx]["bm25_rank"] = rank
            meta[doc_idx]["bm25_score"] = round(score, 3)

        candidates = []
        for doc_idx, score in rrf_scores.items():
            candidates.append({
                "doc_idx": doc_idx,
                "rrf_score": score,
                "vector_rank": meta[doc_idx].get("vector_rank"),
                "bm25_rank": meta[doc_idx].get("bm25_rank"),
                "chunk": self.chunks[doc_idx]
            })

        candidates.sort(key=lambda x: x["rrf_score"], reverse=True)
        return candidates

    def rerank(self, candidates: List[Dict[str, Any]], query: str, top_k: int = 4) -> List[Citation]:
        """
        Re-ranking step evaluating:
        - Query term coverage ratio
        - Exact phrase match bonus
        - Markdown header relevance
        Calibrates final score to [0.50, 0.98].
        """
        if not candidates:
            return []

        q_tokens = set(self._tokenize(query))
        q_lower = query.lower()

        reranked = []
        max_rrf = max(c["rrf_score"] for c in candidates) if candidates else 1.0

        for item in candidates:
            chunk_content = item["chunk"]["content"]
            chunk_tokens = set(self._tokenize(chunk_content))
            content_lower = chunk_content.lower()

            # 1. Base RRF contribution (0.0 - 0.40)
            base_score = (item["rrf_score"] / max_rrf) * 0.40

            # 2. Query Term Coverage (0.0 - 0.30)
            overlap = len(q_tokens.intersection(chunk_tokens))
            coverage = overlap / max(1, len(q_tokens))
            coverage_score = coverage * 0.30

            # 3. Exact Phrase Match Bonus (0.0 - 0.15)
            phrase_bonus = 0.0
            # Test significant bigrams / phrases
            words = q_lower.split()
            for w_len in [3, 2]:
                for start in range(len(words) - w_len + 1):
                    subphrase = " ".join(words[start:start + w_len])
                    if len(subphrase) > 6 and subphrase in content_lower:
                        phrase_bonus = 0.15
                        break
                if phrase_bonus > 0:
                    break

            # 4. Header match bonus (0.0 - 0.10)
            header_bonus = 0.0
            if any(line.startswith("#") and any(t in line.lower() for t in q_tokens) for line in chunk_content.splitlines()):
                header_bonus = 0.10

            final_similarity = round(min(0.98, max(0.50, base_score + coverage_score + phrase_bonus + header_bonus + 0.15)), 3)

            snippet = chunk_content[:280] + ("..." if len(chunk_content) > 280 else "")

            reranked.append({
                "citation": Citation(
                    source=item["chunk"]["source"],
                    snippet=snippet,
                    similarity=final_similarity,
                    retrieval_method="hybrid (BM25 + Vector + RRF)",
                    bm25_rank=item.get("bm25_rank"),
                    vector_rank=item.get("vector_rank")
                ),
                "final_score": final_similarity
            })

        reranked.sort(key=lambda x: x["final_score"], reverse=True)
        return [r["citation"] for r in reranked[:top_k]]

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        threshold: float = 0.15,
        mode: str = "hybrid"
    ) -> List[Citation]:
        """
        Unified retrieval endpoint.
        mode: 'hybrid' (default), 'vector', or 'bm25'.
        """
        if not self.chunks:
            return []

        if mode == "vector":
            v_results = self.retrieve_vector(query, top_k=top_k, threshold=threshold)
            return [
                Citation(
                    source=self.chunks[idx]["source"],
                    snippet=self.chunks[idx]["content"][:280] + ("..." if len(self.chunks[idx]["content"]) > 280 else ""),
                    similarity=round(score, 3),
                    retrieval_method="vector"
                )
                for score, idx in v_results
            ]

        if mode == "bm25":
            b_results = self.retrieve_bm25(query, top_k=top_k)
            return [
                Citation(
                    source=self.chunks[idx]["source"],
                    snippet=self.chunks[idx]["content"][:280] + ("..." if len(self.chunks[idx]["content"]) > 280 else ""),
                    similarity=round(min(0.99, score / 10.0), 3),
                    retrieval_method="bm25"
                )
                for score, idx in b_results
            ]

        # Hybrid Mode: Combine Vector + BM25 via Reciprocal Rank Fusion & Re-rank
        v_results = self.retrieve_vector(query, top_k=top_k * 2, threshold=0.01)
        b_results = self.retrieve_bm25(query, top_k=top_k * 2)

        candidates = self.reciprocal_rank_fusion(v_results, b_results, k=60)
        citations = self.rerank(candidates, query, top_k=top_k)

        # Fallback to vector if candidate list is empty
        if not citations and v_results:
            return [
                Citation(
                    source=self.chunks[idx]["source"],
                    snippet=self.chunks[idx]["content"][:280] + ("..." if len(self.chunks[idx]["content"]) > 280 else ""),
                    similarity=round(score, 3),
                    retrieval_method="vector_fallback"
                )
                for score, idx in v_results[:top_k]
            ]

        return citations

rag_service = RAGPipeline()
