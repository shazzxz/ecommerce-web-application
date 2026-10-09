import os
from datetime import datetime, timezone
from functools import wraps

import jwt
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_PATH = os.getenv("SHOPLITE_DB", os.path.join(BASE_DIR, "shoplite.db"))
JWT_SECRET = os.getenv("JWT_SECRET", "local-shoplite-secret-change-before-deploy")
TOKEN_HOURS = int(os.getenv("TOKEN_TTL_HOURS", "12"))
CORS_ORIGINS = [value.strip() for value in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if value.strip()]
IS_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}})


def connect_db():
    if IS_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    import sqlite3
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def db():
    if "connection" not in g:
        g.connection = connect_db()
    return g.connection


@app.teardown_appcontext
def close_db(_error=None):
    connection = g.pop("connection", None)
    if connection is not None:
        connection.close()


def execute(sql, params=()):
    cursor = db().cursor()
    cursor.execute(sql.replace("?", "%s") if IS_POSTGRES else sql, params)
    return cursor


def new_id(cursor):
    if IS_POSTGRES:
        return cursor.fetchone()["id"]
    return cursor.lastrowid


def now_text():
    return datetime.now(timezone.utc).isoformat()


def init_db():
    id_type = "BIGSERIAL PRIMARY KEY" if IS_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
    statements = [
        f"""CREATE TABLE IF NOT EXISTS users (
            id {id_type}, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'customer',
            created_at TEXT NOT NULL
        )""",
        f"""CREATE TABLE IF NOT EXISTS products (
            id {id_type}, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT 'General', price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0, image_url TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )""",
        f"""CREATE TABLE IF NOT EXISTS orders (
            id {id_type}, user_id BIGINT NOT NULL, customer_name TEXT NOT NULL,
            email TEXT NOT NULL, phone TEXT NOT NULL, address TEXT NOT NULL,
            total REAL NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        )""",
        f"""CREATE TABLE IF NOT EXISTS order_items (
            id {id_type}, order_id BIGINT NOT NULL, product_id BIGINT NOT NULL,
            product_name TEXT NOT NULL, unit_price REAL NOT NULL,
            quantity INTEGER NOT NULL
        )""",
    ]
    connection = connect_db()
    try:
        cursor = connection.cursor()
        for statement in statements:
            cursor.execute(statement)
        if IS_POSTGRES:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)")
        else:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)")
        cursor.execute("SELECT COUNT(*) AS count FROM products")
        row = cursor.fetchone()
        count = row["count"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
        if count == 0:
            samples = [
                ("Everyday Backpack", "A durable everyday bag with a padded laptop sleeve.", "Accessories", 39.99, 18, "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=900&q=80", now_text()),
                ("Wireless Headphones", "Comfortable over-ear listening with a clean, balanced sound.", "Electronics", 79.00, 12, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80", now_text()),
                ("Ceramic Coffee Set", "Minimal ceramic mug set for slow mornings.", "Home", 26.50, 24, "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=900&q=80", now_text()),
                ("Classic Sneakers", "Versatile low-top sneakers for everyday wear.", "Clothing", 64.95, 9, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80", now_text()),
                ("Desk Lamp", "An adjustable warm-light lamp for focused work.", "Home", 34.00, 15, "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=900&q=80", now_text()),
                ("Steel Water Bottle", "Reusable double-wall bottle for commutes and trips.", "Accessories", 18.75, 30, "https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=900&q=80", now_text()),
            ]
            for item in samples:
                cursor.execute(
                    "INSERT INTO products (name, description, category, price, stock, image_url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)".replace("?", "%s") if IS_POSTGRES else "INSERT INTO products (name, description, category, price, stock, image_url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    item,
                )
        admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
        admin_password = os.getenv("ADMIN_PASSWORD", "")
        if admin_email and admin_password:
            cursor.execute("SELECT id FROM users WHERE email = ?" .replace("?", "%s") if IS_POSTGRES else "SELECT id FROM users WHERE email = ?", (admin_email,))
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(
                    "INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, 'admin', ?)".replace("?", "%s") if IS_POSTGRES else "INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, 'admin', ?)",
                    ("ShopLite Admin", admin_email, generate_password_hash(admin_password), now_text()),
                )
        connection.commit()
    finally:
        connection.close()


def token_for(user):
    return jwt.encode({
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "name": user["name"],
        "exp": datetime.now(timezone.utc).timestamp() + TOKEN_HOURS * 3600,
    }, JWT_SECRET, algorithm="HS256")


def auth_required(admin=False):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return jsonify({"error": "Please log in to continue."}), 401
            try:
                payload = jwt.decode(header[7:].strip(), JWT_SECRET, algorithms=["HS256"])
                user = {"id": int(payload["sub"]), "email": payload.get("email", ""), "name": payload.get("name", ""), "role": payload.get("role", "customer")}
            except (jwt.InvalidTokenError, ValueError, KeyError):
                return jsonify({"error": "Your session is invalid or expired. Please log in again."}), 401
            if admin and user["role"] != "admin":
                return jsonify({"error": "Administrator access is required."}), 403
            g.user = user
            return fn(*args, **kwargs)
        return wrapped
    return decorator


def product_dict(row):
    item = dict(row)
    item["price"] = round(float(item["price"]), 2)
    item["stock"] = int(item["stock"])
    return item


@app.get("/api/health")
def health():
    try:
        execute("SELECT 1").fetchone()
        return jsonify({"status": "ok", "database": "connected", "engine": "postgresql" if IS_POSTGRES else "sqlite"})
    except Exception:
        app.logger.exception("Health check failed")
        return jsonify({"status": "error", "database": "unavailable"}), 503


@app.get("/api/products")
def products():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    query = "SELECT id, name, description, category, price, stock, image_url FROM products WHERE 1=1"
    params = []
    if search:
        query += " AND (LOWER(name) LIKE LOWER(?) OR LOWER(description) LIKE LOWER(?))"
        params.extend([f"%{search}%", f"%{search}%"])
    if category and category.lower() != "all":
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY id DESC"
    rows = execute(query, tuple(params)).fetchall()
    return jsonify({"products": [product_dict(row) for row in rows]})


@app.post("/api/auth/register")
def register():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    if len(name) < 2 or len(name) > 100 or "@" not in email or len(password) < 8:
        return jsonify({"error": "Enter a name, valid email, and password with at least 8 characters."}), 400
    if IS_POSTGRES:
        cursor = execute("INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, 'customer', ?) RETURNING id", (name, email, generate_password_hash(password), now_text()))
        user_id = cursor.fetchone()["id"]
    else:
        cursor = execute("INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, 'customer', ?)", (name, email, generate_password_hash(password), now_text()))
        user_id = cursor.lastrowid
    try:
        db().commit()
    except Exception:
        db().rollback()
        return jsonify({"error": "That email may already be registered."}), 409
    user = {"id": user_id, "name": name, "email": email, "role": "customer"}
    return jsonify({"user": user, "token": token_for(user)}), 201


@app.post("/api/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    row = execute("SELECT id, name, email, password_hash, role FROM users WHERE email = ?", (email,)).fetchone()
    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"error": "Email or password is incorrect."}), 401
    user = {"id": row["id"], "name": row["name"], "email": row["email"], "role": row["role"]}
    return jsonify({"user": user, "token": token_for(user)})


@app.get("/api/auth/me")
@auth_required()
def me():
    return jsonify({"user": g.user})


@app.get("/api/orders")
@auth_required()
def my_orders():
    rows = execute("SELECT id, total, status, created_at FROM orders WHERE user_id = ? ORDER BY id DESC", (g.user["id"],)).fetchall()
    results = []
    for row in rows:
        order = dict(row)
        items = execute("SELECT product_name, unit_price, quantity FROM order_items WHERE order_id = ?", (order["id"],)).fetchall()
        order["total"] = round(float(order["total"]), 2)
        order["items"] = [dict(item) for item in items]
        results.append(order)
    return jsonify({"orders": results})


@app.post("/api/orders")
@auth_required()
def place_order():
    payload = request.get_json(silent=True) or {}
    shipping = payload.get("shipping") or {}
    name = str(shipping.get("name", "")).strip()
    email = str(shipping.get("email", "")).strip().lower()
    phone = str(shipping.get("phone", "")).strip()
    address = str(shipping.get("address", "")).strip()
    items = payload.get("items") or []
    if not name or "@" not in email or not phone or not address or not isinstance(items, list) or not items:
        return jsonify({"error": "Complete the shipping details and add at least one item."}), 400
    try:
        cart = {}
        for item in items:
            product_id = int(item.get("product_id"))
            quantity = int(item.get("quantity"))
            if quantity < 1 or quantity > 20:
                raise ValueError
            cart[product_id] = cart.get(product_id, 0) + quantity
    except (TypeError, ValueError, AttributeError):
        return jsonify({"error": "Cart contains an invalid product or quantity."}), 400

    connection = db()
    try:
        order_lines = []
        total = 0.0
        for product_id, quantity in cart.items():
            product = execute("SELECT id, name, price, stock FROM products WHERE id = ?", (product_id,)).fetchone()
            if not product:
                raise ValueError("A product in the cart no longer exists.")
            if int(product["stock"]) < quantity:
                raise ValueError(f"Not enough stock for {product['name']}.")
            price = float(product["price"])
            total += price * quantity
            order_lines.append((product_id, product["name"], price, quantity))
        if IS_POSTGRES:
            cur = execute("INSERT INTO orders (user_id, customer_name, email, phone, address, total, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?) RETURNING id",
                          (g.user["id"], name, email, phone, address, round(total, 2), now_text()))
            order_id = cur.fetchone()["id"]
        else:
            cur = execute("INSERT INTO orders (user_id, customer_name, email, phone, address, total, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
                          (g.user["id"], name, email, phone, address, round(total, 2), now_text()))
            order_id = cur.lastrowid
        for product_id, product_name, price, quantity in order_lines:
            execute("INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity) VALUES (?, ?, ?, ?, ?)",
                    (order_id, product_id, product_name, price, quantity))
            execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
        connection.commit()
        return jsonify({"order": {"id": order_id, "total": round(total, 2), "status": "pending"}}), 201
    except ValueError as exc:
        connection.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception:
        connection.rollback()
        app.logger.exception("Order checkout failed")
        return jsonify({"error": "Could not place order. Please try again."}), 500


@app.get("/api/admin/products")
@auth_required(admin=True)
def admin_products():
    rows = execute("SELECT id, name, description, category, price, stock, image_url FROM products ORDER BY id DESC").fetchall()
    return jsonify({"products": [product_dict(row) for row in rows]})


@app.post("/api/admin/products")
@auth_required(admin=True)
def create_product():
    payload = request.get_json(silent=True) or {}
    try:
        name = str(payload.get("name", "")).strip()
        price = float(payload.get("price"))
        stock = int(payload.get("stock"))
        if not name or price < 0 or stock < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Provide a product name, non-negative price and stock."}), 400
    values = (name, str(payload.get("description", "")).strip(), str(payload.get("category", "General")).strip() or "General",
              price, stock, str(payload.get("image_url", "")).strip(), now_text())
    sql = "INSERT INTO products (name, description, category, price, stock, image_url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
    if IS_POSTGRES:
        cur = execute(sql + " RETURNING id", values)
        product_id = cur.fetchone()["id"]
    else:
        cur = execute(sql, values)
        product_id = cur.lastrowid
    db().commit()
    return jsonify({"id": product_id}), 201


@app.patch("/api/admin/products/<int:product_id>")
@auth_required(admin=True)
def update_product(product_id):
    payload = request.get_json(silent=True) or {}
    allowed = {"name", "description", "category", "price", "stock", "image_url"}
    fields, values = [], []
    for key in allowed:
        if key in payload:
            fields.append(f"{key} = ?")
            values.append(payload[key])
    if not fields:
        return jsonify({"error": "No product changes provided."}), 400
    values.append(product_id)
    cur = execute(f"UPDATE products SET {', '.join(fields)} WHERE id = ?", tuple(values))
    db().commit()
    if cur.rowcount == 0:
        return jsonify({"error": "Product not found."}), 404
    return jsonify({"ok": True})


@app.delete("/api/admin/products/<int:product_id>")
@auth_required(admin=True)
def delete_product(product_id):
    cur = execute("DELETE FROM products WHERE id = ?", (product_id,))
    db().commit()
    if cur.rowcount == 0:
        return jsonify({"error": "Product not found."}), 404
    return jsonify({"ok": True})


@app.get("/api/admin/orders")
@auth_required(admin=True)
def admin_orders():
    rows = execute("SELECT id, user_id, customer_name, email, phone, address, total, status, created_at FROM orders ORDER BY id DESC").fetchall()
    results = []
    for row in rows:
        order = dict(row)
        order["total"] = round(float(order["total"]), 2)
        order["items"] = [dict(item) for item in execute("SELECT product_name, unit_price, quantity FROM order_items WHERE order_id = ?", (order["id"],)).fetchall()]
        results.append(order)
    return jsonify({"orders": results})


@app.patch("/api/admin/orders/<int:order_id>")
@auth_required(admin=True)
def update_order(order_id):
    status = str((request.get_json(silent=True) or {}).get("status", ""))
    if status not in {"pending", "processing", "shipped", "completed", "cancelled"}:
        return jsonify({"error": "Invalid order status."}), 400
    cur = execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    db().commit()
    if cur.rowcount == 0:
        return jsonify({"error": "Order not found."}), 404
    return jsonify({"ok": True, "status": status})


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"error": "Route not found."}), 404


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
