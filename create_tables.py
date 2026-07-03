import os
import psycopg2

def build_production_tables():
    """Automatically loads and runs schema.sql on Render startup"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("⚠️ database auto-setup skipped: DATABASE_URL not found.")
        return

    # Fix connection prefix for psycopg2 compatibility
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    # Inject SSL requirement
    if "sslmode" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"

    # Verify if schema file is present in deployment package
    if not os.path.exists("schema.sql"):
        print("⚠️ database auto-setup skipped: schema.sql file is missing.")
        return

    try:
        print("🚀 [STARTUP] Initializing database migration...")
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        with open("schema.sql", "r", encoding="utf-8") as f:
            cur.execute(f.read())
            
        conn.commit()
        print("🎉 [STARTUP] Database schema successfully synced!")
    except Exception as e:
        print(f"❌ [STARTUP] Database initialization failed: {e}")
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    build_production_tables()
