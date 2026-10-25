# ALPHA TOP UP

A gaming storefront starter for Free Fire Diamonds and PUBG Mobile UC with a static frontend, FastAPI backend, PostgreSQL/SQLite persistence, manual payment workflow and order tracking.

## Important
- Package prices are examples. Replace them with your verified supplier prices.
- This starter does **not** deliver Diamonds/UC automatically. Configure an authorized top-up provider and implement its documented API, authentication, payment checks, idempotency and fulfillment logic before enabling automatic delivery.
- Never request a game password, OTP or recovery code.
- Manual payment numbers and instructions should be shared only through your verified official store channels.
- Do not store provider secrets in frontend files or commit `.env` files.

## Repository layout
- `frontend/`: GitHub Pages static site
- `backend/`: FastAPI service and order database
- `backend/render.yaml`: Render deployment blueprint

## Run backend locally
Python 3.11+ recommended.

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

Set environment variables before starting:
- `ADMIN_TOKEN`: long random secret (at least 24 characters; use 32+)
- `CORS_ORIGINS`: comma-separated frontend origins
- `DATABASE_URL`: PostgreSQL URL for persistent deployment; defaults to local SQLite for development

Windows PowerShell example:
```powershell
$env:ADMIN_TOKEN="replace-with-a-long-random-secret"
$env:CORS_ORIGINS="http://localhost:5500"
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for API docs and `http://localhost:8000/health` for health check.

## Configure frontend
Edit `frontend/app.js`:
- Set `API_BASE` to your backend base URL, e.g. `https://your-api.onrender.com` (no trailing slash).
- Set `STORE_WHATSAPP` to your official store number in international digits-only format, e.g. `8801XXXXXXXXX`.

Run frontend locally with VS Code Live Server on port 5500, or use another local static server. Add that exact origin to `CORS_ORIGINS`.

## Free hosting outline
1. Push this repository to GitHub.
2. Create a PostgreSQL database on a provider whose current free tier meets your needs; copy its internal/external connection URL as appropriate.
3. In Render, create a Web Service from this repository, root directory `backend`, build command `pip install -r requirements.txt`, start command `uvicorn main:app --host 0.0.0.0 --port $PORT`.
4. Add environment variables `DATABASE_URL`, `ADMIN_TOKEN` and `CORS_ORIGINS`. Never put these in the frontend. Free-tier availability, sleep behavior, storage limits and database expiry vary by provider and may change.
5. Deploy and test `/health`.
6. Enable GitHub Pages for `frontend/` by using GitHub Actions or copy its contents to a separate Pages repository/root. GitHub Pages typically publishes from a repository branch root or `/docs`; for this repository, easiest is a GitHub Actions Pages workflow or a separate frontend repository.
7. Set `API_BASE` to your deployed backend URL and set `CORS_ORIGINS` to the exact deployed frontend origin, then redeploy both.
8. Test creating an order and tracking it before sharing the site.

## Admin API
Send `X-Admin-Token: <ADMIN_TOKEN>` as a header. Never expose the token in frontend JavaScript.
- `GET /api/admin/orders`
- `POST /api/admin/orders/{order_id}/payment-reference`
- `POST /api/admin/orders/{order_id}/status`

Example status body:
```json
{"status":"paid_verified"}
```

Use admin endpoints only from a secure admin tool or API client. This starter intentionally does not provide a public admin dashboard or automatic fulfillment. Add authenticated admin UI, rate limiting, audit logs, privacy/retention rules, payment verification and provider integration before production.

## Order statuses
`awaiting_payment` → `payment_submitted` → `paid_verified` → `processing` → `completed`

A store operator must verify the payment independently. `completed` should only be set after the provider confirms successful fulfillment.

## Production checklist
- Use a provider officially authorized to fulfill the relevant game top-ups and follow the provider's terms.
- Verify provider webhooks/signatures server-side; use idempotency keys to prevent duplicate purchases.
- Validate all price and package data server-side (basic validation is included).
- Add rate limiting, monitoring, HTTPS, secure admin login, audit logs and backups.
- Do not trust client-supplied payment screenshots or transaction IDs as proof of payment.
