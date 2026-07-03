"""
auth.py
Bearer token authentication dependency for protected endpoints.

Usage — add this to any endpoint that requires protection:
    from auth import require_token
    from fastapi import Depends

    @router.get("/something")
    def my_endpoint(_token: str = Depends(require_token)):
        ...

FastAPI will automatically extract the Authorization header,
validate the token, and return 401 if it's missing or wrong.
The endpoint function only runs if the token is valid.
"""

import os
from fastapi import Header, HTTPException, status
from dotenv import load_dotenv

load_dotenv()

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")


def require_token(authorization: str = Header(...)):
    """
    Validates the Bearer token from the Authorization header.
    Raises HTTP 401 if the token is missing, malformed, or incorrect.
    """
    if not ADMIN_TOKEN:
        raise RuntimeError("ADMIN_TOKEN environment variable is not set")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected: Bearer <token>",
        )

    token = authorization.split(" ", 1)[1].strip()

    if token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return token
