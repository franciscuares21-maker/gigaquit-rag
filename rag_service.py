from flask import Flask, request, jsonify
import mysql.connector
import os

app = Flask(__name__)

# 🔐 SECURE DB CONFIG (ENV VARIABLES)
# Set these in Render:
# DB_HOST=31.97.221.62
# DB_USER=www_gigaquit_user
# DB_PASSWORD=your_real_password
# DB_NAME=www_gigaquit_db
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}


# -------------------------------
# DATABASE HELPERS
# -------------------------------
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def run_scalar(query, params=None):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        row = cursor.fetchone()
        return row
    except Exception as e:
        print("DB ERROR:", e)
        return None
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def run_rows(query, params=None):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchall()
    except Exception as e:
        print("DB ERROR:", e)
        return []
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def table_exists(table_name):
    row = run_scalar("SHOW TABLES LIKE %s", (table_name,))
    return row is not None


def column_exists(table_name, column_name):
    row = run_scalar("""
        SELECT COUNT(*) AS total
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
        AND TABLE_NAME = %s
        AND COLUMN_NAME = %s
    """, (DB_CONFIG["database"], table_name, column_name))

    return bool(row and row.get("total", 0) > 0)


# -------------------------------
# INTENT DETECTION
# -------------------------------
def detect_intent(question):
    q = question.lower().strip()

    if "total users" in q or "how many users" in q or "registered users" in q:
        return "total_users"

    if "role counts" in q or ("farmers" in q and "producers" in q) or "user counts" in q:
        return "role_counts"

    if "revenue" in q or "total revenue" in q:
        return "revenue"

    if ("top" in q and "product" in q) or "best selling" in q or "top-selling" in q:
        return "top_products"

    if "low stock" in q or "out of stock" in q:
        return "low_stock"

    if "sap" in q:
        return "sap"

    if "products" in q or "show products" in q or "available products" in q:
        return "products"

    if "producers" in q or "who are the producers" in q:
        return "producers"

    if "history" in q:
        return "history"

    if "what is" in q or "about system" in q or "about gigaquit rhum" in q:
        return "system"

    return "unknown"


# -------------------------------
# ANSWERS
# -------------------------------
def answer_total_users():
    if not table_exists("users"):
        return "The users table was not found."

    row = run_scalar("SELECT COUNT(*) AS total FROM users")
    total = row["total"] if row else 0
    return f"There are {total} registered users."


def answer_role_counts():
    if not table_exists("users"):
        return "The users table was not found."

    if not column_exists("users", "role"):
        return "The role column was not found in the users table."

    rows = run_rows("""
        SELECT role, COUNT(*) AS total
        FROM users
        GROUP BY role
        ORDER BY total DESC
    """)

    if not rows:
        return "No role data found."

    parts = []
    for row in rows:
        role = str(row.get("role", "unknown")).replace("_", " ").title()
        total = int(row.get("total", 0))
        parts.append(f"{role}: {total}")

    return "Current registered users by role: " + ", ".join(parts) + "."


def answer_products():
    if not table_exists("products"):
        return "The products table was not found."

    name_column = "name" if column_exists("products", "name") else None
    price_column = "price" if column_exists("products", "price") else "retail_price" if column_exists("products", "retail_price") else None
    stock_column = "stock_quantity" if column_exists("products", "stock_quantity") else None

    if not name_column:
        return "No product name column was found."

    select_price = f", {price_column} AS price" if price_column else ", 0 AS price"
    select_stock = f", {stock_column} AS stock_quantity" if stock_column else ", 0 AS stock_quantity"

    rows = run_rows(f"""
        SELECT {name_column} AS name
        {select_price}
        {select_stock}
        FROM products
        LIMIT 5
    """)

    if not rows:
        return "No products found."

    return "\n".join([
        f"- {r.get('name', 'Unnamed Product')} (₱{float(r.get('price', 0)):,.2f}, stock: {int(r.get('stock_quantity', 0))})"
        for r in rows
    ])


def answer_producers():
    if not table_exists("users"):
        return "The users table was not found."

    if not column_exists("users", "role"):
        return "The role column was not found in the users table."

    rows = run_rows("""
        SELECT full_name
        FROM users
        WHERE role = 'producer'
        LIMIT 5
    """)

    if not rows:
        return "No producers found."

    return "\n".join([f"- {r.get('full_name', 'Unknown Producer')}" for r in rows])


def answer_revenue():
    if not table_exists("orders"):
        return "The orders table was not found."

    if not column_exists("orders", "total_amount"):
        return "The total_amount column was not found in the orders table."

    row = run_scalar("""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM orders
    """)

    total = float(row["total"]) if row else 0
    return f"Total revenue is ₱{total:,.2f}."


