from flask import Flask, request, jsonify
import os
import mysql.connector

app = Flask(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", ""),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", ""),
    "port": int(os.getenv("DB_PORT", "3306")),
}


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def run_scalar(query, params=None):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def run_rows(query, params=None):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def table_exists(table_name):
    try:
        row = run_scalar("SHOW TABLES LIKE %s", (table_name,))
        return row is not None
    except Exception:
        return False


def column_exists(table_name, column_name):
    try:
        row = run_scalar("""
            SELECT COUNT(*) AS total
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = %s
              AND COLUMN_NAME = %s
        """, (DB_CONFIG["database"], table_name, column_name))
        return bool(row and int(row.get("total", 0)) > 0)
    except Exception:
        return False


def money(value):
    return f"₱{float(value or 0):,.2f}"


def detect_intent(question):
    q = question.lower().strip()

    if "gigaquit rhum" in q or "what is this system" in q or "about system" in q:
        return "system_info"
    if "history" in q or "origin" in q or "heritage" in q:
        return "history_info"
    if "show products" in q or "available products" in q or "products" in q:
        return "product_info"
    if "producer" in q or "producers" in q:
        return "producer_info"
    if "total users" in q or "how many users" in q or "registered users" in q:
        return "total_users"
    if "role counts" in q or "user counts" in q or ("farmers" in q and "producers" in q and "customers" in q):
        return "role_counts"
    if "total revenue" in q or "overall revenue" in q or "revenue" in q:
        return "total_revenue"
    if "orders" in q or "total orders" in q or "pending orders" in q:
        return "orders_summary"
    if "top selling" in q or "top-selling" in q or "best selling" in q or "best-selling" in q:
        return "top_products"
    if "low stock" in q or "out of stock" in q:
        return "low_stock"
    if "sap purchases" in q or "recent sap purchases" in q or "sap sales" in q or "sap purchase" in q:
        return "sap_purchases"

    return "unknown"


def answer_system_info():
    return {
        "answer": (
            "Gigaquit Rhum is a databank and marketplace system for the local rhum industry of "
            "Gigaquit, Surigao del Norte. It connects farmers, producers, customers, and administrators "
            "in one platform. The system supports SAP supply management, product selling, order tracking, "
            "payments, printable reports, and an AI-powered RAG assistant for databank insights."
        ),
        "source": "knowledge_base"
    }


def answer_history_info():
    return {
        "answer": (
            "Gigaquit Rhum reflects the local craftsmanship, agricultural identity, and rhum-making culture "
            "of Gigaquit, Surigao del Norte. The system helps modernize this local industry by organizing "
            "SAP supply, producer products, customer orders, and business records through a digital databank."
        ),
        "source": "knowledge_base"
    }


def answer_total_users():
    if not table_exists("users"):
        return {"answer": "The users table was not found in the database.", "source": "database"}

    row = run_scalar("SELECT COUNT(*) AS total FROM users")
    return {
        "answer": f"There are currently {int(row.get('total', 0))} registered users in the system.",
        "source": "database"
    }


def answer_role_counts():
    if not table_exists("users") or not column_exists("users", "role"):
        return {"answer": "User role data is not available in the database.", "source": "database"}

    rows = run_rows("""
        SELECT role, COUNT(*) AS total
        FROM users
        GROUP BY role
        ORDER BY total DESC
    """)

    if not rows:
        return {"answer": "No user role data was found.", "source": "database"}

    parts = []
    for row in rows:
        role = str(row.get("role", "unknown")).replace("_", " ").title()
        total = int(row.get("total", 0))
        parts.append(f"{role}: {total}")

    return {
        "answer": "Current registered users by role: " + ", ".join(parts) + ".",
        "source": "database"
    }


def answer_total_revenue():
    if not table_exists("orders"):
        return {"answer": "The orders table was not found in the database.", "source": "database"}

    if not column_exists("orders", "total_amount"):
        return {"answer": "The total_amount column was not found in the orders table.", "source": "database"}

    if column_exists("orders", "payment_status"):
        row = run_scalar("""
            SELECT COALESCE(SUM(total_amount), 0) AS total
            FROM orders
            WHERE payment_status = 'paid'
        """)
    else:
        row = run_scalar("""
            SELECT COALESCE(SUM(total_amount), 0) AS total
            FROM orders
        """)

    return {
        "answer": f"The current total paid revenue recorded in the system is {money(row.get('total', 0))}.",
        "source": "database"
    }


