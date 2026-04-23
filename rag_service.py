from flask import Flask, request, jsonify
import mysql.connector
import os

app = Flask(__name__)

# 🔐 SECURE DB CONFIG (ENV VARIABLES)
DB_CONFIG = {
    "host": os.getenv("31.97.221.62"),
    "user": os.getenv("www_gigaquit_user"),
    "password": os.getenv("fcuares111"),
    "database": os.getenv("www_gigaquit_db")
}


# -------------------------------
# DATABASE HELPERS
# -------------------------------
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def run_scalar(query, params=None):
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
            cursor.close()
            conn.close()
        except:
            pass


def run_rows(query, params=None):
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
            cursor.close()
            conn.close()
        except:
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
    q = question.lower()

    if "total users" in q:
        return "total_users"

    if "role counts" in q or "farmers" in q:
        return "role_counts"

    if "revenue" in q:
        return "revenue"

    if "top" in q and "product" in q:
        return "top_products"

    if "low stock" in q:
        return "low_stock"

    if "sap" in q:
        return "sap"

    if "products" in q:
        return "products"

    if "producers" in q:
        return "producers"

    if "history" in q:
        return "history"

    if "what is" in q:
        return "system"

    return "unknown"


# -------------------------------
# ANSWERS
# -------------------------------
def answer_total_users():
    row = run_scalar("SELECT COUNT(*) AS total FROM users")
    total = row["total"] if row else 0
    return f"There are {total} registered users."


def answer_products():
    rows = run_rows("""
        SELECT name, price, stock_quantity
        FROM products
        LIMIT 5
    """)

    if not rows:
        return "No products found."

    return "\n".join([
        f"- {r['name']} (₱{r['price']}, stock: {r['stock_quantity']})"
        for r in rows
    ])


def answer_producers():
    rows = run_rows("""
        SELECT full_name FROM users WHERE role = 'producer' LIMIT 5
    """)

    if not rows:
        return "No producers found."

    return "\n".join([f"- {r['full_name']}" for r in rows])


def answer_revenue():
    row = run_scalar("""
        SELECT COALESCE(SUM(total_amount),0) AS total FROM orders
    """)

    total = row["total"] if row else 0
    return f"Total revenue is ₱{total:,.2f}"


def answer_unknown():
    return "I couldn’t understand that yet. Try asking about products, users, or revenue."


# -------------------------------
# MAIN LOGIC
# -------------------------------
def generate_answer(question):
    intent = detect_intent(question)

    if intent == "total_users":
        return answer_total_users()

    if intent == "products":
        return answer_products()

    if intent == "producers":
        return answer_producers()

    if intent == "revenue":
        return answer_revenue()

    return answer_unknown()


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
    return jsonify({
        "success": True
    })


@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json() or {}
        question = data.get("question", "").strip()

        if not question:
            return jsonify({
                "success": False,
                "answer": "Question is required"
            }), 400

        answer = generate_answer(question)

        return jsonify({
            "success": True,
            "answer": answer
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
