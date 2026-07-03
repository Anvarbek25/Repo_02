"""
utils.py
Shared utility functions used across all routers.
"""

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """
    Extracts the real client IP address from the incoming request.

    When the API runs behind Render's reverse proxy (which it always does),
    the actual visitor IP is forwarded via the X-Forwarded-For header.
    The header can contain a chain: "client_ip, proxy1_ip, proxy2_ip"
    — we always want the first value (the original client).

    Falls back to the direct connection IP if the header is absent
    (useful for local development).
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host
