"""
routers/enquiries.py

Endpoints:
  POST /api/enquiries  — public, logs IP + timestamp only (no body required)
                         Email is handled entirely by EmailJS on the frontend.
  GET  /api/enquiries  — token protected, returns anonymous log for analytics
"""

from fastapi import APIRouter, Request, Depends, Query, HTTPException, status
from datetime import date
from database import get_connection
from auth import require_token
from utils import get_client_ip

router = APIRouter(prefix="/api/enquiries", tags=["Enquiries"])


# ─── POST /api/enquiries ─────────────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
def log_enquiry(request: Request):
    """
    Fire-and-forget endpoint called by the frontend after EmailJS succeeds.
    No request body required — just logs the IP address and timestamp.
    Max 10 logs per IP per Melbourne day.
    """
    ip = get_client_ip(request)

    conn = get_connection()
    try:
        cur = conn.cursor()

        # Rate limit check
        cur.execute(
            """
            SELECT COUNT(*) AS daily_count FROM enquiries
            WHERE ip_address = %s
              AND (submitted_at AT TIME ZONE 'Australia/Melbourne')::date =
                  (NOW() AT TIME ZONE 'Australia/Melbourne')::date
            """,
            (ip,),
        )
        count = cur.fetchone()["daily_count"]

        if count >= 10:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded.",
            )

        cur.execute(
            "INSERT INTO enquiries (ip_address, submitted_at) VALUES (%s, NOW())",
            (ip,),
        )
        conn.commit()

        return {"status": "logged"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ─── GET /api/enquiries ──────────────────────────────────────────────────────
@router.get("")
def get_enquiries(
    start: date = Query(..., description="Start date inclusive (YYYY-MM-DD)"),
    end:   date = Query(..., description="End date inclusive (YYYY-MM-DD)"),
    page:  int  = Query(1,  ge=1,         description="Page number"),
    limit: int  = Query(50, ge=1, le=200, description="Records per page (max 200)"),
    _token: str = Depends(require_token),
):
    """
    Returns anonymous enquiry log filtered by date range.
    Requires Bearer token authentication.
    """
    if end < start:
        raise HTTPException(status_code=400, detail="'end' date must be on or after 'start' date")

    offset = (page - 1) * limit

    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT COUNT(*) AS total FROM enquiries
            WHERE (submitted_at AT TIME ZONE 'Australia/Melbourne')::date BETWEEN %s AND %s
            """,
            (start, end),
        )
        total = cur.fetchone()["total"]

        cur.execute(
            """
            SELECT
                id,
                ip_address,
                submitted_at AT TIME ZONE 'Australia/Melbourne' AS submitted_at
            FROM enquiries
            WHERE (submitted_at AT TIME ZONE 'Australia/Melbourne')::date BETWEEN %s AND %s
            ORDER BY submitted_at DESC
            LIMIT %s OFFSET %s
            """,
            (start, end, limit, offset),
        )
        rows = cur.fetchall()

        records = []
        for r in rows:
            records.append({
                "id":           r["id"],
                "ip_address":   r["ip_address"],
                "submitted_at": r["submitted_at"].isoformat() if r["submitted_at"] else None,
            })

        return {"total": total, "page": page, "limit": limit, "data": records}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cur.close()
        conn.close()
