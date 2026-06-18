# =============================================================================
# pdf_service.py — The brain of our PDF processing pipeline
# =============================================================================
#
# WHAT HAPPENS WHEN YOU UPLOAD A PDF?
#
#  PDF File
#    │
#    ▼
#  [Step 1] Extract raw text using PyMuPDF
#    │
#    ▼
#  [Step 2] Split text into chunks (small pieces ~500 words each)
#    │
#    ▼
#  [Step 3] Convert each chunk into a vector (list of 384 numbers)
#             using sentence-transformers/all-MiniLM-L6-v2
#    │
#    ▼
#  [Step 4] Store all vectors in FAISS (a fast vector search database)
#    │
#    ▼
#  Ready to answer questions!
#
# WHY CHUNKS? Because LLMs have a limited "context window" (they can only
# read so much text at once). We break the PDF into small pieces and only
# send the RELEVANT pieces to the LLM.
#
# WHY VECTORS? Because we can't search text by meaning using simple string
# matching. Vectors let us find "semantically similar" chunks.
# =============================================================================

import re

import fitz  # PyMuPDF — extracts text from PDFs
import faiss  # Facebook AI Similarity Search — vector database
import numpy as np  # NumPy — for working with arrays of numbers
from sentence_transformers import SentenceTransformer  # Creates embeddings
from typing import List, Tuple
import os
import pickle  # For saving Python objects to disk

# -----------------------------------------------------------------------------
# GLOBAL STATE
# In a production app you'd use a real database, but for learning,
# we keep everything in memory (Python variables).
# -----------------------------------------------------------------------------

# The embedding model — loads once when the server starts.
# "all-MiniLM-L6-v2" is a small but powerful model (only 90MB).
# It converts text into 384-dimensional vectors.
print("⏳ Loading embedding model... (this takes ~10 seconds the first time)")
embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
print("✅ Embedding model loaded!")

# FAISS index — our vector database
# None means "not created yet" — it's created after the first PDF upload
faiss_index = None

# We also store the original text chunks so we can return them to the LLM.
# FAISS only stores vectors, not text, so we maintain a parallel list.
text_chunks: List[str] = []

# Track which PDF filenames have been processed
processed_files: List[str] = []

# Dimension of our embedding vectors (all-MiniLM-L6-v2 produces 384 numbers)
EMBEDDING_DIM = 384

# -----------------------------------------------------------------------------
# STEP 1: Extract text from PDF
# -----------------------------------------------------------------------------
def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Takes raw PDF bytes and returns all the text as a single string.

    PyMuPDF (imported as 'fitz') opens PDFs and lets us read each page.

    Example:
        Input:  b'%PDF-1.4...' (raw PDF bytes)
        Output: "Introduction\nThis paper explores..."
    """
    # Open the PDF from bytes (not from a file path)
    # fitz.open() can accept bytes using the stream parameter
    pdf_document = fitz.open(stream=file_bytes, filetype="pdf")

    full_text = ""

    # Loop through every page and extract its text
    for page_number in range(len(pdf_document)):
        page = pdf_document[page_number]

        # get_text() returns the text content of the page as a string
        page_text = page.get_text()

        full_text += page_text + "\n"  # Add newline between pages

    pdf_document.close()

    return full_text


# -----------------------------------------------------------------------------
# STEP 2: Split text into chunks
# -----------------------------------------------------------------------------
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Splits a long text into smaller overlapping chunks.

    WHY OVERLAP?
    Imagine the answer to a question spans the boundary between two chunks.
    Without overlap, you'd lose that context. With overlap, the same sentences
    appear in both the previous and the next chunk, so the answer is captured.

    Example (chunk_size=10, overlap=3):
        Text:   "The quick brown fox jumps over the lazy dog"
        Words:  [The, quick, brown, fox, jumps, over, the, lazy, dog]
        Chunk1: "The quick brown fox jumps over the lazy dog"  ← 9 words, fits!

    With longer texts:
        Chunk1: words 0-9
        Chunk2: words 7-16   ← starts 3 words back (the overlap)
        Chunk3: words 14-23
        ...

    Args:
        text:       The full text extracted from the PDF
        chunk_size: How many words per chunk (500 is a good balance)
        overlap:    How many words to repeat between consecutive chunks
    """
    # Split text into individual words
    words = text.split()

    chunks = []
    start_index = 0

    while start_index < len(words):
        # Take `chunk_size` words starting from `start_index`
        end_index = start_index + chunk_size
        chunk_words = words[start_index:end_index]

        # Join the words back into a string
        chunk_text_str = " ".join(chunk_words)

        # Only add non-empty chunks
        bad_chars = chunk_text_str.count("�")

        if chunk_text_str.strip() and bad_chars < 5:
            chunks.append(chunk_text_str)

        # Move forward by (chunk_size - overlap) words
        # This creates the overlapping effect
        start_index += chunk_size - overlap

    return chunks


