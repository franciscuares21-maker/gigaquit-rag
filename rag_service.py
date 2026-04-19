from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "www_gigaquit_user",
    "password": "fcuares111",
    "database": "www_gigaquit_db"
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
        row = cursor.fetchone()
        return row
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
        rows = cursor.fetchall()
        return rows
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def table_exists(table_name: str) -> bool:
    row = run_scalar("SHOW TABLES LIKE %s", (table_name,))
    return row is not None


def column_exists(table_name: str, column_name: str) -> bool:
    row = run_scalar(
        """
        SELECT COUNT(*) AS total
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (DB_CONFIG["database"], table_name, column_name)
    )
    return bool(row and int(row.get("total", 0)) > 0)


def detect_intent(question: str) -> str:
    q = question.lower().strip()

    # ADMIN / INTERNAL ANALYTICS
    if "total users" in q or "how many users" in q or "registered users" in q:
        return "total_users"

    if "farmers" in q and "producers" in q and "customers" in q:
        return "role_counts"

    if "role counts" in q or "user counts" in q:
        return "role_counts"

    if "total revenue" in q or q == "revenue" or "overall revenue" in q:
        return "total_revenue"

    if "top-selling" in q or "top selling" in q or "best-selling" in q or "best selling" in q:
        return "top_products"

    if "low stock" in q or "out of stock" in q:
        return "low_stock"

    if "sap purchases" in q or "recent sap purchases" in q or "sap sales" in q:
        return "sap_purchases"

    # PUBLIC / GENERAL KNOWLEDGE
    if "what is gigaquit rhum" in q or "about gigaquit rhum" in q or "about system" in q or "what is this system" in q:
        return "system_info"

    if "history" in q or "origin" in q or "heritage" in q:
        return "history_info"

    if "products" in q or "what products" in q or "available products" in q or "show products" in q:
        return "product_info"

    if "producers" in q or "who are the producers" in q or "verified producers" in q:
        return "producer_info"

    return "unknown"


def answer_total_users():
    if not table_exists("users"):
        return {
            "answer": "The users table was not found in the database.",
            "source": "database"
        }

    row = run_scalar("SELECT COUNT(*) AS total_users FROM users")
    total = row["total_users"] if row else 0
    return {
        "answer": f"There are currently {total} total users registered in the system.",
        "source": "database"
    }


def answer_role_counts():
    if not table_exists("users"):
        return {
            "answer": "The users table was not found in the database.",
            "source": "database"
        }

    if column_exists("users", "role"):
        rows = run_rows("""
            SELECT role, COUNT(*) AS total
            FROM users
            GROUP BY role
            ORDER BY total DESC
        """)
    else:
        return {
            "answer": "The role column was not found in the users table.",
            "source": "database"
        }

    if not rows:
        return {
            "answer": "No user role data was found in the system.",
            "source": "database"
        }

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
        return {
            "answer": "The orders table was not found in the database.",
            "source": "database"
        }

    payment_status_exists = column_exists("orders", "payment_status")
    status_exists = column_exists("orders", "status")
    total_amount_exists = column_exists("orders", "total_amount")

    if not total_amount_exists:
        return {
            "answer": "The total_amount column was not found in the orders table.",
            "source": "database"
        }

    if payment_status_exists and status_exists:
        row = run_scalar("""
            SELECT COALESCE(SUM(total_amount), 0) AS total_revenue
            FROM orders
            WHERE payment_status = 'paid' OR status IN ('completed', 'delivered')
        """)
    elif payment_status_exists:
        row = run_scalar("""
            SELECT COALESCE(SUM(total_amount), 0) AS total_revenue
            FROM orders
            WHERE payment_status = 'paid'
        """)
    elif status_exists:
        row = run_scalar("""
            SELECT COALESCE(SUM(total_amount), 0) AS total_revenue
            FROM orders
            WHERE status IN ('completed', 'delivered')
        """)
    else:
        row = run_scalar("""
            SELECT COALESCE(SUM(total_amount), 0) AS total_revenue
            FROM orders
        """)

    total = float(row["total_revenue"]) if row else 0.0
    return {
        "answer": f"The current total revenue recorded in the system is ₱{total:,.2f}.",
        "source": "database"
    }


def answer_top_products():
    if not table_exists("order_items") or not table_exists("products"):
        return {
            "answer": "The required product sales tables were not found in the database.",
            "source": "database"
        }

    name_column = "name" if column_exists("products", "name") else "product_name" if column_exists("products", "product_name") else None

    if not name_column:
        return {
            "answer": "No product name column was found in the products table.",
            "source": "database"
        }

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
        return {
            "answer": "No top-selling product data is available yet.",
            "source": "database"
        }

    lines = []
    for i, row in enumerate(rows, start=1):
        name = row.get("name") or "Unnamed Product"
        sold = int(row.get("total_sold", 0))
        sales = float(row.get("total_sales", 0))
        lines.append(f"{i}. {name} - {sold} sold, ₱{sales:,.2f} sales")

    return {
        "answer": "Top-selling products:\n" + "\n".join(lines),
        "source": "database"
    }


def answer_low_stock():
    if not table_exists("products"):
        return {
            "answer": "The products table was not found in the database.",
            "source": "database"
        }

    name_column = "name" if column_exists("products", "name") else "product_name" if column_exists("products", "product_name") else None
    stock_column = "stock_quantity" if column_exists("products", "stock_quantity") else None

    if not name_column or not stock_column:
        return {
            "answer": "The required product stock columns were not found in the products table.",
            "source": "database"
        }

    has_created_at = column_exists("products", "created_at")

    if has_created_at:
        rows = run_rows(f"""
            SELECT {name_column} AS name, {stock_column} AS stock_quantity
            FROM products
            WHERE {stock_column} < 10
            ORDER BY {stock_column} ASC, created_at DESC
            LIMIT 10
        """)
    else:
        rows = run_rows(f"""
            SELECT {name_column} AS name, {stock_column} AS stock_quantity
            FROM products
            WHERE {stock_column} < 10
            ORDER BY {stock_column} ASC
            LIMIT 10
        """)

    if not rows:
        return {
            "answer": "There are currently no low-stock products below the threshold.",
            "source": "database"
        }

    lines = []
    for row in rows:
        name = row.get("name") or "Unnamed Product"
        stock = int(row.get("stock_quantity", 0))
        lines.append(f"- {name}: {stock} remaining")

    return {
        "answer": "Low-stock products:\n" + "\n".join(lines),
        "source": "database"
    }


def answer_sap_purchases():
    if not table_exists("sap_purchases"):
        return {
            "answer": "The sap_purchases table was not found in the database.",
            "source": "database"
        }

    rows = run_rows("""
        SELECT 
            uf.full_name AS farmer_name,
            up.full_name AS producer_name,
            sp.quantity_purchased,
            sp.total_amount,
            sp.created_at
        FROM sap_purchases sp
        LEFT JOIN users uf ON sp.farmer_id = uf.id
        LEFT JOIN users up ON sp.producer_id = up.id
        ORDER BY sp.created_at DESC
        LIMIT 10
    """)

    if not rows:
        return {
            "answer": "No recent SAP purchases were found.",
            "source": "database"
        }

    lines = []
    for row in rows:
        farmer = row.get("farmer_name") or "Unknown Farmer"
        producer = row.get("producer_name") or "Unknown Producer"
        qty = float(row.get("quantity_purchased", 0))
        total = float(row.get("total_amount", 0))
        created = str(row.get("created_at", ""))
        lines.append(
            f"- Farmer: {farmer}, Producer: {producer}, Qty: {qty}, Total: ₱{total:,.2f}, Date: {created}"
        )

    return {
        "answer": "Recent SAP purchases:\n" + "\n".join(lines),
        "source": "database"
    }


def answer_system_info():
    return {
        "answer": (
            "Gigaquit Rhum is a modern marketplace and databank platform that connects farmers, "
            "producers, customers, and administrators in one seamless system. It supports product "
            "management, SAP transactions, e-commerce operations, and Retrieval-Augmented Generation "
            "(RAG) for intelligent databank assistance and decision support."
        ),
        "source": "knowledge_base"
    }


def answer_history_info():
    return {
        "answer": (
            "Gigaquit Rhum reflects the local craftsmanship, agricultural heritage, and identity of "
            "Gigaquit, Surigao del Norte. It represents a combination of traditional rhum-making culture "
            "and modern digital innovation through its marketplace and databank platform."
        ),
        "source": "knowledge_base"
    }


def answer_product_info():
    if not table_exists("products"):
        return {
            "answer": "The products table was not found in the database.",
            "source": "database"
        }

    name_column = "name" if column_exists("products", "name") else "product_name" if column_exists("products", "product_name") else None
    price_column = "price" if column_exists("products", "price") else "retail_price" if column_exists("products", "retail_price") else None
    stock_column = "stock_quantity" if column_exists("products", "stock_quantity") else None
    active_column = "is_active" if column_exists("products", "is_active") else None

    if not name_column:
        return {
            "answer": "No product name column was found in the products table.",
            "source": "database"
        }

    where_clause = f"WHERE {active_column} = 1" if active_column else ""
    select_price = f", {price_column} AS price" if price_column else ", 0 AS price"
    select_stock = f", {stock_column} AS stock_quantity" if stock_column else ", 0 AS stock_quantity"
    order_clause = "ORDER BY is_featured DESC, created_at DESC" if column_exists("products", "is_featured") and column_exists("products", "created_at") else "ORDER BY id DESC"

    rows = run_rows(f"""
        SELECT {name_column} AS name
        {select_price}
        {select_stock}
        FROM products
        {where_clause}
        {order_clause}
        LIMIT 5
    """)

    if not rows:
        return {
            "answer": "No products are currently available in the system.",
            "source": "database"
        }

    lines = []
    for row in rows:
        name = row.get("name") or "Unnamed Product"
        price = float(row.get("price", 0))
        stock = int(row.get("stock_quantity", 0))
        lines.append(f"- {name} (₱{price:,.2f}, Stock: {stock})")

    return {
        "answer": "Here are some available products:\n" + "\n".join(lines),
        "source": "database"
    }


def answer_producer_info():
    if table_exists("producer_profiles"):
        company_col = "company_name" if column_exists("producer_profiles", "company_name") else None
        location_col = "municipality" if column_exists("producer_profiles", "municipality") else None
        verification_col = "verification_status" if column_exists("producer_profiles", "verification_status") else None

        if company_col:
            where_clause = f"WHERE {verification_col} = 'verified'" if verification_col else ""
            select_location = f", {location_col} AS municipality" if location_col else ", '' AS municipality"

            rows = run_rows(f"""
                SELECT {company_col} AS company_name
                {select_location}
                FROM producer_profiles
                {where_clause}
                LIMIT 5
            """)

            if rows:
                lines = []
                for row in rows:
                    name = row.get("company_name", "Unknown Producer")
                    location = row.get("municipality", "")
                    if location:
                        lines.append(f"- {name} ({location})")
                    else:
                        lines.append(f"- {name}")

                return {
                    "answer": "Here are some producers in the system:\n" + "\n".join(lines),
                    "source": "database"
                }

    if table_exists("users") and column_exists("users", "role"):
        rows = run_rows("""
            SELECT full_name
            FROM users
            WHERE role IN ('producer', 'farmer_producer')
            LIMIT 5
        """)

        if rows:
            lines = []
            for row in rows:
                name = row.get("full_name") or "Unknown Producer"
                lines.append(f"- {name}")

            return {
                "answer": "Here are some producers in the system:\n" + "\n".join(lines),
                "source": "database"
            }

    return {
        "answer": "No producer information is currently available.",
        "source": "database"
    }


def answer_unknown():
    return {
        "answer": (
            "I could not confidently match that question yet. "
            "You can ask about the system, history, products, producers, total users, revenue, "
            "top-selling products, low-stock products, or recent SAP purchases."
        ),
        "source": "assistant"
    }


def generate_answer(question: str):
    intent = detect_intent(question)

    if intent == "total_users":
        result = answer_total_users()
    elif intent == "role_counts":
        result = answer_role_counts()
    elif intent == "total_revenue":
        result = answer_total_revenue()
    elif intent == "top_products":
        result = answer_top_products()
    elif intent == "low_stock":
        result = answer_low_stock()
    elif intent == "sap_purchases":
        result = answer_sap_purchases()
    elif intent == "system_info":
        result = answer_system_info()
    elif intent == "history_info":
        result = answer_history_info()
    elif intent == "product_info":
        result = answer_product_info()
    elif intent == "producer_info":
        result = answer_producer_info()
    else:
        result = answer_unknown()

    result["intent"] = intent
    return result


@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({
            "success": True,
            "message": "RAG service is running.",
            "database": "connected"
        })
    except Error as e:
        return jsonify({
            "success": False,
            "message": "RAG service is running but database connection failed.",
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
                "answer": "Question is required."
            }), 400

        result = generate_answer(question)

        return jsonify({
            "success": True,
            "question": question,
            "answer": result["answer"],
            "source": result["source"],
            "intent": result["intent"],
            "user_id": user_id,
            "role": role,
            "user_name": user_name
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "answer": "An error occurred while processing the question.",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)