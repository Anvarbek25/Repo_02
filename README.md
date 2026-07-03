# Bahafix Backend API v2.0

Python + FastAPI + PostgreSQL backend for the Bahafix website.
Deployed on Render (web service + managed PostgreSQL).

---

## Project Structure

```
bahafix_api/
├── main.py              # FastAPI app — entry point, CORS, routers
├── database.py          # PostgreSQL connection (psycopg2)
├── auth.py              # Bearer token authentication dependency
├── utils.py             # Shared helpers (client IP extraction)
├── email_sender.py      # Gmail SMTP email dispatch
├── schema.sql           # Run once to create all database tables
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template (copy to .env)
└── routers/
    ├── phone_clicks.py  # POST + GET /api/phone-clicks
    ├── enquiries.py     # POST + GET /api/enquiries
    └── blogs.py         # CRUD /api/blogs
```

---

## Local Development Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `ADMIN_TOKEN` | Your secret Bearer token (min 32 chars) |
| `GMAIL_ADDRESS` | Gmail account that sends notifications |
| `GMAIL_APP_PASSWORD` | 16-char Google App Password (not login password) |
| `NOTIFY_EMAIL` | Business owner email that receives enquiries |
| `FRONTEND_ORIGIN` | Website domain for CORS (e.g. https://bahafix.com.au) |

**Generating a secure ADMIN_TOKEN:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Getting a Gmail App Password:**
1. Go to myaccount.google.com → Security
2. Enable 2-Step Verification (required)
3. Go to Security → App Passwords
4. Create an App Password for "Mail"
5. Copy the 16-character password into `.env`

### 3. Set up the database

Create a local PostgreSQL database, then run the schema:

```bash
psql -U your_user -d your_database -f schema.sql
```

### 4. Start the server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Visit **http://localhost:8000/docs** to test all endpoints interactively.

---

## Render Deployment

### Step 1 — Push to GitHub
Push this project to a GitHub repository.

### Step 2 — Create PostgreSQL on Render
- Render dashboard → New → PostgreSQL
- Copy the **External Database URL** for local testing
- Render will inject `DATABASE_URL` automatically into your web service

### Step 3 — Run the schema
```bash
psql "<your External Database URL>" -f schema.sql
```

### Step 4 — Create Web Service on Render
- Render dashboard → New → Web Service
- Connect your GitHub repository
- Runtime: **Python 3**
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Step 5 — Set environment variables in Render dashboard
Set all variables from `.env.example` under your web service's Environment tab.
Do NOT upload your `.env` file — set them directly in the Render UI.

### Step 6 — Verify
Visit `https://your-render-url.onrender.com/docs` to confirm the API is live.

---

## API Endpoints

| # | Method | Path | Auth | Description |
|---|--------|------|------|-------------|
| 1 | POST | `/api/phone-clicks` | Public | Record phone button click |
| 2 | GET | `/api/phone-clicks` | Token | Get click records by date range |
| 3 | POST | `/api/enquiries` | Public | Submit enquiry (sends email, stores no PII) |
| 4 | GET | `/api/enquiries` | Token | Get submission log (analytics only) |
| 5 | POST | `/api/blogs` | Token | Create blog post |
| 6 | GET | `/api/blogs/latest` | Public | Get latest 20 posts |
| 7 | GET | `/api/blogs/{id}` | Token | Get single post by ID |
| 8 | PUT | `/api/blogs/{id}` | Token | Update blog post |
| 9 | DELETE | `/api/blogs/{id}` | Token | Delete blog post |

---

## Using Protected Endpoints

**Via /docs page (easiest):**
1. Open `/docs`
2. Click the **Authorize** 🔒 button at the top right
3. Enter your token — FastAPI will include it in all subsequent requests

**Via Postman:**
- Tab: **Authorization** → Type: **Bearer Token** → paste your ADMIN_TOKEN

**Via curl:**
```bash
curl -H "Authorization: Bearer your_token_here" \
     "https://your-api.onrender.com/api/blogs/latest"
```
