"""
routers/phone_clicks.py

Endpoints:
  POST /api/phone-clicks  — public, records one click per IP per Melbourne day
  GET  /api/phone-clicks  — token protected, returns records by date range
"""

from fastapi import APIRouter, Request, Depends, Query, HTTPException, status
from datetime import date
from database import get_connection
from auth import require_token
from utils import get_client_ip

router = APIRouter(prefix="/api/phone-clicks", tags=["Phone Clicks"])


# ─── POST /api/phone-clicks ──────────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
def record_phone_click(request: Request):
    """
    Records a phone call button click from the website.

    - Extracts the visitor's IP address automatically
    - Checks if this IP has already been recorded today (Melbourne time)
    - If yes: returns 200 without inserting a duplicate
    - If no:  inserts a new record and returns 201
    """
    ip = get_client_ip(request)

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        # Check for an existing record from this IP today (Melbourne date)
        cursor.execute(
            """
            SELECT id FROM PhoneClicks
            WHERE ip_address = %s
              AND DATE(clicked_at) = DATE(CONVERT_TZ(NOW(), 'UTC', 'Australia/Melbourne'))
            LIMIT 1
            """,
            (ip,),
        )
        existing = cursor.fetchone()

        if existing:
            # Already recorded today — return 200 silently, no duplicate inserted
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": "duplicate", "message": "Already recorded for today"},
            )

        # Insert new click record
        cursor.execute(
            """
            INSERT INTO PhoneClicks (ip_address, clicked_at)
            VALUES (%s, CONVERT_TZ(NOW(), 'UTC', 'Australia/Melbourne'))
            """,
            (ip,),
        )
        conn.commit()

        return {"status": "recorded", "message": "Click recorded successfully"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


# ─── GET /api/phone-clicks ───────────────────────────────────────────────────
@router.get("")
def get_phone_clicks(
    start: date = Query(..., description="Start date inclusive (YYYY-MM-DD)"),
    end: date   = Query(..., description="End date inclusive (YYYY-MM-DD)"),
    page: int   = Query(1,   ge=1,   description="Page number"),
    limit: int  = Query(100, ge=1, le=500, description="Records per page (max 500)"),
    _token: str = Depends(require_token),
):
    """
    Returns phone click records filtered by date range.
    Requires Bearer token authentication.
    """
    if end < start:
        raise HTTPException(status_code=400, detail="'end' date must be on or after 'start' date")

    offset = (page - 1) * limit

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        # Total count for pagination metadata
        cursor.execute(
            """
            SELECT COUNT(*) AS total FROM PhoneClicks
            WHERE DATE(clicked_at) BETWEEN %s AND %s
            """,
            (start, end),
        )
        total = cursor.fetchone()["total"]

        # Paginated records
        cursor.execute(
            """
            SELECT id, ip_address, clicked_at
            FROM PhoneClicks
            WHERE DATE(clicked_at) BETWEEN %s AND %s
            ORDER BY clicked_at DESC
            LIMIT %s OFFSET %s
            """,
            (start, end, limit, offset),
        )
        records = cursor.fetchall()

        # Convert datetime objects to ISO strings for JSON serialisation
        for r in records:
            if r["clicked_at"]:
                r["clicked_at"] = r["clicked_at"].isoformat()

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "data": records,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()
