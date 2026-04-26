from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

BRIDGE_URL = os.getenv(
    "BRIDGE_URL",
    "https://www.gigaquitrhum.site/api/db_bridge.php"
)


def bridge_get(action):
    try:
        res = requests.get(BRIDGE_URL, params={"action": action}, timeout=10)
        return res.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def money(value):
    try:
        return f"₱{float(value or 0):,.2f}"
    except Exception:
        return "₱0.00"


def detect_intent(question):
    q = question.lower().strip()

    if "overview" in q or "database" in q or "tables" in q:
        return "database_overview"
    if "gigaquit rhum" in q or "what is this system" in q or "about system" in q:
        return "system_info"
    if "history" in q or "origin" in q or "heritage" in q:
        return "history_info"
    if "total users" in q or "how many users" in q or "registered users" in q:
        return "total_users"
    if "role" in q or "farmers producers customers" in q:
        return "role_counts"
    if "farmers" in q and "sap" not in q:
        return "farmers"
    if "producers" in q:
        return "producers"
    if "customers" in q:
        return "customers"
    if "recent users" in q or "latest users" in q:
        return "recent_users"
    if "show products" in q or "available products" in q or "products" in q:
        return "products"
    if "low stock" in q or "out of stock" in q:
        return "low_stock"
    if "top selling" in q or "top-selling" in q or "best selling" in q or "best-selling" in q:
        return "top_products"
    if "recent orders" in q or "latest orders" in q:
        return "recent_orders"
    if "revenue" in q or "sales" in q or "orders summary" in q or "total orders" in q:
        return "orders_summary"
    if "sap summary" in q or "sap total" in q:
        return "sap_summary"
    if "sap" in q and ("purchase" in q or "recent" in q or "sales" in q):
        return "recent_sap_purchases"
    if "sap inventory" in q or "sap stock" in q or "sap submissions" in q:
        return "sap_inventory"
    if "reviews" in q or "ratings" in q:
        return "product_reviews"
    if "knowledge" in q or "databank" in q:
        return "knowledge_base"

    return "unknown"


def answer_system_info():
    return {
        "answer": (
            "Gigaquit Rhum is a databank and marketplace system for the local rhum industry of "
            "Gigaquit, Surigao del Norte. It connects farmers, producers, customers, and administrators "
            "in one platform. It supports SAP supply management, product selling, order tracking, "
            "payments, reports, and an AI-powered RAG assistant."
        ),
        "source": "knowledge_base"
    }


def answer_history_info():
    return {
        "answer": (
            "Gigaquit Rhum reflects local craftsmanship, agricultural identity, and rhum-making culture "
            "of Gigaquit, Surigao del Norte. The system modernizes this local industry through a digital "
            "databank and marketplace."
        ),
        "source": "knowledge_base"
    }


def list_lines(title, rows, formatter, empty):
    if not rows:
        return {"answer": empty, "source": "php_bridge"}
    return {"answer": title + "\n" + "\n".join(formatter(r) for r in rows), "source": "php_bridge"}


def answer_total_users():
    d = bridge_get("total_users")
    total = d.get("data", {}).get("total_users", 0)
    return {"answer": f"There are currently {total} registered users in the system.", "source": "php_bridge"}


def answer_role_counts():
    d = bridge_get("role_counts")
    rows = d.get("data", [])
    return list_lines(
        "Current user role counts:",
        rows,
        lambda r: f"- {str(r.get('role','Unknown')).replace('_',' ').title()}: {r.get('total',0)}",
        "No role data found."
    )


def answer_people(action, title):
    d = bridge_get(action)
    rows = d.get("data", [])
    return list_lines(
        title,
        rows,
        lambda r: f"- {r.get('full_name','Unknown')} ({r.get('email','No email')})",
        f"No {title.lower()} found."
    )


def answer_products():
    d = bridge_get("products")
    rows = d.get("data", [])
    return list_lines(
        "Available products:",
        rows,
        lambda r: f"- {r.get('name','Unnamed Product')} | Price: {money(r.get('price'))} | Stock: {r.get('stock',0)}",
        "No products found."
    )


def answer_low_stock():
    d = bridge_get("low_stock")
    rows = d.get("data", [])
    return list_lines(
        "Low-stock products:",
        rows,
        lambda r: f"- {r.get('name','Unnamed Product')}: {r.get('stock',0)} remaining",
        "There are currently no low-stock products."
    )


def answer_orders_summary():
    d = bridge_get("orders_summary")
    x = d.get("data", {})
    return {
        "answer": (
            "Orders and sales summary:\n"
            f"- Total orders: {x.get('total_orders',0)}\n"
            f"- Paid orders: {x.get('paid_orders',0)}\n"
            f"- Pending orders: {x.get('pending_orders',0)}\n"
            f"- Total revenue: {money(x.get('total_revenue',0))}"
        ),
        "source": "php_bridge"
    }


