"""
routers/blogs.py

Endpoints:
  POST   /api/blogs          — token protected, create blog post
  GET    /api/blogs/latest   — public, returns latest 20 posts
  GET    /api/blogs/{id}     — token protected, single post by ID
  PUT    /api/blogs/{id}     — token protected, update post
  DELETE /api/blogs/{id}     — token protected, delete post

IMPORTANT: /api/blogs/latest must be defined BEFORE /api/blogs/{id}
otherwise FastAPI will try to match the string "latest" as an integer
and return a 422 validation error instead of serving the public endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from database import get_connection
from auth import require_token

router = APIRouter(prefix="/api/blogs", tags=["Blogs"])


# ─── Request models ──────────────────────────────────────────────────────────
class BlogCreateRequest(BaseModel):
    location: str
    subject:  str
    text:     str
    hashtags: List[str]

    class Config:
        str_strip_whitespace = True


class BlogUpdateRequest(BaseModel):
    location: Optional[str]       = None
    subject:  Optional[str]       = None
    text:     Optional[str]       = None
    hashtags: Optional[List[str]] = None

    class Config:
        str_strip_whitespace = True


# ─── Helpers ─────────────────────────────────────────────────────────────────
def _get_tags(cur, blog_id: int) -> List[str]:
    """Fetches all tag names associated with a blog post."""
    cur.execute(
        """
        SELECT t.name FROM tags t
        JOIN blog_tags bt ON bt.tag_id = t.id
        WHERE bt.blog_id = %s
        ORDER BY t.name
        """,
        (blog_id,),
    )
    return [row["name"] for row in cur.fetchall()]


def _save_tags(cur, blog_id: int, hashtags: List[str]):
    """
    Upserts each hashtag and creates the blog_tags junction records.

    For each tag:
      1. Normalise to lowercase and strip whitespace
      2. Insert into tags table if it doesn't exist (ON CONFLICT DO NOTHING)
      3. Fetch the tag ID
      4. Insert into blog_tags (ON CONFLICT DO NOTHING prevents duplicates)
    """
    for raw_tag in hashtags:
        tag_name = raw_tag.strip().lower()
        if not tag_name:
            continue

        # Insert tag if it doesn't exist
        cur.execute(
            "INSERT INTO tags (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
            (tag_name,),
        )

        # Get the tag ID
        cur.execute("SELECT id FROM tags WHERE name = %s", (tag_name,))
        tag_id = cur.fetchone()["id"]

        # Link tag to blog post
        cur.execute(
            "INSERT INTO blog_tags (blog_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (blog_id, tag_id),
        )


def _format_blog(row: dict, tags: List[str]) -> dict:
    """Serialises a blog row into a clean dict for the API response."""
    result = {
        "id":       row["id"],
        "location": row["location"],
        "subject":  row["subject"],
        "text":     row["text"],
        "hashtags": tags,
    }
    if row.get("created_at"):
        result["created_at"] = row["created_at"].isoformat()
    if row.get("updated_at"):
        result["updated_at"] = row["updated_at"].isoformat()
    return result


# ─── POST /api/blogs ─────────────────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
def create_blog(payload: BlogCreateRequest, _token: str = Depends(require_token)):
    """
    Creates a new blog post with associated hashtags.
    Requires Bearer token authentication.
    """
    if not payload.location.strip():
        raise HTTPException(status_code=400, detail="location cannot be empty")
    if not payload.subject.strip():
        raise HTTPException(status_code=400, detail="subject cannot be empty")
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")

    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO blogs (location, subject, text, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            RETURNING id, location, subject, created_at
            """,
            (payload.location, payload.subject, payload.text),
        )
        blog = cur.fetchone()
        blog_id = blog["id"]

        _save_tags(cur, blog_id, payload.hashtags)
        conn.commit()

        tags = _get_tags(cur, blog_id)

        return {
            "id":         blog_id,
            "location":   blog["location"],
            "subject":    blog["subject"],
            "created_at": blog["created_at"].isoformat(),
            "hashtags":   tags,
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ─── GET /api/blogs/latest ───────────────────────────────────────────────────
# Must be defined BEFORE /{blog_id} — see module docstring.
@router.get("/latest")
def get_latest_blogs():
    """
    Returns the 20 most recently created blog posts.
    Public endpoint — no authentication required.
    Includes full text and hashtags so the frontend needs no additional calls.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                id, location, subject, text,
                created_at AT TIME ZONE 'Australia/Melbourne' AS created_at
            FROM blogs
            ORDER BY created_at DESC
            LIMIT 20
            """
        )
        rows = cur.fetchall()

        blogs = []
        for row in rows:
            tags = _get_tags(cur, row["id"])
            blogs.append(_format_blog(dict(row), tags))

        return {"count": len(blogs), "data": blogs}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ─── GET /api/blogs/{id} ─────────────────────────────────────────────────────
@router.get("/{blog_id}")
def get_blog(blog_id: int, _token: str = Depends(require_token)):
    """
    Returns a single blog post by ID.
    Requires Bearer token authentication.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                id, location, subject, text,
                created_at AT TIME ZONE 'Australia/Melbourne' AS created_at,
                updated_at AT TIME ZONE 'Australia/Melbourne' AS updated_at
            FROM blogs
            WHERE id = %s
            """,
            (blog_id,),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Blog post not found")

        tags = _get_tags(cur, blog_id)
        return _format_blog(dict(row), tags)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ─── PUT /api/blogs/{id} ─────────────────────────────────────────────────────
@router.put("/{blog_id}")
def update_blog(
    blog_id: int,
    payload: BlogUpdateRequest,
    _token: str = Depends(require_token),
):
    """
    Updates an existing blog post.
    Only fields present in the request body are modified.
    If hashtags are provided, ALL existing tag associations are replaced.
    Requires Bearer token authentication.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Confirm post exists
        cur.execute("SELECT id FROM blogs WHERE id = %s", (blog_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Blog post not found")

        # Build dynamic SET clause from provided fields only
        fields = {}
        if payload.location is not None:
            fields["location"] = payload.location
        if payload.subject is not None:
            fields["subject"] = payload.subject
        if payload.text is not None:
            fields["text"] = payload.text

        if fields:
            fields["updated_at"] = "NOW()"
            # Separate literal SQL values from column values
            set_parts = []
            values = []
            for col, val in fields.items():
                if val == "NOW()":
                    set_parts.append(f"{col} = NOW()")
                else:
                    set_parts.append(f"{col} = %s")
                    values.append(val)
            values.append(blog_id)
            cur.execute(
                f"UPDATE blogs SET {', '.join(set_parts)} WHERE id = %s",
                values,
            )

        # Replace hashtags if provided
        if payload.hashtags is not None:
            cur.execute("DELETE FROM blog_tags WHERE blog_id = %s", (blog_id,))
            _save_tags(cur, blog_id, payload.hashtags)

        conn.commit()
        return {"status": "updated", "id": blog_id}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ─── DELETE /api/blogs/{id} ──────────────────────────────────────────────────
@router.delete("/{blog_id}")
def delete_blog(blog_id: int, _token: str = Depends(require_token)):
    """
    Permanently deletes a blog post.
    blog_tags records are removed automatically via ON DELETE CASCADE.
    Tags in the tags table are preserved for use by other posts.
    Requires Bearer token authentication.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT id FROM blogs WHERE id = %s", (blog_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Blog post not found")

        cur.execute("DELETE FROM blogs WHERE id = %s", (blog_id,))
        conn.commit()

        return {"status": "deleted", "message": f"Blog post {blog_id} has been permanently deleted"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cur.close()
        conn.close()
