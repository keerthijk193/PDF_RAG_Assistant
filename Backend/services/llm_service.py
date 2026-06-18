# # =============================================================================
# # llm_service.py — Talks to the local LLM via Ollama
# # =============================================================================
# #
# # WHAT IS OLLAMA?
# # Ollama is a tool that lets you run powerful AI models (like Llama 3 or
# # Mistral) LOCALLY on your own computer — completely FREE, no API key needed.
# #
# # HOW IT WORKS:
# #   1. You install Ollama and download a model (e.g., "ollama pull llama3")
# #   2. Ollama runs a local HTTP server at http://localhost:11434
# #   3. We send our prompt to that server and get back the AI's response
# #
# # WHAT IS RAG?
# # Retrieval-Augmented Generation — instead of asking the LLM to answer
# # from its training data, we:
# #   1. RETRIEVE relevant chunks from our PDF (using FAISS)
# #   2. AUGMENT the prompt with those chunks as context
# #   3. GENERATE an answer based on that context
# #
# # This is why the LLM can answer questions about YOUR documents,
# # even though it never saw them during training.
# # =============================================================================

# import httpx  # Async HTTP client (like requests, but async)
# from typing import List, AsyncGenerator
# import json

# # Ollama's local API endpoint
# # When you run "ollama serve", it starts a server here
# OLLAMA_BASE_URL = "http://localhost:11434"

# # The model to use — change this to "mistral" if you prefer Mistral
# # Make sure you've run: ollama pull llama3
# DEFAULT_MODEL = "llama3"


# # -----------------------------------------------------------------------------
# # Build the RAG prompt
# # -----------------------------------------------------------------------------
# def build_rag_prompt(
#     question: str,
#     context_chunks: List[str],
#     chat_history: List[dict]
# ) -> List[dict]:
#     """
#     Constructs the message list to send to the LLM.

#     PROMPT ENGINEERING — how we structure the message matters A LOT.
#     A well-crafted prompt gets much better answers.

#     We use a "system prompt" to set the LLM's behavior, then include
#     the retrieved chunks as context, followed by the chat history,
#     and finally the user's new question.

#     Args:
#         question:      The user's current question
#         context_chunks: Relevant chunks retrieved from FAISS
#         chat_history:  Previous messages in the conversation

#     Returns:
#         A list of message dicts in the format Ollama expects:
#         [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
#     """

#     # Format the retrieved chunks into a readable context block
#     if context_chunks:
#         context_text = "\n\n---\n\n".join([
#             f"[Source chunk {i+1}]:\n{chunk}"
#             for i, chunk in enumerate(context_chunks)
#         ])
#     else:
#         context_text = "No relevant context found in the uploaded documents."

#     # System prompt: tells the LLM WHO it is and HOW to behave
#     system_message = {
#         "role": "system",
#         "content": (
#             "You are a helpful AI assistant that answers questions based on "
#             "the provided document context. Follow these rules:\n\n"
#             "1. ONLY answer using the information from the provided context.\n"
#             "2. If the context doesn't contain the answer, say: "
#             "'I couldn't find information about that in the uploaded documents.'\n"
#             "3. Be concise and clear.\n"
#             "4. If quoting from the document, mention it.\n"
#             "5. Do not make up information.\n\n"
#             f"Here is the relevant context from the user's documents:\n\n"
#             f"{context_text}"
#         )
#     }

#     # Build the message list: system message + chat history + new question
#     messages = [system_message]

#     # Add previous conversation turns (so the LLM remembers the conversation)
#     # Chat history format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
#     for msg in chat_history[-10:]:  # Only use last 10 messages to avoid context overflow
#         messages.append({
#             "role": msg["role"],
#             "content": msg["content"]
#         })

#     # Add the new question
#     messages.append({
#         "role": "user",
#         "content": question
#     })

#     return messages


# # -----------------------------------------------------------------------------
# # Call Ollama API (streaming)
# # -----------------------------------------------------------------------------
# async def stream_ollama_response(
#     messages: List[dict],
#     model: str = DEFAULT_MODEL
# ) -> AsyncGenerator[str, None]:
#     """
#     Sends the prompt to Ollama and streams back the response token by token.

#     WHAT IS STREAMING?
#     Instead of waiting for the entire response (which could take 30 seconds),
#     we receive and display each word/token as it's generated.
#     This makes the UI feel much more responsive — like watching someone type.

#     HOW STREAMING WORKS:
#     1. We make a POST request with stream=True
#     2. Ollama sends back many small JSON responses, one per token
#     3. We parse each line and yield (send) the text to the caller
#     4. The FastAPI endpoint passes this through to the React frontend
#        via Server-Sent Events (SSE)