def answer_orders_summary():
    if not table_exists("orders"):
        return {"answer": "The orders table was not found in the database.", "source": "database"}

    total = run_scalar("SELECT COUNT(*) AS total FROM orders")

    paid = {"total": 0}
    pending = {"total": 0}

    if column_exists("orders", "payment_status"):
        paid = run_scalar("SELECT COUNT(*) AS total FROM orders WHERE payment_status = 'paid'")

    if column_exists("orders", "status"):
        pending = run_scalar("SELECT COUNT(*) AS total FROM orders WHERE status = 'pending'")

    return {
        "answer": (
            f"Order summary: {int(total.get('total', 0))} total orders, "
            f"{int(paid.get('total', 0))} paid orders, and "
            f"{int(pending.get('total', 0))} pending orders."
        ),
        "source": "database"
    }


def answer_product_info():
    if not table_exists("products"):
        return {"answer": "The products table was not found in the database.", "source": "database"}

    name_col = "name" if column_exists("products", "name") else None
    price_col = "price" if column_exists("products", "price") else "retail_price" if column_exists("products", "retail_price") else None
    stock_col = "stock_quantity" if column_exists("products", "stock_quantity") else None

    if not name_col:
        return {"answer": "No product name column was found in the products table.", "source": "database"}

    rows = run_rows(f"""
        SELECT 
            {name_col} AS name,
            {price_col if price_col else '0'} AS price,
            {stock_col if stock_col else '0'} AS stock
        FROM products
        ORDER BY id DESC
        LIMIT 5
    """)

    if not rows:
        return {"answer": "No products are currently available in the system.", "source": "database"}

    lines = []
    for row in rows:
        lines.append(
            f"- {row.get('name') or 'Unnamed Product'} "
            f"({money(row.get('price', 0))}, Stock: {int(row.get('stock', 0))})"
        )

    return {
        "answer": "Here are some products in the marketplace:\n" + "\n".join(lines),
        "source": "database"
    }


def answer_producer_info():
    if not table_exists("users") or not column_exists("users", "role"):
        return {"answer": "No producer information is currently available.", "source": "database"}

    rows = run_rows("""
        SELECT full_name
        FROM users
        WHERE role IN ('producer', 'farmer_producer')
        ORDER BY full_name ASC
        LIMIT 5
    """)

    if not rows:
        return {"answer": "No producer information is currently available.", "source": "database"}

    lines = []
    for row in rows:
        lines.append(f"- {row.get('full_name') or 'Unknown Producer'}")

    return {
        "answer": "Here are some producers in the system:\n" + "\n".join(lines),
        "source": "database"
    }


def answer_top_products():
    if not table_exists("order_items") or not table_exists("products"):
        return {"answer": "The required product sales tables were not found.", "source": "database"}

    name_col = "name" if column_exists("products", "name") else None

    if not name_col:
        return {"answer": "No product name column was found.", "source": "database"}

    rows = run_rows(f"""
        SELECT 
            p.{name_col} AS name,
            COALESCE(SUM(oi.quantity), 0) AS total_sold,
            COALESCE(SUM(oi.subtotal), 0) AS total_sales
        FROM order_items oi
        LEFT JOIN products p ON oi.product_id = p.id
        GROUP BY p.id, p.{name_col}
        ORDER BY total_sold DESC, total_sales DESC
        LIMIT 5
    """)

    if not rows:
        return {"answer": "No top-selling product data is available yet.", "source": "database"}

    lines = []
    for i, row in enumerate(rows, 1):
        lines.append(
            f"{i}. {row.get('name') or 'Unnamed Product'} - "
            f"{int(row.get('total_sold', 0))} sold, {money(row.get('total_sales', 0))} sales"
        )

    return {
        "answer": "Top-selling products:\n" + "\n".join(lines),
        "source": "database"
    }


