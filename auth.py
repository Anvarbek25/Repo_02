"""
auth.py
Bearer token authentication dependency for protected endpoints.

How it works:
  - Protected endpoints declare `token: str = Depends(require_token)`
  - FastAPI automatically extracts the Authorization header
  - If the token matches ADMIN_TOKEN in .env, the request proceeds
  - Otherwise a 401 Unauthorized response is returned immediately
"""

import os
from fastapi import Header, HTTPException, status
from dotenv import load_dotenv

load_dotenv()

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")


def require_token(authorization: str = Header(...)):
    """
    FastAPI dependency that validates the Bearer token.
    Add `token: str = Depends(require_token)` to any endpoint
    that should be protected.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected: Bearer <token>",
        )

    token = authorization.split(" ", 1)[1]

    if token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return token
