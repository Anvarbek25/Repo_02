# Bahafix Backend API

Python + FastAPI + MySQL backend for the Bahafix website.

---

## Project Structure

```
bahafix_api/
├── main.py              # FastAPI app entry point
├── database.py          # MySQL connection pool
├── auth.py              # Bearer token authentication
├── utils.py             # Shared helpers (IP extraction)
├── email_job.py         # Background email dispatch job
├── schema.sql           # MySQL database setup script
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
└── routers/
    ├── phone_clicks.py  # POST/GET /api/phone-clicks
    ├── enquiries.py     # POST/GET /api/enquiries
    └── blogs.py         # CRUD    /api/blogs
```

---

## Setup

### 1. Clone / copy the project files to your server

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up the MySQL database

Log into MySQL and run the schema file:

```bash
mysql -u root -p < schema.sql
```

This creates the `bahafix` database and all tables.

### 4. Configure environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set:
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` — your MySQL credentials
- `ADMIN_TOKEN` — a long random string (your API password for protected endpoints)
- `GMAIL_ADDRESS` — the Gmail account that sends notifications
- `GMAIL_APP_PASSWORD` — 16-character App Password from Google Account settings
- `NOTIFY_EMAIL` — the email address that receives enquiry notifications
- `FRONTEND_ORIGIN` — your website domain (e.g. https://bahafix.com.au)

#### How to get a Gmail App Password:
1. Go to your Google Account → Security
2. Enable 2-Step Verification (required)
3. Go to Security → App Passwords
4. Create a new App Password for "Mail"
5. Copy the 16-character password into `.env`

---

## Running the API

### Start the API server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

For development with auto-reload on file changes:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Start the email background job (separate terminal / process)

```bash
python email_job.py
```

This must run alongside the API. On a production server, use a process
manager like `supervisor` or `systemd` to keep both running automatically.

---

## API Documentation

Once the server is running, visit:

```
http://localhost:8000/docs
```

This opens the interactive FastAPI docs page where you can test every
endpoint directly in your browser — including protected endpoints by
clicking the lock icon and entering your Bearer token.

---

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/phone-clicks | Public | Record phone button click |
| GET | /api/phone-clicks | Token | Get clicks by date range |
| POST | /api/enquiries | Public | Submit contact form |
| GET | /api/enquiries | Token | Get enquiries by date range |
| POST | /api/blogs | Token | Create blog post |
| GET | /api/blogs/latest | Public | Get latest 20 posts |
| GET | /api/blogs/{id} | Token | Get single post by ID |
| PUT | /api/blogs/{id} | Token | Update blog post |
| DELETE | /api/blogs/{id} | Token | Delete blog post |

---

## Using Protected Endpoints in Postman

1. Open the request in Postman
2. Go to the **Headers** tab
3. Add: `Authorization` → `Bearer your_admin_token_here`

Or use the **Authorization** tab → Type: **Bearer Token** → paste your token.