def answer_low_stock():
    if not table_exists("products"):
        return {"answer": "The products table was not found.", "source": "database"}

    name_col = "name" if column_exists("products", "name") else None
    stock_col = "stock_quantity" if column_exists("products", "stock_quantity") else None

    if not name_col or not stock_col:
        return {"answer": "Product stock columns are not available.", "source": "database"}

    rows = run_rows(f"""
        SELECT {name_col} AS name, {stock_col} AS stock
        FROM products
        WHERE {stock_col} < 10
        ORDER BY {stock_col} ASC
        LIMIT 10
    """)

    if not rows:
        return {"answer": "There are currently no low-stock products below the threshold.", "source": "database"}

    lines = []
    for row in rows:
        lines.append(f"- {row.get('name') or 'Unnamed Product'}: {int(row.get('stock', 0))} remaining")

    return {
        "answer": "Low-stock products:\n" + "\n".join(lines),
        "source": "database"
    }


def answer_sap_purchases():
    if not table_exists("sap_purchases"):
        return {"answer": "The sap_purchases table was not found.", "source": "database"}

    qty_col = None
    for col in ["quantity_purchased", "quantity", "quantity_liters", "liters"]:
        if column_exists("sap_purchases", col):
            qty_col = col
            break

    amount_col = None
    for col in ["total_amount", "total_price", "amount", "subtotal"]:
        if column_exists("sap_purchases", col):
            amount_col = col
            break

    if not qty_col:
        return {"answer": "SAP purchase quantity column was not found.", "source": "database"}

    amount_select = f"sp.{amount_col}" if amount_col else "0"

    rows = run_rows(f"""
        SELECT 
            COALESCE(uf.full_name, 'Unknown Farmer') AS farmer_name,
            COALESCE(up.full_name, 'Unknown Producer') AS producer_name,
            sp.{qty_col} AS quantity_purchased,
            {amount_select} AS total_amount,
            sp.created_at
        FROM sap_purchases sp
        LEFT JOIN users uf ON sp.farmer_id = uf.id
        LEFT JOIN users up ON sp.producer_id = up.id
        ORDER BY sp.created_at DESC
        LIMIT 10
    """)

    if not rows:
        return {"answer": "No recent SAP purchases were found.", "source": "database"}

    lines = []
    for row in rows:
        lines.append(
            f"- Farmer: {row.get('farmer_name')}, Producer: {row.get('producer_name')}, "
            f"Qty: {float(row.get('quantity_purchased', 0)):,.2f} L, "
            f"Total: {money(row.get('total_amount', 0))}, Date: {row.get('created_at')}"
        )

    return {
        "answer": "Recent SAP purchases:\n" + "\n".join(lines),
        "source": "database"
    }


def answer_unknown():
    return {
        "answer": (
            "I could not confidently match that question yet. You may ask about Gigaquit Rhum, "
            "history, products, producers, total users, role counts, total revenue, order summary, "
            "top-selling products, low-stock products, or recent SAP purchases."
        ),
        "source": "assistant"
    }


def generate_answer(question):
    intent = detect_intent(question)

    handlers = {
        "system_info": answer_system_info,
        "history_info": answer_history_info,
        "product_info": answer_product_info,
        "producer_info": answer_producer_info,
        "total_users": answer_total_users,
        "role_counts": answer_role_counts,
        "total_revenue": answer_total_revenue,
        "orders_summary": answer_orders_summary,
        "top_products": answer_top_products,
        "low_stock": answer_low_stock,
        "sap_purchases": answer_sap_purchases,
    }

    result = handlers.get(intent, answer_unknown)()
    result["intent"] = intent
    return result


@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "success": True,
        "message": "Gigaquit RAG API is running."
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "success": True,
        "message": "RAG service is running.",
        "database": "not_checked"
    })


@app.route("/db-health", methods=["GET"])
def db_health():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({
            "success": True,
            "message": "Database connected.",
            "database": "connected"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Database connection failed.",
            "database": "not_connected",
            "error": str(e)
        }), 500


@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json(silent=True) or {}
        question = str(data.get("question", "")).strip()

        if not question:
            return jsonify({
                "success": False,
                "answer": "Question is required."
            }), 400

        result = generate_answer(question)

        return jsonify({
            "success": True,
            "question": question,
            "answer": result["answer"],
            "source": result["source"],
            "intent": result["intent"],
            "user_id": data.get("user_id"),
            "role": data.get("role", "guest"),
            "user_name": data.get("user_name", "Guest")
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "answer": "An error occurred while processing the question.",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
