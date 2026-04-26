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

    if "gigaquit rhum" in q or "what is this system" in q or "about system" in q:
        return "system_info"

    if "history" in q or "origin" in q or "heritage" in q:
        return "history_info"

    if "total users" in q or "how many users" in q or "registered users" in q:
        return "total_users"

    if "role" in q or "farmers producers customers" in q:
        return "role_counts"

    if "show products" in q or "available products" in q or "products" in q:
        return "products"

    if "low stock" in q or "out of stock" in q:
        return "low_stock"

    if "top selling" in q or "top-selling" in q or "best selling" in q or "best-selling" in q:
        return "top_products"

    if "revenue" in q or "sales" in q or "orders summary" in q or "total orders" in q:
        return "orders_summary"

    if "recent orders" in q:
        return "recent_orders"

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
            "in one platform. The system supports SAP supply management, product selling, order tracking, "
            "payments, printable reports, and an AI-powered RAG assistant for databank insights."
        ),
        "source": "knowledge_base"
    }


def answer_history_info():
    return {
        "answer": (
            "Gigaquit Rhum reflects the local craftsmanship, agricultural identity, and rhum-making culture "
            "of Gigaquit, Surigao del Norte. The system modernizes these operations through a digital "
            "databank and marketplace."
        ),
        "source": "knowledge_base"
    }


def answer_total_users():
    data = bridge_get("total_users")
    if data.get("success"):
        total = data.get("data", {}).get("total_users", 0)
        return {
            "answer": f"There are currently {total} registered users in the system.",
            "source": "php_bridge"
        }
    return {"answer": "Unable to fetch total users right now.", "source": "php_bridge"}


def answer_role_counts():
    data = bridge_get("role_counts")
    if data.get("success"):
        rows = data.get("data", [])
        if not rows:
            return {"answer": "No role count data found.", "source": "php_bridge"}

        lines = []
        for r in rows:
            role = str(r.get("role", "Unknown")).replace("_", " ").title()
            total = r.get("total", 0)
            lines.append(f"- {role}: {total}")

        return {
            "answer": "Current user role counts:\n" + "\n".join(lines),
            "source": "php_bridge"
        }

    return {"answer": "Unable to fetch role counts right now.", "source": "php_bridge"}


def answer_products():
    data = bridge_get("products")
    if data.get("success"):
        rows = data.get("data", [])
        if not rows:
            return {"answer": "No products found in the marketplace.", "source": "php_bridge"}

        lines = []
        for r in rows:
            lines.append(
                f"- {r.get('name', 'Unnamed Product')} | Price: {money(r.get('price'))} | Stock: {r.get('stock', 0)}"
            )

        return {
            "answer": "Available products:\n" + "\n".join(lines),
            "source": "php_bridge"
        }

    return {"answer": "Unable to fetch product data right now.", "source": "php_bridge"}


def answer_low_stock():
    data = bridge_get("low_stock")
    if data.get("success"):
        rows = data.get("data", [])
        if not rows:
            return {"answer": "There are currently no low-stock products.", "source": "php_bridge"}

        lines = []
        for r in rows:
            lines.append(f"- {r.get('name', 'Unnamed Product')}: {r.get('stock', 0)} remaining")

        return {
            "answer": "Low-stock products:\n" + "\n".join(lines),
            "source": "php_bridge"
        }

    return {"answer": "Unable to fetch low-stock data right now.", "source": "php_bridge"}


def answer_orders_summary():
    data = bridge_get("orders_summary")
    if data.get("success"):
        d = data.get("data", {})
        return {
            "answer": (
                f"Orders summary:\n"
                f"- Total orders: {d.get('total_orders', 0)}\n"
                f"- Paid orders: {d.get('paid_orders', 0)}\n"
                f"- Pending orders: {d.get('pending_orders', 0)}\n"
                f"- Total revenue: {money(d.get('total_revenue', 0))}"
            ),
            "source": "php_bridge"
        }

    return {"answer": "Unable to fetch orders summary right now.", "source": "php_bridge"}


def answer_recent_orders():
    data = bridge_get("recent_orders")
    if data.get("success"):
        rows = data.get("data", [])
        if not rows:
            return {"answer": "No recent orders found.", "source": "php_bridge"}

        lines = []
        for r in rows:
            lines.append(
                f"- {r.get('order_number', 'Order')} | Customer: {r.get('customer_name', 'Unknown')} | "
                f"Amount: {money(r.get('total_amount'))} | Status: {r.get('status', 'N/A')} | "
                f"Payment: {r.get('payment_status', 'N/A')}"
            )

        return {
            "answer": "Recent orders:\n" + "\n".join(lines),
            "source": "php_bridge"
        }

    return {"answer": "Unable to fetch recent orders right now.", "source": "php_bridge"}