# -----------------------------------------------------------------------------
# STEP 3: Generate embeddings (convert text → vectors)
# -----------------------------------------------------------------------------
def generate_embeddings(chunks: List[str]) -> np.ndarray:
    """
    Converts a list of text chunks into a 2D array of vectors.

    WHAT IS AN EMBEDDING?
    An embedding is a list of numbers (a vector) that represents the
    MEANING of a piece of text in mathematical space.

    Example:
        "The cat sat on the mat"  →  [0.12, -0.45, 0.89, ..., 0.23]  (384 numbers)
        "A feline rested on a rug" → [0.13, -0.44, 0.87, ..., 0.21]  (384 numbers)

    These two sentences have SIMILAR vectors because they mean similar things!
    This is how we can find relevant chunks using "semantic search."

    The model: sentence-transformers/all-MiniLM-L6-v2
        - "L6" means 6 transformer layers (small and fast)
        - "v2" means version 2
        - Produces 384-dimensional vectors
        - FREE, runs locally, no API key needed!

    Returns:
        A numpy array of shape (num_chunks, 384)
        Each row is the embedding for one chunk.
    """
    # encode() processes all chunks in batch (faster than one by one)
    # convert_to_numpy=True returns numpy array instead of PyTorch tensor
    embeddings = embedding_model.encode(chunks, convert_to_numpy=True)

    return embeddings


# -----------------------------------------------------------------------------
# STEP 4: Store vectors in FAISS
# -----------------------------------------------------------------------------
def store_in_faiss(embeddings: np.ndarray, chunks: List[str]) -> None:
    """
    Adds new embeddings to the FAISS index and saves the text chunks.

    WHAT IS FAISS?
    FAISS (Facebook AI Similarity Search) is a library for efficiently
    searching through millions of vectors to find the most similar ones.

    ANALOGY: Imagine you have 10,000 book summaries as vectors.
    When you search for "machine learning books," FAISS quickly finds
    the top 5 most similar vectors — much faster than comparing each one.

    INDEX TYPE: IndexFlatL2
        - "Flat" = stores all vectors as-is (no compression)
        - "L2"   = uses Euclidean distance to measure similarity
        - Good for learning; for production use IndexIVFFlat (faster)
    """
    global faiss_index, text_chunks

    # FAISS needs float32 (32-bit floats), not float64
    embeddings = embeddings.astype(np.float32)

    if faiss_index is None:
        # First time: create a new index
        # IndexFlatL2(EMBEDDING_DIM) creates an index for 384-dimensional vectors
        faiss_index = faiss.IndexFlatL2(EMBEDDING_DIM)
        print(f"✅ Created new FAISS index (dimension={EMBEDDING_DIM})")

    # Add vectors to the index
    faiss_index.add(embeddings)

    # Save the text chunks (parallel to the vectors)
    text_chunks.extend(chunks)

    print(f"✅ Added {len(chunks)} chunks. Total chunks in index: {len(text_chunks)}")


