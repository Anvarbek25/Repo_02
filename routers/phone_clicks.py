"""
routers/phone_clicks.py

Endpoints:
  POST /api/phone-clicks  — public, records one click per IP per Melbourne day
  GET  /api/phone-clicks  — token protected, returns records by date range
"""

from fastapi import APIRouter, Request, Depends, Query, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import date
from database import get_connection
from auth import require_token
from utils import get_client_ip

router = APIRouter(prefix="/api/phone-clicks", tags=["Phone Clicks"])


# ─── POST /api/phone-clicks ──────────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
def record_phone_click(request: Request):
    """
    Records a phone button click from the website.

    Extracts the visitor IP automatically.
    Stores a maximum of one record per IP per Melbourne calendar day.
    Duplicate clicks are silently discarded — returns 200 instead of 201.
    """
    ip = get_client_ip(request)

    conn = get_connection()
    try:
        cur = conn.cursor()

        # Check if this IP already has a record for today (Melbourne date)
        cur.execute(
            """
            SELECT id FROM phone_clicks
            WHERE ip_address = %s
              AND (clicked_at AT TIME ZONE 'Australia/Melbourne')::date = 
                  (NOW() AT TIME ZONE 'Australia/Melbourne')::date
            LIMIT 1
            """,
            (ip,),
        )
        existing = cur.fetchone()

        if existing:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": "duplicate", "message": "Already recorded for today"},
            )

        cur.execute(
            "INSERT INTO phone_clicks (ip_address, clicked_at) VALUES (%s, NOW())",
            (ip,),
        )
        conn.commit()

        return {"status": "recorded", "message": "Click recorded successfully"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ─── GET /api/phone-clicks ───────────────────────────────────────────────────
@router.get("")
def get_phone_clicks(
    start: date = Query(..., description="Start date inclusive (YYYY-MM-DD)"),
    end:   date = Query(..., description="End date inclusive (YYYY-MM-DD)"),
    page:  int  = Query(1,   ge=1,         description="Page number"),
    limit: int  = Query(100, ge=1, le=500, description="Records per page (max 500)"),
    _token: str = Depends(require_token),
):
    """
    Returns phone click records filtered by date range.
    Dates are matched against Melbourne local time.
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
            SELECT COUNT(*) AS total FROM phone_clicks
            WHERE (clicked_at AT TIME ZONE 'Australia/Melbourne')::date BETWEEN %s AND %s
            """,
            (start, end),
        )
        total = cur.fetchone()["total"]

        cur.execute(
            """
            SELECT
                id,
                ip_address,
                clicked_at AT TIME ZONE 'Australia/Melbourne' AS clicked_at
            FROM phone_clicks
            WHERE (clicked_at AT TIME ZONE 'Australia/Melbourne')::date BETWEEN %s AND %s
            ORDER BY clicked_at DESC
            LIMIT %s OFFSET %s
            """,
            (start, end, limit, offset),
        )
        rows = cur.fetchall()

        records = []
        for r in rows:
            records.append({
                "id":         r["id"],
                "ip_address": r["ip_address"],
                "clicked_at": r["clicked_at"].isoformat() if r["clicked_at"] else None,
            })

        return {"total": total, "page": page, "limit": limit, "data": records}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cur.close()
        conn.close()
