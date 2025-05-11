# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.database import create_db_and_tables #, populate_initial_citations
from backend.api import chat, citation # Import router objects

import os
from dotenv import load_dotenv
env_path = os.path.abspath(".env")
# print("Loading .env from:", env_path)
load_dotenv(env_path)

# Create DB tables on startup if they don't exist
create_db_and_tables()
# Populate initial citation data if needed
# populate_initial_citations()


# Initialize FastAPI app
app = FastAPI(
    title="Chat App Backend API",
    description="API for managing chat sessions, messages, and citations.",
    version="0.1.0",
)
BACKEND_PORT= int(os.getenv("BACKEND_PORT", 8000)) # Default to 8000 if PORT not set in .env
# print(f"Port used: {BACKEND_PORT} \t{os.environ['BACKEND_PORT']}")
# --- CORS Middleware ---
# Allow requests from your Streamlit app's origin (e.g., http://localhost:8501)
# Use "*" for development, but restrict in production!
origins = [
    "http://localhost",         # Allow localhost (any port)
    "http://localhost:8501",    # Default Streamlit port
    "http://127.0.0.1",       # Allow loopback (any port)
    "http://127.0.0.1:8501",  # Explicit loopback for Streamlit
    # Add deployed Streamlit app URL in production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"], # Allows all headers
)

# --- Include Routers ---
app.include_router(chat.router)
app.include_router(citation.router)

# --- Root Endpoint (Optional) ---
@app.get("/")
async def read_root():
    """Simple root endpoint to check if the API is running."""
    return {"message": "Welcome to the Chat App Backend API!"}

if __name__ == "__main__":
    # Active .venv and run `python .\backend\main.py`
    import uvicorn
    uvicorn.run(app, host="localhost", port=BACKEND_PORT, log_level="info")

# --- Run in CMD -> comment all of the `if __name__ == "__main__":` ---
# uvicorn chat_backend.main:app --reload --port 8000 # --host 0.0.0.0 , etc.
# Reload works with the CMD command
