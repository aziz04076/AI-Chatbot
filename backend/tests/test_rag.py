import pytest
from app.services.rag_service import RAGPipeline

def test_rag_pipeline_indexing_and_retrieval():
    rag = RAGPipeline()
    sample_doc = (
        "PagedAttention is an algorithm that improves memory efficiency for LLM serving. "
        "It manages the KV cache in virtual memory blocks, eliminating memory fragmentation."
    )
    chunks = rag._chunk_text(sample_doc, "sample.md")
    rag.chunks = chunks
    rag._build_vector_space()

    assert len(rag.chunks) > 0
    assert "pagedattention" in rag.vocabulary

    results = rag.retrieve("How does PagedAttention handle KV cache memory?", top_k=1, threshold=0.1)
    assert len(results) > 0
    assert results[0].source == "sample.md"
    assert "PagedAttention" in results[0].snippet
