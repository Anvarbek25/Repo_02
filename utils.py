"""
utils.py
Shared utility functions used across the API.
"""

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """
    Extracts the real client IP address from the request.

    When running behind a reverse proxy or cloud load balancer,
    the actual client IP is forwarded in the X-Forwarded-For header.
    If that header is absent, we fall back to the direct connection IP.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain a chain of IPs: "client, proxy1, proxy2"
        # The first one is always the original client
        return forwarded_for.split(",")[0].strip()
    return request.client.host
