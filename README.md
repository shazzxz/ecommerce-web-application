# ShopLite — E-Commerce Web Application

A full-stack online store built for the e-commerce task requirements: product catalog, cart and checkout, customer/admin access, product management, order management, and database-backed data.

## Features

- Product catalog with category navigation, search, sorting, details, prices and stock availability
- Shopping cart with quantity controls, removal, and totals
- Checkout with shipping details and database-backed order creation
- Customer registration/login and role-based authorization
- Admin product CRUD and stock management
- Customer order history
- Admin order list and order-status updates
- Responsive storefront and dashboard layouts
- SQLite for zero-setup local use; optional PostgreSQL support via `DATABASE_URL`
- API tests for core authentication, inventory and order workflows

Payment processing is intentionally not included because it is not required by the assignment. Checkout creates an order record; it does not charge a payment method.

## Stack

- Frontend: React + Vite
- Backend: Python + Flask REST API
- Database: SQLite by default; optional PostgreSQL
- Authentication: JWT
- Password hashing: Werkzeug

## Run locally on Windows

1. Install Python 3.11+ and Node.js 20+.
2. Extract the source ZIP from this repository.
3. Run `setup.bat`.
4. Run `run_backend.bat` in one terminal.
5. Run `run_frontend.bat` in another terminal.
6. Open `http://localhost:5173`.

No Docker installation is needed for the default SQLite setup.

## PostgreSQL option

The project includes `requirements-postgres.txt` for the optional PostgreSQL driver. Configure `DATABASE_URL` in a local `.env` file for a dedicated ShopLite database. Do not use credentials from other projects.

## Source archive

Download `ShopLite-Source.zip` from the repository files to get the complete runnable source package, including the backend, frontend, tests, and Windows setup scripts.

## Verify the project

- Read `SUBMISSION_CHECKLIST.md` for the requirement mapping and demo flow.
- Read `CHANGELOG.md` for the release notes.
- Test product browsing, cart changes, checkout, order history, and admin product/order management.

## Author

Shashwat Solanki
