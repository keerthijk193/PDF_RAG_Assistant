# =============================================================================
# routers/chat.py — Handles chat messages
# =============================================================================
#
# This file defines the POST /api/chat endpoint.
#
# THE FULL RAG PIPELINE (what happens when user sends a message):
#
#  User types question
#       │
#       ▼
#  POST /api/chat { question, history }
#       │
#       ▼
#  [1] Embed the question → vector
#       │
#       ▼
#  [2] Search FAISS → find top-4 most similar chunks
#       │
#       ▼
#  [3] Build prompt:
#       System: "Answer using this context: [chunks]"
#       History: [previous messages]
#       User: "What is X?"
#       │
#       ▼
#  [4] Send to Ollama (local LLM) → stream back tokens
#       │
#       ▼
#  [5] Frontend receives tokens and displays them word by word
# =============================================================================

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import json

from services.pdf_service import search_similar_chunks
from services.llm_service import build_rag_prompt, stream_ollama_response

router = APIRouter()


# -----------------------------------------------------------------------------
# Pydantic Models — define the shape of our request/response data
# -----------------------------------------------------------------------------
# Pydantic is FastAPI's data validation library. When we define a model,
# FastAPI automatically:
#   1. Parses the JSON body of the request
#   2. Validates that all required fields are present
#   3. Converts types (e.g., strings to numbers)
#   4. Returns helpful error messages if validation fails

class ChatMessage(BaseModel):
    """Represents a single message in the conversation."""
    role: str     # Either "user" or "assistant"
    content: str  # The text of the message

class ChatRequest(BaseModel):
    """The body of a POST /api/chat request."""
    question: str              # The user's new question
    history: List[ChatMessage] = []  # Previous messages (default: empty list)
    model: str = "llama-3.1-8b-instant"      # Which Ollama model to use


# -----------------------------------------------------------------------------
# The streaming chat endpoint
# -----------------------------------------------------------------------------
@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Main RAG chat endpoint. Retrieves relevant context, builds the prompt,
    and streams the LLM's response back to the frontend.

    WHAT IS StreamingResponse?
    Instead of waiting for the ENTIRE response and sending it all at once,
    StreamingResponse lets us send data piece by piece as it's generated.

    This is how ChatGPT shows text appearing word by word!

    WHAT IS Server-Sent Events (SSE)?
    A protocol where the server "pushes" data to the browser over a
    long-lived HTTP connection. The browser reads chunks of data as
    they arrive. Each chunk is formatted as:
        data: <content>\n\n
    """

    # Validate the question
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Step 1: Find relevant chunks from our PDF knowledge base
    context_chunks = search_similar_chunks(request.question, top_k=3)

    # Step 2: Build the full prompt with context + history
    messages = build_rag_prompt(
        question=request.question,
        context_chunks=context_chunks,
        chat_history=[msg.dict() for msg in request.history]
    )

    # Step 3: Create a streaming generator function
    # This function will yield data chunks as the LLM generates them
    async def generate():
        """
        This is an "async generator function."
        It runs the Ollama call and yields tokens one by one.
        Each yielded value is sent immediately to the frontend.
        """
        # First, send the context sources so the frontend can show them
        sources_data = {
            "type": "sources",
            "sources": context_chunks[:2]  # Send first 2 chunks as sources
        }
        yield f"data: {json.dumps(sources_data)}\n\n"

        # Then stream the actual answer tokens
        async for token in stream_ollama_response(messages, request.model):
            token_data = {
                "type": "token",
                "content": token
            }
            yield f"data: {json.dumps(token_data)}\n\n"

        # Signal that streaming is complete
        done_data = {"type": "done"}
        yield f"data: {json.dumps(done_data)}\n\n"

    # Return a streaming response
    # media_type="text/event-stream" tells the browser to expect SSE format
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",       # Don't cache streaming responses
            "X-Accel-Buffering": "no",          # Disable nginx buffering
        }
    )