def answer_top_products():
    data = bridge_get("top_products")
    if data.get("success"):
        rows = data.get("data", [])
        if not rows:
            return {"answer": "No top-selling product data found.", "source": "php_bridge"}

        lines = []
        for i, r in enumerate(rows, start=1):
            lines.append(
                f"{i}. {r.get('name', 'Unnamed Product')} - {r.get('total_sold', 0)} sold, "
                f"{money(r.get('total_sales', 0))} sales"
            )

        return {
            "answer": "Top-selling products:\n" + "\n".join(lines),
            "source": "php_bridge"
        }

    return {"answer": "Unable to fetch top products right now.", "source": "php_bridge"}


def answer_recent_sap_purchases():
    data = bridge_get("recent_sap_purchases")
    if data.get("success"):
        rows = data.get("data", [])
        if not rows:
            return {"answer": "No recent SAP purchases found.", "source": "php_bridge"}

        lines = []
        for r in rows:
            lines.append(
                f"- Farmer: {r.get('farmer_name', 'Unknown')} | Producer: {r.get('producer_name', 'Unknown')} | "
                f"Qty: {r.get('quantity', 0)} L | Amount: {money(r.get('total_amount'))} | Date: {r.get('created_at', '')}"
            )

        return {
            "answer": "Recent SAP purchases:\n" + "\n".join(lines),
            "source": "php_bridge"
        }

    return {"answer": "Unable to fetch SAP purchases right now.", "source": "php_bridge"}


def answer_sap_inventory():
    data = bridge_get("sap_inventory")
    if data.get("success"):
        rows = data.get("data", [])
        if not rows:
            return {"answer": "No SAP inventory records found.", "source": "php_bridge"}

        lines = []
        for r in rows:
            lines.append(
                f"- Farmer: {r.get('farmer_name', 'Unknown')} | Submitted: {r.get('quantity_liters', 0)} L | "
                f"Purchased: {r.get('purchased_liters', 0)} L | Remaining: {r.get('remaining_liters', 0)} L | "
                f"Grade: {r.get('quality_grade', 'N/A')} | Status: {r.get('availability_status', 'N/A')}"
            )

        return {
            "answer": "SAP inventory records:\n" + "\n".join(lines),
            "source": "php_bridge"
        }

    return {"answer": "Unable to fetch SAP inventory right now.", "source": "php_bridge"}


def answer_product_reviews():
    data = bridge_get("product_reviews")
    if data.get("success"):
        rows = data.get("data", [])
        if not rows:
            return {"answer": "No product reviews found.", "source": "php_bridge"}

        lines = []
        for r in rows:
            lines.append(
                f"- Rating: {r.get('rating', 'N/A')} | Customer: {r.get('customer_name', 'Unknown')} | "
                f"Review: {r.get('review', '')}"
            )

        return {
            "answer": "Recent product reviews:\n" + "\n".join(lines),
            "source": "php_bridge"
        }

    return {"answer": "Unable to fetch reviews right now.", "source": "php_bridge"}


def answer_knowledge_base():
    data = bridge_get("knowledge_base")
    if data.get("success"):
        rows = data.get("data", [])
        if not rows:
            return {"answer": "No knowledge base records found.", "source": "php_bridge"}

        lines = []
        for r in rows:
            text = " | ".join([f"{k}: {v}" for k, v in r.items() if v is not None])
            lines.append(f"- {text}")

        return {
            "answer": "Knowledge base records:\n" + "\n".join(lines),
            "source": "php_bridge"
        }

    return {"answer": "Unable to fetch knowledge base records right now.", "source": "php_bridge"}


def answer_unknown():
    return {
        "answer": (
            "I can answer questions about Gigaquit Rhum, history, users, roles, products, low stock, "
            "orders, revenue, top-selling products, recent SAP purchases, SAP inventory, reviews, and knowledge base records."
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
        "products": answer_products,
        "low_stock": answer_low_stock,
        "orders_summary": answer_orders_summary,
        "recent_orders": answer_recent_orders,
        "top_products": answer_top_products,
        "recent_sap_purchases": answer_recent_sap_purchases,
        "sap_inventory": answer_sap_inventory,
        "product_reviews": answer_product_reviews,
        "knowledge_base": answer_knowledge_base,
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
    return jsonify({
        "success": bool(data.get("success")),
        "message": "Bridge checked.",
        "bridge_response": data
    })


@app.route("/ask", methods=["POST"])
def ask():
    try:
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

    except Exception as e:
        return jsonify({
            "success": False,
            "answer": "An error occurred while processing the question.",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