# -----------------------------------------------------------------------------
# STEP 5: Search FAISS for relevant chunks
# -----------------------------------------------------------------------------
def search_similar_chunks(query: str, top_k: int = 4) -> List[str]:
    """
    Given a user's question, finds the most relevant text chunks.

    HOW IT WORKS:
    1. Convert the question into a vector (using the same model as before)
    2. Search the FAISS index for the closest vectors
    3. Return the corresponding text chunks

    WHY THE SAME MODEL?
    Both the PDF chunks AND the user's question must be embedded with
    the SAME model. Otherwise, the vectors would be in different "spaces"
    and the similarity search wouldn't work.

    Args:
        query:  The user's question (e.g., "What is the main finding?")
        top_k:  How many chunks to retrieve (4 is usually enough)

    Returns:
        A list of the most relevant text chunks
    """
    if faiss_index is None or faiss_index.ntotal == 0:
        return []  # No PDFs uploaded yet

    # Embed the question
    query_embedding = embedding_model.encode([query], convert_to_numpy=True)
    query_embedding = query_embedding.astype(np.float32)

    # Search FAISS
    # .search() returns:
    #   distances: how far each result is (lower = more similar)
    #   indices:   which chunks in our list are the results
    distances, indices = faiss_index.search(query_embedding, top_k)

    # Retrieve the actual text for each matching index
    relevant_chunks = []
    for idx in indices[0]:  # indices[0] because query_embedding is 2D
        if 0 <= idx < len(text_chunks):  # Safety check
            relevant_chunks.append(text_chunks[idx])
    print("\n===== RETRIEVED CHUNKS =====")

    for i, chunk in enumerate(relevant_chunks):
        print(f"\nChunk {i+1}:")
        print(chunk[:1000])

    print("============================\n")
    return relevant_chunks


# -----------------------------------------------------------------------------
# MAIN PIPELINE: Process a PDF file end-to-end
# -----------------------------------------------------------------------------
async def process_pdf(file_bytes: bytes, filename: str) -> dict:
    """
    Runs the full pipeline:  PDF → Text → Chunks → Embeddings → FAISS

    This is the function called by our upload API endpoint.

    Returns a dict with stats about what was processed.
    """
    print(f"\n📄 Processing: {filename}")

    # Step 1: Extract text
    print("  [1/4] Extracting text from PDF...")
    raw_text = extract_text_from_pdf(file_bytes)
    import re

    # Remove non-printable Unicode characters
    raw_text = re.sub(r'[^\x20-\x7E\n\r\t]', ' ', raw_text)

    # Remove extra spaces
    raw_text = re.sub(r'\s+', ' ', raw_text)
    if not raw_text.strip():
        raise ValueError("The PDF appears to be empty or contains only images (no extractable text).")

    print(f"  ✅ Extracted {len(raw_text)} characters")

    # Step 2: Chunk the text
    print("  [2/4] Splitting text into chunks...")
    chunks = chunk_text(raw_text, chunk_size=500, overlap=50)
    print(f"  ✅ Created {len(chunks)} chunks")

    # Step 3: Generate embeddings
    print("  [3/4] Generating embeddings (this may take a moment)...")
    embeddings = generate_embeddings(chunks)
    print(f"  ✅ Generated embeddings of shape {embeddings.shape}")

    # Step 4: Store in FAISS
    print("  [4/4] Storing in FAISS vector database...")
    store_in_faiss(embeddings, chunks)

    # Track the filename
    processed_files.append(filename)

    print(f"  🎉 Done! {filename} is ready for questions.\n")

    return {
        "filename": filename,
        "characters_extracted": len(raw_text),
        "chunks_created": len(chunks),
        "total_chunks_in_index": len(text_chunks),
    }


def get_status() -> dict:
    """Returns the current state of the vector database."""
    return {
        "total_chunks": len(text_chunks),
        "processed_files": processed_files,
        "index_ready": faiss_index is not None,
    }