def answer_recent_orders():
    d = bridge_get("recent_orders")
    rows = d.get("data", [])
    return list_lines(
        "Recent orders:",
        rows,
        lambda r: f"- {r.get('order_number','Order')} | {r.get('customer_name','Unknown')} | {money(r.get('total_amount'))} | {r.get('status','N/A')} | {r.get('payment_status','N/A')}",
        "No recent orders found."
    )


def answer_top_products():
    d = bridge_get("top_products")
    rows = d.get("data", [])
    return list_lines(
        "Top-selling products:",
        rows,
        lambda r: f"- {r.get('name','Unnamed Product')} | Sold: {r.get('total_sold',0)} | Sales: {money(r.get('total_sales',0))}",
        "No top-selling product data found."
    )


def answer_recent_sap_purchases():
    d = bridge_get("recent_sap_purchases")
    rows = d.get("data", [])
    return list_lines(
        "Recent SAP purchases:",
        rows,
        lambda r: f"- Farmer: {r.get('farmer_name','Unknown')} | Producer: {r.get('producer_name','Unknown')} | Qty: {r.get('quantity',0)} L | Amount: {money(r.get('total_amount'))} | Date: {r.get('created_at','')}",
        "No recent SAP purchases found."
    )


def answer_sap_inventory():
    d = bridge_get("sap_inventory")
    rows = d.get("data", [])
    return list_lines(
        "SAP inventory records:",
        rows,
        lambda r: f"- Farmer: {r.get('farmer_name','Unknown')} | Submitted: {r.get('quantity_liters',0)} L | Purchased: {r.get('purchased_liters',0)} L | Remaining: {r.get('remaining_liters',0)} L | Status: {r.get('availability_status','N/A')}",
        "No SAP inventory records found."
    )


def answer_sap_summary():
    d = bridge_get("sap_summary")
    x = d.get("data", {})
    return {
        "answer": (
            "SAP summary:\n"
            f"- Submitted liters: {x.get('submitted_liters',0)} L\n"
            f"- Purchased liters: {x.get('purchased_liters',0)} L\n"
            f"- Total SAP amount: {money(x.get('sap_amount',0))}"
        ),
        "source": "php_bridge"
    }


def answer_reviews():
    d = bridge_get("product_reviews")
    rows = d.get("data", [])
    return list_lines(
        "Recent product reviews:",
        rows,
        lambda r: f"- Rating: {r.get('rating','N/A')} | Customer: {r.get('customer_name','Unknown')} | Review: {r.get('review','')}",
        "No product reviews found."
    )


def answer_knowledge_base():
    d = bridge_get("knowledge_base")
    rows = d.get("data", [])
    return list_lines(
        "Knowledge base records:",
        rows,
        lambda r: "- " + " | ".join([f"{k}: {v}" for k, v in r.items() if v is not None]),
        "No knowledge base records found."
    )


def answer_database_overview():
    d = bridge_get("database_overview")
    data = d.get("data", {})
    if not data:
        return {"answer": "No database overview available.", "source": "php_bridge"}

    lines = [f"- {table}: {count} records" for table, count in data.items()]
    return {"answer": "Database overview:\n" + "\n".join(lines), "source": "php_bridge"}


def answer_unknown():
    return {
        "answer": (
            "I can answer questions about users, roles, farmers, producers, customers, products, low stock, "
            "orders, revenue, recent orders, top-selling products, SAP purchases, SAP inventory, SAP summary, "
            "reviews, knowledge base, and database overview."
        ),
        "source": "assistant"
    }


def generate_answer(question):
    intent = detect_intent(question)

    handlers = {
        "system_info": answer_system_info,
        "history_info": answer_history_info,
        "total_users": answer_total_users,
        "role_counts": answer_role_counts,
        "recent_users": lambda: answer_people("recent_users", "Recent users:"),
        "farmers": lambda: answer_people("farmers", "Farmers:"),
        "producers": lambda: answer_people("producers", "Producers:"),
        "customers": lambda: answer_people("customers", "Customers:"),
        "products": answer_products,
        "low_stock": answer_low_stock,
        "orders_summary": answer_orders_summary,
        "recent_orders": answer_recent_orders,
        "top_products": answer_top_products,
        "recent_sap_purchases": answer_recent_sap_purchases,
        "sap_inventory": answer_sap_inventory,
        "sap_summary": answer_sap_summary,
        "product_reviews": answer_reviews,
        "knowledge_base": answer_knowledge_base,
        "database_overview": answer_database_overview,
    }

    result = handlers.get(intent, answer_unknown)()
    result["intent"] = intent
    return result


@app.route("/", methods=["GET"])
def root():
    return jsonify({"success": True, "message": "Gigaquit RAG API is running."})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"success": True, "message": "RAG service is running.", "bridge": "not_checked"})


@app.route("/bridge-health", methods=["GET"])
def bridge_health():
    data = bridge_get("health")
    return jsonify({"success": bool(data.get("success")), "message": "Bridge checked.", "bridge_response": data})


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()

    if not question:
        return jsonify({"success": False, "answer": "Question is required."}), 400

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


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