def answer_top_products():
    if not table_exists("order_items") or not table_exists("products"):
        return "The required product sales tables were not found."

    name_column = "name" if column_exists("products", "name") else None
    if not name_column:
        return "No product name column was found."

    rows = run_rows(f"""
        SELECT
            p.{name_column} AS name,
            COALESCE(SUM(oi.quantity), 0) AS total_sold,
            COALESCE(SUM(oi.subtotal), 0) AS total_sales
        FROM order_items oi
        LEFT JOIN products p ON oi.product_id = p.id
        GROUP BY p.id, p.{name_column}
        ORDER BY total_sold DESC, total_sales DESC
        LIMIT 5
    """)

    if not rows:
        return "No top-selling product data is available yet."

    lines = []
    for i, row in enumerate(rows, start=1):
        name = row.get("name") or "Unnamed Product"
        sold = int(row.get("total_sold", 0))
        sales = float(row.get("total_sales", 0))
        lines.append(f"{i}. {name} - {sold} sold, ₱{sales:,.2f} sales")

    return "Top-selling products:\n" + "\n".join(lines)


def answer_low_stock():
    if not table_exists("products"):
        return "The products table was not found."

    name_column = "name" if column_exists("products", "name") else None
    stock_column = "stock_quantity" if column_exists("products", "stock_quantity") else None

    if not name_column or not stock_column:
        return "The required stock columns were not found."

    rows = run_rows(f"""
        SELECT {name_column} AS name, {stock_column} AS stock_quantity
        FROM products
        WHERE {stock_column} < 10
        ORDER BY {stock_column} ASC
        LIMIT 10
    """)

    if not rows:
        return "There are currently no low-stock products."

    lines = []
    for row in rows:
        name = row.get("name") or "Unnamed Product"
        stock = int(row.get("stock_quantity", 0))
        lines.append(f"- {name}: {stock} remaining")

    return "Low-stock products:\n" + "\n".join(lines)


def answer_sap():
    if not table_exists("sap_purchases"):
        return "The sap_purchases table was not found."

    rows = run_rows("""
        SELECT
            quantity_purchased,
            total_amount,
            created_at
        FROM sap_purchases
        ORDER BY created_at DESC
        LIMIT 10
    """)

    if not rows:
        return "No recent SAP purchases were found."

    lines = []
    for row in rows:
        qty = float(row.get("quantity_purchased", 0))
        total = float(row.get("total_amount", 0))
        created = str(row.get("created_at", ""))
        lines.append(f"- Qty: {qty}, Total: ₱{total:,.2f}, Date: {created}")

    return "Recent SAP purchases:\n" + "\n".join(lines)


def answer_history():
    return (
        "Gigaquit Rhum reflects the local craftsmanship, agricultural heritage, and identity "
        "of Gigaquit, Surigao del Norte. It combines traditional rhum-making culture with "
        "modern digital innovation through its marketplace and databank platform."
    )


def answer_system():
    return (
        "Gigaquit Rhum is a modern marketplace and databank platform that connects farmers, "
        "producers, customers, and administrators in one seamless system. It supports product "
        "management, SAP transactions, e-commerce operations, and Retrieval-Augmented Generation "
        "(RAG) for intelligent databank assistance and decision support."
    )


def answer_unknown():
    return "I couldn’t understand that yet. Try asking about products, users, producers, revenue, low stock, or SAP purchases."


# -------------------------------
# MAIN LOGIC
# -------------------------------
def generate_answer(question):
    intent = detect_intent(question)

    if intent == "total_users":
        answer = answer_total_users()
    elif intent == "role_counts":
        answer = answer_role_counts()
    elif intent == "products":
        answer = answer_products()
    elif intent == "producers":
        answer = answer_producers()
    elif intent == "revenue":
        answer = answer_revenue()
    elif intent == "top_products":
        answer = answer_top_products()
    elif intent == "low_stock":
        answer = answer_low_stock()
    elif intent == "sap":
        answer = answer_sap()
    elif intent == "history":
        answer = answer_history()
    elif intent == "system":
        answer = answer_system()
    else:
        answer = answer_unknown()

    return {
        "answer": answer,
        "intent": intent
    }


# -------------------------------
# ROUTES
# -------------------------------
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "success": True,
        "message": "RAG service is live"
    })


@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({
            "success": True,
            "message": "RAG service and database are running"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Database connection failed",
            "error": str(e)
        }), 500


@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json(silent=True) or {}
        question = str(data.get("question", "")).strip()
        user_id = data.get("user_id")
        role = data.get("role", "guest")
        user_name = data.get("user_name", "Guest")

        if not question:
            return jsonify({
                "success": False,
                "answer": "Question is required"
            }), 400

        result = generate_answer(question)

        return jsonify({
            "success": True,
            "question": question,
            "answer": result["answer"],
            "intent": result["intent"],
            "user_id": user_id,
            "role": role,
            "user_name": user_name
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "answer": "Server error occurred",
            "error": str(e)
        }), 500


# -------------------------------
# RUN
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
