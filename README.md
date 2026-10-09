# ShopLite — E-Commerce Web Application

ShopLite is a small full-stack online store built to cover the e-commerce task requirements.

## Features

- Product catalog with category filters and search
- Shopping cart with quantity controls and totals
- Checkout with shipping details and persistent order creation
- Customer registration/login and JWT authentication
- Role-based admin access
- Admin product management and stock updates
- Customer order history
- Admin order list and status updates
- Responsive UI
- SQLite for quick local setup; optional PostgreSQL with `DATABASE_URL`

Payment processing is intentionally omitted because the task does not require a payment gateway. Checkout creates a database order without charging a payment method.

## Stack

- React + Vite
- Python + Flask REST API
- SQLite local database, with optional PostgreSQL support
- JWT sessions
- Werkzeug password hashing

## Run locally on Windows

1. Install Python 3.11+ and Node.js 20+.
2. Open this folder in VS Code.
3. Run `setup.bat`.
4. In one terminal run `run_backend.bat`.
5. In a second terminal run `run_frontend.bat`.
6. Open `http://localhost:5173`.

No Docker or local PostgreSQL installation is required for the default SQLite mode.

## Admin account

Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in your local `.env` file before the first backend start. The app creates the admin account if these values are configured. The values in `.env.example` are examples only; change the password before use.

## PostgreSQL mode

To use PostgreSQL instead of SQLite, set `DATABASE_URL` to a dedicated PostgreSQL database URL and install requirements using `pip install -r requirements.txt`. Keep database credentials out of Git.

## Main API routes

- `GET /api/products`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/orders`
- `GET /api/orders`
- `GET /api/admin/products`
- `POST /api/admin/products`
- `PATCH /api/admin/products/<id>`
- `DELETE /api/admin/products/<id>`
- `GET /api/admin/orders`
- `PATCH /api/admin/orders/<id>`
- `GET /api/health`

See `SUBMISSION_CHECKLIST.md` for a practical demo flow.
