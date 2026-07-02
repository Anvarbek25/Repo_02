"""
main.py
Bahafix Backend API — Entry Point

Start the server:
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Interactive API docs (once running):
  http://localhost:8000/docs
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import phone_clicks, enquiries, blogs

load_dotenv()

# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Bahafix API",
    description=(
        "Backend API for the Bahafix website. "
        "Manages blog posts, customer enquiries, and phone click analytics. "
        "Protected endpoints require a Bearer token in the Authorization header."
    ),
    version="1.0.0",
)

# ─── CORS ────────────────────────────────────────────────────────────────────
# Only allows requests from the Bahafix frontend domain
# Change FRONTEND_ORIGIN in .env to match your actual domain
allowed_origins = [
    os.getenv("FRONTEND_ORIGIN", "https://bahafix.com.au"),
    "http://localhost:3000",   # for local frontend development
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
    Simple health check endpoint.
    Visit http://localhost:8000/ to confirm the API is running.
    """
    return {"status": "ok", "service": "Bahafix API", "version": "1.0.0"}
