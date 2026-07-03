"""
routers/enquiries.py

Endpoints:
  POST /api/enquiries  — public, validates form, sends Gmail immediately,
                         stores only ip + timestamp (no PII in DB)
  GET  /api/enquiries  — token protected, returns anonymous log for analytics
"""

from fastapi import APIRouter, Request, Depends, Query, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from datetime import date
from database import get_connection
from auth import require_token
from utils import get_client_ip
from email_sender import send_enquiry_email

router = APIRouter(prefix="/api/enquiries", tags=["Enquiries"])


# ─── Request model ───────────────────────────────────────────────────────────
class EnquiryRequest(BaseModel):
    name:    str
    phone:   str
    email:   EmailStr
    message: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        if len(v) > 255:
            raise ValueError("Name cannot exceed 255 characters")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Phone cannot be empty")
        if len(v) > 50:
            raise ValueError("Phone cannot exceed 50 characters")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > 400:
            raise ValueError("Message cannot exceed 400 characters")
        return v


# ─── POST /api/enquiries ─────────────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
def submit_enquiry(payload: EnquiryRequest, request: Request):
    """
    Accepts a customer contact form submission.

    Process:
      1. Validate all fields (FastAPI handles this automatically via EnquiryRequest)
      2. Check IP rate limit — max 10 submissions per IP per Melbourne day
      3. Compose and send email via Gmail immediately
      4. If email succeeds: store anonymous log (ip + timestamp only) and return 201
      5. If email fails: return 500, do NOT store a log record

    Privacy: name, phone, email, message are NEVER written to the database.
    They exist in memory only for the duration of this request.
    """
    ip = get_client_ip(request)

    conn = get_connection()
    try:
        cur = conn.cursor()

        # ── Rate limit check ──────────────────────────────────────────────
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
                detail="Maximum enquiries reached for today from this location.",
            )

        # ── Send email immediately ────────────────────────────────────────
        sent = send_enquiry_email(
            name=payload.name,
            phone=payload.phone,
            email=str(payload.email),
            message=payload.message,
        )

        if not sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send enquiry. Please try again.",
            )

        # ── Store anonymous log record (no PII) ───────────────────────────
        cur.execute(
            "INSERT INTO enquiries (ip_address, submitted_at) VALUES (%s, NOW())",
            (ip,),
        )
        conn.commit()

        return {
            "status": "received",
            "message": "Your enquiry has been received. We will be in touch shortly.",
        }

    except HTTPException:
        raise  # Re-raise HTTP exceptions without wrapping
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
    Returns the anonymous enquiry submission log filtered by date range.
    Only id, ip_address, and submitted_at are returned — no PII exists in DB.
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
