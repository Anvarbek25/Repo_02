"""
main.py
Bahafix Backend API v2.0 — Entry Point

─── Local development ────────────────────────────────────────────────────────
  1. Copy .env.example to .env and fill in your values
  2. pip install -r requirements.txt
  3. uvicorn main:app --host 0.0.0.0 --port 8000 --reload
  4. Visit http://localhost:8000/docs to test all endpoints interactively

─── Render deployment ────────────────────────────────────────────────────────
  Start command: uvicorn main:app --host 0.0.0.0 --port $PORT
  Environment variables: set in Render dashboard (not .env file)
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import phone_clicks, enquiries, blogs

load_dotenv()

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Bahafix API",
    description=(
        "Backend API for the Bahafix carpentry and property maintenance website.\n\n"
        "**Protected endpoints** require a Bearer token in the `Authorization` header:\n"
        "`Authorization: Bearer <your_admin_token>`\n\n"
        "Click the 🔒 **Authorize** button above to enter your token once and test all endpoints."
    ),
    version="2.0.0",
)

# ─── CORS ────────────────────────────────────────────────────────────────────
# Only the listed origins can call this API from a browser.
# The Render-assigned URL is included for testing before a custom domain is set.
allowed_origins = [
    os.getenv("FRONTEND_ORIGIN", "https://bahafix.com.au"),
    "http://localhost:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(phone_clicks.router)
app.include_router(enquiries.router)
app.include_router(blogs.router)


# ─── Health check ────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def health_check():
    """
    Confirms the API is running.
    Visit <your-render-url>/ or http://localhost:8000/ after starting the server.
    """
    return {
        "status": "ok",
        "service": "Bahafix API",
        "version": "2.0.0",
    }
