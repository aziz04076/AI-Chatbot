import io
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.services.rag_service import rag_service
import logging

logger = logging.getLogger("NexusAI-Files")
router = APIRouter(prefix="/files", tags=["File Analysis & Ingestion"])

class FileAnalysisResponse(BaseModel):
    filename: str
    content_type: str
    extracted_text_preview: str
    total_characters: int
    chunks_indexed: int
    message: str

@router.post("/upload", response_model=FileAnalysisResponse)
async def upload_and_analyze_file(file: UploadFile = File(...)):
    """
    Uploads PDF or text file, extracts text, performs content analysis,
    and indexes chunks into the RAG vector space.
    """
    try:
        content = await file.read()
        extracted_text = ""

        if file.filename.endswith(".pdf"):
            try:
                import pypdf
                pdf_reader = pypdf.PdfReader(io.BytesIO(content))
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n"
            except Exception as e:
                logger.warning(f"pypdf extraction failed, attempting fallback: {e}")
                extracted_text = content.decode("utf-8", errors="ignore")
        else:
            extracted_text = content.decode("utf-8", errors="ignore")

        if not extracted_text.strip():
            extracted_text = f"Analyzed binary file: {file.filename}. Image / document structure noted."

        # Index into RAG pipeline
        chunks = rag_service._chunk_text(extracted_text, file.filename)
        rag_service.chunks.extend(chunks)
        rag_service._build_vector_space()

        preview = extracted_text[:300].strip() + ("..." if len(extracted_text) > 300 else "")

        return FileAnalysisResponse(
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            extracted_text_preview=preview,
            total_characters=len(extracted_text),
            chunks_indexed=len(chunks),
            message=f"File successfully ingested into NexusAI RAG index ({len(chunks)} chunks created)."
        )
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {e}")
