"""
routers/enquiries.py

Endpoints:
  POST /api/enquiries  — public, stores enquiry, enforces IP rate limit
  GET  /api/enquiries  — token protected, returns records by date range
"""

from fastapi import APIRouter, Request, Depends, Query, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from datetime import date
from database import get_connection
from auth import require_token
from utils import get_client_ip

router = APIRouter(prefix="/api/enquiries", tags=["Enquiries"])


# ─── Request model ───────────────────────────────────────────────────────────
class EnquiryRequest(BaseModel):
    name:    str
    phone:   str
    email:   EmailStr
    message: str

    # Validators — FastAPI runs these automatically before the endpoint executes
    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        if len(v) > 255:
            raise ValueError("Name cannot exceed 255 characters")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def phone_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Phone cannot be empty")
        if len(v) > 50:
            raise ValueError("Phone cannot exceed 50 characters")
        return v.strip()

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Message cannot be empty")
        if len(v) > 400:
            raise ValueError("Message cannot exceed 400 characters")
        return v.strip()


# ─── POST /api/enquiries ─────────────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
def submit_enquiry(payload: EnquiryRequest, request: Request):
    """
    Accepts a customer contact form submission.

    - Validates all fields (FastAPI handles this via the EnquiryRequest model)
    - Checks IP rate limit: max 10 submissions per IP per Melbourne day
    - Stores the record with sent_at = NULL (email sent by background job)
    - Returns 429 if rate limit exceeded
    """
    ip = get_client_ip(request)

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        # Count how many enquiries this IP has submitted today (Melbourne date)
        cursor.execute(
            """
            SELECT COUNT(*) AS daily_count FROM Enquiries
            WHERE ip_address = %s
              AND DATE(submitted_at) = DATE(CONVERT_TZ(NOW(), 'UTC', 'Australia/Melbourne'))
            """,
            (ip,),
        )
        count = cursor.fetchone()["daily_count"]

        if count >= 10:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum enquiries reached for today from this location.",
            )

        # Insert enquiry — sent_at is left NULL, email job will populate it
        cursor.execute(
            """
            INSERT INTO Enquiries (name, phone, email, message, ip_address, submitted_at, sent_at)
            VALUES (%s, %s, %s, %s, %s, CONVERT_TZ(NOW(), 'UTC', 'Australia/Melbourne'), NULL)
            """,
            (payload.name, payload.phone, payload.email, payload.message, ip),
        )
        conn.commit()

        return {
            "status": "received",
            "message": "Your enquiry has been received. We will be in touch shortly.",
        }

    except HTTPException:
        raise  # re-raise rate limit error without wrapping it
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


# ─── GET /api/enquiries ──────────────────────────────────────────────────────
@router.get("")
def get_enquiries(
    start: date = Query(..., description="Start date inclusive (YYYY-MM-DD)"),
    end: date   = Query(..., description="End date inclusive (YYYY-MM-DD)"),
    page: int   = Query(1,  ge=1,   description="Page number"),
    limit: int  = Query(50, ge=1, le=200, description="Records per page (max 200)"),
    _token: str = Depends(require_token),
):
    """
    Returns enquiry records filtered by date range.
    Requires Bearer token authentication.
    """
    if end < start:
        raise HTTPException(status_code=400, detail="'end' date must be on or after 'start' date")

    offset = (page - 1) * limit

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT COUNT(*) AS total FROM Enquiries
            WHERE DATE(submitted_at) BETWEEN %s AND %s
            """,
            (start, end),
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT id, name, phone, email, message, ip_address, submitted_at, sent_at
            FROM Enquiries
            WHERE DATE(submitted_at) BETWEEN %s AND %s
            ORDER BY submitted_at DESC
            LIMIT %s OFFSET %s
            """,
            (start, end, limit, offset),
        )
        records = cursor.fetchall()

        for r in records:
            if r["submitted_at"]:
                r["submitted_at"] = r["submitted_at"].isoformat()
            if r["sent_at"]:
                r["sent_at"] = r["sent_at"].isoformat()

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
