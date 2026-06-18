# =============================================================================
# routers/upload.py — Handles PDF file upload API endpoint
# =============================================================================
#
# This file defines the POST /api/upload endpoint.
#
# WHAT HAPPENS WHEN THE USER UPLOADS A PDF:
#   React → POST /api/upload (with the file) → FastAPI receives it →
#   We process it (extract text, chunk, embed, store) → Return success
# =============================================================================

from fastapi import APIRouter, UploadFile, File, HTTPException
from services.pdf_service import process_pdf, get_status

# APIRouter groups related endpoints. Think of it like a sub-application.
router = APIRouter()


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Receives a PDF file from the frontend, processes it, and adds it to FAISS.

    WHAT IS UploadFile?
    FastAPI's special type for handling file uploads. It gives us:
      - file.filename: the original filename
      - file.content_type: "application/pdf"
      - file.read(): reads the raw bytes of the file

    WHAT IS File(...)?
    The "..." means this parameter is REQUIRED. If no file is provided,
    FastAPI automatically returns a 422 error.
    """

    # Validate that the uploaded file is actually a PDF
    # (Users might accidentally upload .docx or .txt files)
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported. Please upload a .pdf file."
        )

    # Read the file's raw bytes into memory
    # This is the binary content of the PDF
    file_bytes = await file.read()

    # Safety check: make sure the file isn't empty
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    # File size limit: 50MB (to prevent server overload)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 50MB."
        )

    try:
        # Hand off to our PDF processing pipeline (defined in pdf_service.py)
        result = await process_pdf(file_bytes, file.filename)

        return {
            "success": True,
            "message": f"Successfully processed '{file.filename}'",
            "details": result
        }

    except ValueError as e:
        # ValueError is raised when the PDF has no extractable text
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        # Catch all other errors (disk full, memory error, etc.)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(e)}"
        )


@router.get("/status")
async def get_index_status():
    """
    Returns information about the current state of the FAISS index.
    The frontend uses this to show which PDFs have been uploaded.
    """
    return get_status()
