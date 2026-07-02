"""
routers/blogs.py

Endpoints:
  POST   /api/blogs          — token protected, create blog post
  GET    /api/blogs/latest   — public, returns latest 20 posts
  GET    /api/blogs/{id}     — token protected, single post by ID
  PUT    /api/blogs/{id}     — token protected, update post
  DELETE /api/blogs/{id}     — token protected, delete post
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
        # Strips whitespace from all string fields automatically
        str_strip_whitespace = True


class BlogUpdateRequest(BaseModel):
    location: Optional[str] = None
    subject:  Optional[str] = None
    text:     Optional[str] = None
    hashtags: Optional[List[str]] = None

    class Config:
        str_strip_whitespace = True


# ─── Helper: fetch tags for a blog post ─────────────────────────────────────
def _get_tags_for_blog(cursor, blog_id: int) -> List[str]:
    cursor.execute(
        """
        SELECT t.name FROM Tags t
        JOIN BlogTags bt ON bt.tag_id = t.id
        WHERE bt.blog_id = %s
        ORDER BY t.name
        """,
        (blog_id,),
    )
    return [row["name"] for row in cursor.fetchall()]


# ─── Helper: upsert tags and link to blog ───────────────────────────────────
def _save_tags(cursor, blog_id: int, hashtags: List[str]):
    """
    For each hashtag:
      1. Insert into Tags if it doesn't already exist (INSERT IGNORE)
      2. Fetch the tag's ID
      3. Insert into BlogTags junction table
    """
    for tag_name in hashtags:
        tag_name = tag_name.strip().lower()
        if not tag_name:
            continue

        # Insert tag if it doesn't exist yet
        cursor.execute(
            "INSERT IGNORE INTO Tags (name) VALUES (%s)",
            (tag_name,),
        )

        # Get the tag ID (whether just inserted or already existed)
        cursor.execute("SELECT id FROM Tags WHERE name = %s", (tag_name,))
        tag_id = cursor.fetchone()["id"]

        # Link tag to blog (INSERT IGNORE prevents duplicates)
        cursor.execute(
            "INSERT IGNORE INTO BlogTags (blog_id, tag_id) VALUES (%s, %s)",
            (blog_id, tag_id),
        )


# ─── POST /api/blogs ─────────────────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
def create_blog(payload: BlogCreateRequest, _token: str = Depends(require_token)):
    """
    Creates a new blog post with associated hashtags.
    Requires Bearer token authentication.
    """
    if not payload.location or not payload.subject or not payload.text:
        raise HTTPException(status_code=400, detail="location, subject, and text are required")

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        # Insert the blog post
        cursor.execute(
            """
            INSERT INTO Blogs (location, subject, text, created_at, updated_at)
            VALUES (%s, %s, %s,
                    CONVERT_TZ(NOW(), 'UTC', 'Australia/Melbourne'),
                    CONVERT_TZ(NOW(), 'UTC', 'Australia/Melbourne'))
            """,
            (payload.location, payload.subject, payload.text),
        )
        blog_id = cursor.lastrowid

        # Save hashtags and link them
        _save_tags(cursor, blog_id, payload.hashtags)

        conn.commit()

        # Fetch the created record to return it
        cursor.execute("SELECT id, location, subject, created_at FROM Blogs WHERE id = %s", (blog_id,))
        blog = cursor.fetchone()
        blog["created_at"] = blog["created_at"].isoformat()
        blog["hashtags"] = _get_tags_for_blog(cursor, blog_id)

        return blog

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


# ─── GET /api/blogs/latest ───────────────────────────────────────────────────
# IMPORTANT: This route must be defined BEFORE /api/blogs/{id}
# otherwise FastAPI will try to match "latest" as an integer ID and fail
@router.get("/latest")
def get_latest_blogs():
    """
    Returns the 20 most recently created blog posts.
    Public endpoint — no authentication required.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, location, subject, text, created_at
            FROM Blogs
            ORDER BY created_at DESC
            LIMIT 20
            """
        )
        blogs = cursor.fetchall()

        for blog in blogs:
            blog["created_at"] = blog["created_at"].isoformat()
            blog["hashtags"] = _get_tags_for_blog(cursor, blog["id"])

        return {"count": len(blogs), "data": blogs}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
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
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, location, subject, text, created_at, updated_at FROM Blogs WHERE id = %s",
            (blog_id,),
        )
        blog = cursor.fetchone()

        if not blog:
            raise HTTPException(status_code=404, detail="Blog post not found")

        blog["created_at"] = blog["created_at"].isoformat()
        blog["updated_at"] = blog["updated_at"].isoformat()
        blog["hashtags"] = _get_tags_for_blog(cursor, blog_id)

        return blog

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


# ─── PUT /api/blogs/{id} ─────────────────────────────────────────────────────
@router.put("/{blog_id}")
def update_blog(
    blog_id: int,
    payload: BlogUpdateRequest,
    _token: str = Depends(require_token),
):
    """
    Updates an existing blog post. Only fields provided are updated.
    If hashtags are provided, ALL existing tags for this post are replaced.
    Requires Bearer token authentication.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        # Confirm the post exists
        cursor.execute("SELECT id FROM Blogs WHERE id = %s", (blog_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Blog post not found")

        # Build dynamic UPDATE — only update fields that were sent
        fields = {}
        if payload.location is not None:
            fields["location"] = payload.location
        if payload.subject is not None:
            fields["subject"] = payload.subject
        if payload.text is not None:
            fields["text"] = payload.text

        if fields:
            set_clause = ", ".join(f"{col} = %s" for col in fields)
            values = list(fields.values()) + [blog_id]
            cursor.execute(f"UPDATE Blogs SET {set_clause} WHERE id = %s", values)

        # Replace hashtags if provided
        if payload.hashtags is not None:
            # Remove all existing tag links for this post
            cursor.execute("DELETE FROM BlogTags WHERE blog_id = %s", (blog_id,))
            # Add the new set
            _save_tags(cursor, blog_id, payload.hashtags)

        conn.commit()
        return {"status": "updated", "id": blog_id}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


# ─── DELETE /api/blogs/{id} ──────────────────────────────────────────────────
@router.delete("/{blog_id}")
def delete_blog(blog_id: int, _token: str = Depends(require_token)):
    """
    Permanently deletes a blog post and all its tag associations.
    Tag records in the Tags table are preserved for use by other posts.
    Requires Bearer token authentication.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM Blogs WHERE id = %s", (blog_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Blog post not found")

        # BlogTags rows are deleted automatically via ON DELETE CASCADE
        # defined in schema.sql, so we only need to delete the Blog row
        cursor.execute("DELETE FROM Blogs WHERE id = %s", (blog_id,))
        conn.commit()

        return {"status": "deleted", "message": f"Blog post {blog_id} has been permanently deleted"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()