#     This function is an "async generator" — it uses "yield" to send
#     values back one at a time, rather than returning all at once.
#     """
#     payload = {
#         "model": model,
#         "messages": messages,
#         "stream": True,  # Enable streaming
#         "options": {
#             "temperature": 0.7,  # 0=deterministic, 1=creative. 0.7 is balanced.
#             "num_predict": 1024, # Max tokens to generate
#         }
#     }

#     try:
#         # httpx.AsyncClient() is an async HTTP client
#         # We use it inside an "async with" block so it auto-closes
#         async with httpx.AsyncClient(timeout=120.0) as client:
#             # stream() sends the request and streams the response
#             async with client.stream(
#                 "POST",
#                 f"{OLLAMA_BASE_URL}/api/chat",
#                 json=payload
#             ) as response:

#                 if response.status_code != 200:
#                     yield f"Error: Ollama returned status {response.status_code}. Is Ollama running?"
#                     return

#                 # Read the response line by line
#                 async for line in response.aiter_lines():
#                     if not line:
#                         continue  # Skip empty lines

#                     try:
#                         # Each line is a JSON object
#                         data = json.loads(line)

#                         # Extract the text token from the response
#                         # Ollama's chat API returns: {"message": {"content": "Hello"}, "done": false}
#                         if "message" in data and "content" in data["message"]:
#                             token = data["message"]["content"]
#                             if token:
#                                 yield token  # Send this token to the caller

#                         # When done=True, we've received the full response
#                         if data.get("done", False):
#                             break

#                     except json.JSONDecodeError:
#                         continue  # Skip malformed lines

#     except httpx.ConnectError:
#         yield (
#             "❌ Cannot connect to Ollama. Please make sure:\n"
#             "1. Ollama is installed: https://ollama.ai\n"
#             "2. Ollama is running: run 'ollama serve' in your terminal\n"
#             f"3. The model is downloaded: run 'ollama pull {model}'"
#         )
#     except Exception as e:
#         yield f"❌ Error calling Ollama: {str(e)}"


# # -----------------------------------------------------------------------------
# # Non-streaming version (simpler, but slower UI experience)
# # -----------------------------------------------------------------------------
# async def get_ollama_response(
#     messages: List[dict],
#     model: str = DEFAULT_MODEL
# ) -> str:
#     """
#     Sends the prompt to Ollama and waits for the complete response.
#     Use this when you don't need streaming (e.g., for testing).
#     """
#     full_response = ""
#     async for token in stream_ollama_response(messages, model):
#         full_response += token
#     return full_response


# # -----------------------------------------------------------------------------
# # Check if Ollama is running
# # -----------------------------------------------------------------------------
# async def check_ollama_status() -> dict:
#     """Pings Ollama to see if it's running and which models are available."""
#     try:
#         async with httpx.AsyncClient(timeout=5.0) as client:
#             response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
#             if response.status_code == 200:
#                 models = [m["name"] for m in response.json().get("models", [])]
#                 return {"running": True, "models": models}
#     except Exception:
#         pass

#     return {"running": False, "models": []}



# =============================================================================
# llm_service.py — Talks to Groq's cloud LLM API (replaces local Ollama)
# =============================================================================
#
# WHY GROQ INSTEAD OF OLLAMA FOR DEPLOYMENT?
# Ollama needs real CPU/RAM and runs ON your machine. Free cloud hosting
# (Render, Railway, etc.) doesn't give you enough resources to run an LLM
# yourself. Groq solves this: it's a cloud API that runs open models like
# Llama 3 for you, FOR FREE (generous daily limits), and is extremely fast.
#
# THE BIG IDEA: Groq's API is "OpenAI-compatible" — meaning it expects almost
# the exact same request format as OpenAI's API. This is an industry-wide
# convention, so this same pattern would work for many other providers too.
#
# WHAT IS RAG? (unchanged from before)
# Retrieval-Augmented Generation — we RETRIEVE relevant chunks from FAISS,
# AUGMENT the prompt with those chunks, and GENERATE an answer grounded
# in that context.
# =============================================================================

import httpx
from typing import List, AsyncGenerator
import json
import os

