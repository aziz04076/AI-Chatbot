import pytest
from app.services.rag_service import BM25Index, RAGPipeline

def test_bm25_index_basic():
    bm25 = BM25Index(k1=1.5, b=0.75)
    corpus = [
        ["kubernetes", "pod", "disruption", "budget", "high", "availability"],
        ["vllm", "pagedattention", "gpu", "vram", "optimization", "serving"],
        ["terraform", "eks", "aws", "infrastructure", "as", "code"]
    ]
    bm25.fit(corpus)
    assert bm25.corpus_size == 3
    assert "pagedattention" in bm25.idf

    scores = bm25.get_scores(["pagedattention", "vllm"])
    # Document 1 (vLLM) should have highest BM25 score
    assert scores[1] > scores[0]
    assert scores[1] > scores[2]

def test_hybrid_rag_pipeline():
    rag = RAGPipeline()
    doc1 = (
        "# Nexus Kubernetes Hardening\n\n"
        "Every mission-critical deployment must declare a PodDisruptionBudget specifying minAvailable: 2 "
        "to safeguard service availability during voluntary disruptions."
    )
    doc2 = (
        "# Nexus vLLM Optimization\n\n"
        "PagedAttention divides the KV cache into non-contiguous physical memory blocks rather than "
        "pre-allocating contiguous memory pools, eliminating memory fragmentation."
    )

    chunks = []
    chunks.extend(rag._chunk_text(doc1, "k8s_hardening.md"))
    chunks.extend(rag._chunk_text(doc2, "vllm_opt.md"))
    rag.chunks = chunks
    rag._build_indices()

    assert rag.bm25_index is not None
    assert len(rag.chunks) >= 2

    # Query with exact technical keywords
    citations = rag.retrieve("PodDisruptionBudget minAvailable", top_k=2, mode="hybrid")
    assert len(citations) > 0
    assert citations[0].source == "k8s_hardening.md"
    assert "hybrid" in citations[0].retrieval_method
    assert citations[0].similarity >= 0.50

    # Query with semantic concept
    v_citations = rag.retrieve("How does KV cache memory fragmentation get eliminated in GPU serving?", top_k=1, mode="hybrid")
    assert len(v_citations) > 0
    assert v_citations[0].source == "vllm_opt.md"
    assert "PagedAttention" in v_citations[0].snippet

def test_reciprocal_rank_fusion_math():
    rag = RAGPipeline()
    vector_results = [(0.92, 0), (0.75, 1)]
    bm25_results = [(4.5, 1), (2.1, 0)]

    # Candidate 0: vector rank 1, bm25 rank 2 -> RRF = 1/61 + 1/62
    # Candidate 1: vector rank 2, bm25 rank 1 -> RRF = 1/62 + 1/61
    rag.chunks = [{"source": "doc0.md", "content": "test zero"}, {"source": "doc1.md", "content": "test one"}]
    fused = rag.reciprocal_rank_fusion(vector_results, bm25_results, k=60)
    assert len(fused) == 2
    assert abs(fused[0]["rrf_score"] - fused[1]["rrf_score"]) < 1e-6
