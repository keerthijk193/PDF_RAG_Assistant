# # =============================================================================
# # main.py — The entry point of our FastAPI backend
# # =============================================================================
# # FastAPI is a Python web framework that lets us create HTTP endpoints (URLs)
# # that the React frontend can call to send/receive data.
# #
# # HOW IT WORKS:
# #   Browser → HTTP Request → FastAPI → Process → HTTP Response → Browser
# # =============================================================================

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# # Import our route handlers (we'll define these in separate files)
# from routers import chat, upload

# # -----------------------------------------------------------------------------
# # Create the FastAPI application instance
# # Think of this as creating the "server object"
# # -----------------------------------------------------------------------------
# app = FastAPI(
#     title="RAG AI Assistant",
#     description="A ChatGPT-like assistant that answers questions from your PDFs",
#     version="1.0.0"
# )

# # -----------------------------------------------------------------------------
# # CORS (Cross-Origin Resource Sharing) Middleware
# # -----------------------------------------------------------------------------
# # PROBLEM: By default, browsers block requests from one domain to another.
# #   - Our React app runs at: http://localhost:5173
# #   - Our FastAPI runs at:   http://localhost:8000
# #   - These are DIFFERENT origins → browser blocks the request
# #
# # SOLUTION: Tell FastAPI to allow requests from our React app's origin.
# # -----------------------------------------------------------------------------
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173"],  # React dev server URL
#     allow_credentials=True,
#     allow_methods=["*"],   # Allow GET, POST, PUT, DELETE, etc.
#     allow_headers=["*"],   # Allow any headers
# )

# # -----------------------------------------------------------------------------
# # Register routers
# # A "router" groups related endpoints together (like /chat/* and /upload/*)
# # -----------------------------------------------------------------------------
# app.include_router(upload.router, prefix="/api", tags=["Upload"])
# app.include_router(chat.router, prefix="/api", tags=["Chat"])

# # -----------------------------------------------------------------------------
# # Health check endpoint — useful to verify the server is running
# # -----------------------------------------------------------------------------
# @app.get("/")
# async def root():
#     return {"status": "running", "message": "RAG Assistant API is live!"}

# # -----------------------------------------------------------------------------
# # HOW TO RUN THIS FILE:
# #   uvicorn main:app --reload --port 8000
# #
# #   "uvicorn" = the server that runs our FastAPI app
# #   "main:app" = look in main.py for the object named "app"
# #   "--reload"  = auto-restart when you edit code (great for development)
# #   "--port 8000" = listen on port 8000
# # -----------------------------------------------------------------------------

# =============================================================================
# main.py — The entry point of our FastAPI backend
# =============================================================================
# FastAPI is a Python web framework that lets us create HTTP endpoints (URLs)
# that the React frontend can call to send/receive data.
#
# HOW IT WORKS:
#   Browser → HTTP Request → FastAPI → Process → HTTP Response → Browser
# =============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables from a local .env file (e.g. GROQ_API_KEY).
# On Render, this line does nothing harmful — Render injects env vars
# directly, so there's no .env file there, and load_dotenv() just no-ops.
load_dotenv()

# Import our route handlers (we'll define these in separate files)
from routers import chat, upload

# -----------------------------------------------------------------------------
# Create the FastAPI application instance
# Think of this as creating the "server object"
# -----------------------------------------------------------------------------
app = FastAPI(
    title="RAG AI Assistant",
    description="A ChatGPT-like assistant that answers questions from your PDFs",
    version="1.0.0"
)

# -----------------------------------------------------------------------------
# CORS (Cross-Origin Resource Sharing) Middleware
# -----------------------------------------------------------------------------
# PROBLEM: By default, browsers block requests from one domain to another.
#   - Locally:  React runs at http://localhost:5173, FastAPI at :8000
#   - Deployed: React runs at https://your-app.vercel.app, FastAPI on Render
#   - These are DIFFERENT origins → browser blocks the request unless we allow it
#
# SOLUTION: Read the deployed frontend URL from an environment variable
# (FRONTEND_URL), and always also allow localhost so local development
# still works. Set FRONTEND_URL on Render after you deploy the frontend.
# -----------------------------------------------------------------------------
allowed_origins = ["http://localhost:5173"]

deployed_frontend_url = os.environ.get("FRONTEND_URL", "")
if deployed_frontend_url:
    allowed_origins.append(deployed_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],   # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],   # Allow any headers
)

# -----------------------------------------------------------------------------
# Register routers
# A "router" groups related endpoints together (like /chat/* and /upload/*)
# -----------------------------------------------------------------------------
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])

# -----------------------------------------------------------------------------
# Health check endpoint — useful to verify the server is running
# -----------------------------------------------------------------------------
@app.get("/")
async def root():
    return {"status": "running", "message": "RAG Assistant API is live!"}

# -----------------------------------------------------------------------------
# HOW TO RUN THIS FILE:
#   uvicorn main:app --reload --port 8000
#
#   "uvicorn" = the server that runs our FastAPI app
#   "main:app" = look in main.py for the object named "app"
#   "--reload"  = auto-restart when you edit code (great for development)
#   "--port 8000" = listen on port 8000
# -----------------------------------------------------------------------------