# -----------------------------------------------------------------------------
# Configuration — reads the API key from an environment variable
# -----------------------------------------------------------------------------
# WHY AN ENVIRONMENT VARIABLE INSTEAD OF HARDCODING THE KEY?
# Never put secret keys directly in your code! If you push this to GitHub,
# anyone could steal your key and use up your free quota (or worse, run up
# a bill if it's a paid plan). Environment variables keep secrets OUT of
# your source code. On Render, you'll set this in the dashboard (Step 4).
# Locally, you set it in a ".env" file that's excluded from git.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Groq's API endpoint — note it's "OpenAI-compatible", ending in /chat/completions
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Groq's hosted model name for Llama 3
# (Other free options on Groq: "mixtral-8x7b-32768", "gemma2-9b-it")
DEFAULT_MODEL = "llama3-8b-8192"


# -----------------------------------------------------------------------------
# Build the RAG prompt — IDENTICAL to the Ollama version, unchanged
# -----------------------------------------------------------------------------
def build_rag_prompt(
    question: str,
    context_chunks: List[str],
    chat_history: List[dict]
) -> List[dict]:
    """
    Constructs the message list to send to the LLM.
    This function is UNCHANGED from the Ollama version — RAG prompt
    construction has nothing to do with which LLM provider you use.
    """
    if context_chunks:
        context_text = "\n\n---\n\n".join([
            f"[Source chunk {i+1}]:\n{chunk}"
            for i, chunk in enumerate(context_chunks)
        ])
    else:
        context_text = "No relevant context found in the uploaded documents."

    system_message = {
        "role": "system",
        "content": (
            "You are a helpful AI assistant that answers questions based on "
            "the provided document context. Follow these rules:\n\n"
            "1. ONLY answer using the information from the provided context.\n"
            "2. If the context doesn't contain the answer, say: "
            "'I couldn't find information about that in the uploaded documents.'\n"
            "3. Be concise and clear.\n"
            "4. If quoting from the document, mention it.\n"
            "5. Do not make up information.\n\n"
            f"Here is the relevant context from the user's documents:\n\n"
            f"{context_text}"
        )
    }

    messages = [system_message]

    for msg in chat_history[-10:]:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    messages.append({
        "role": "user",
        "content": question
    })

    return messages


# -----------------------------------------------------------------------------
# Call Groq's API (streaming) — THIS is the function that changed
# -----------------------------------------------------------------------------
async def stream_ollama_response(
    messages: List[dict],
    model: str = DEFAULT_MODEL
) -> AsyncGenerator[str, None]:
    """
    NOTE: kept the function name "stream_ollama_response" so chat.py (the
    router that calls this) doesn't need ANY changes — only this file
    changes internally. This is a good software design lesson: routers
    depend on a stable function signature, not on which provider is behind it.

    Sends the prompt to Groq and streams back the response token by token,
    exactly like we did with Ollama — just a different URL and auth header.
    """
    if not GROQ_API_KEY:
        yield (
            "❌ GROQ_API_KEY is not set. \n\n"
            "If running locally: create a .env file with GROQ_API_KEY=your_key_here\n"
            "If deployed on Render: add GROQ_API_KEY in the Environment tab of your service."
        )
        return

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 1024,
    }

    headers = {
        # Groq uses standard "Bearer token" authentication —
        # the same pattern used by OpenAI, Stripe, GitHub, and most modern APIs.
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{GROQ_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
            ) as response:

                if response.status_code != 200:
                    error_body = await response.aread()
                    yield f"Error: Groq returned status {response.status_code}. {error_body.decode()}"
                    return

                # Groq streams responses in OpenAI's "Server-Sent Events" format:
                # each line looks like: data: {"choices": [{"delta": {"content": "Hello"}}]}
                # and the very last line is: data: [DONE]
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:]  # remove "data: " prefix

                    if data_str.strip() == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield token
                    except json.JSONDecodeError:
                        continue

    except httpx.ConnectError:
        yield "❌ Cannot connect to Groq. Check your internet connection."
    except Exception as e:
        yield f"❌ Error calling Groq: {str(e)}"


# -----------------------------------------------------------------------------
# Non-streaming version (unchanged interface)
# -----------------------------------------------------------------------------
async def get_ollama_response(
    messages: List[dict],
    model: str = DEFAULT_MODEL
) -> str:
    full_response = ""
    async for token in stream_ollama_response(messages, model):
        full_response += token
    return full_response


# -----------------------------------------------------------------------------
# Check if the API key is configured (replaces the old "is Ollama running" check)
# -----------------------------------------------------------------------------
async def check_ollama_status() -> dict:
    """Checks whether GROQ_API_KEY is set — our equivalent of an Ollama health check."""
    return {
        "running": bool(GROQ_API_KEY),
        "models": [DEFAULT_MODEL] if GROQ_API_KEY else [],
    }