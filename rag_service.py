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

    if "business summary" in q or "system summary" in q or "overall summary" in q:
        return "business_summary"
    if "cheapest" in q or "lowest price" in q or "highest stock" in q or "lowest stock product" in q or "most expensive" in q:
        return "product_stats"
    if "overview" in q or "database" in q or "tables" in q:
        return "database_overview"
    if "gigaquit rhum" in q or "what is this system" in q or "about system" in q:
        return "system_info"
    if "history" in q or "origin" in q or "heritage" in q:
        return "history_info"
    if "total users" in q or "how many users" in q or "registered users" in q:
        return "total_users"
    if "role" in q:
        return "role_counts"
    if "farmers" in q and "sap" not in q:
        return "farmers"
    if "producers" in q:
        return "producers"
    if "customers" in q:
        return "customers"
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
    if "reviews" in q or "ratings" in q:
        return "product_reviews"

    return "unknown"

def save_query(question, answer, user_id):
    try:
        requests.post(
            BRIDGE_URL + "?action=save_query",
            json={
                "question": question,
                "answer": answer,
                "user_id": user_id
            },
            timeout=5
        )
    except:
        pass

def get_history(user_id):
    try:
        res = requests.get(
            BRIDGE_URL,
            params={"action": "get_history", "user_id": user_id},
            timeout=5
        )
        return res.json().get("data", [])
    except:
        return []
        

def lines(title, rows, formatter, empty):
    if not rows:
        return {"answer": empty, "source": "php_bridge"}
    return {"answer": title + "\n" + "\n".join(formatter(r) for r in rows), "source": "php_bridge"}


def answer_system_info():
    return {
        "answer": (
            "Gigaquit Rhum is a databank and marketplace system for the local rhum industry of "
            "Gigaquit, Surigao del Norte. It connects farmers, producers, customers, and administrators. "
            "It supports SAP supply, products, orders, payments, reports, and AI-powered databank insights."
        ),
        "source": "knowledge_base"
    }


def answer_history_info():
    return {
        "answer": (
            "Gigaquit Rhum reflects the local craftsmanship, agricultural identity, and rhum-making culture "
            "of Gigaquit, Surigao del Norte. The system helps modernize the local industry using a digital "
            "marketplace and databank."
        ),
        "source": "knowledge_base"
    }


def answer_total_users():
    d = bridge_get("total_users")
    total = d.get("data", {}).get("total_users", 0)
    return {"answer": f"There are currently {total} registered users in the system.", "source": "php_bridge"}


def answer_role_counts():
    d = bridge_get("role_counts")
    return lines(
        "Current user role counts:",
        d.get("data", []),
        lambda r: f"- {str(r.get('role','Unknown')).replace('_',' ').title()}: {r.get('total',0)}",
        "No role data found."
    )


def answer_people(action, title):
    d = bridge_get(action)
    return lines(
        title,
        d.get("data", []),
        lambda r: f"- {r.get('full_name','Unknown')} ({r.get('email','No email')})",
        f"No {title.lower()} found."
    )


def answer_products():
    d = bridge_get("products")
    return lines(
        "Available products:",
        d.get("data", []),
        lambda r: f"- {r.get('name','Unnamed Product')} | Price: {money(r.get('price'))} | Stock: {r.get('stock',0)}",
        "No products found."
    )


def answer_product_stats():
    d = bridge_get("product_stats")
    x = d.get("data", {})
    c = x.get("cheapest") or {}
    e = x.get("most_expensive") or {}
    hs = x.get("highest_stock") or {}
    ls = x.get("lowest_stock") or {}

    return {
        "answer": (
            "Product analytics:\n"
            f"- Cheapest product: {c.get('name','N/A')} at {money(c.get('price'))}\n"
            f"- Most expensive product: {e.get('name','N/A')} at {money(e.get('price'))}\n"
            f"- Highest stock: {hs.get('name','N/A')} with {hs.get('stock',0)} units\n"
            f"- Lowest stock: {ls.get('name','N/A')} with {ls.get('stock',0)} units"
        ),
        "source": "php_bridge"
    }


def answer_low_stock():
    d = bridge_get("low_stock")
    return lines(
        "Low-stock products:",
        d.get("data", []),
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
    return lines(
        "Recent orders:",
        d.get("data", []),
        lambda r: f"- {r.get('order_number','Order')} | {r.get('customer_name','Unknown')} | {money(r.get('total_amount'))} | {r.get('status','N/A')} | {r.get('payment_status','N/A')}",
        "No recent orders found."
    )


def answer_top_products():
    d = bridge_get("top_products")
    return lines(
        "Top-selling products:",
        d.get("data", []),
        lambda r: f"- {r.get('name','Unnamed Product')} | Sold: {r.get('total_sold',0)} | Sales: {money(r.get('total_sales',0))}",
        "No top-selling product data found."
    )


def answer_recent_sap_purchases():
    d = bridge_get("recent_sap_purchases")
    return lines(
        "Recent SAP purchases:",
        d.get("data", []),
        lambda r: f"- Farmer: {r.get('farmer_name','Unknown')} | Producer: {r.get('producer_name','Unknown')} | Qty: {r.get('quantity',0)} L | Amount: {money(r.get('total_amount'))} | Date: {r.get('created_at','')}",
        "No recent SAP purchases found."
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
    return lines(
        "Recent product reviews:",
        d.get("data", []),
        lambda r: f"- Rating: {r.get('rating','N/A')} | Customer: {r.get('customer_name','Unknown')} | Review: {r.get('review','')}",
        "No product reviews found."
    )


def answer_business_summary():
    d = bridge_get("business_summary")
    x = d.get("data", {})
    return {
        "answer": (
            "Business summary:\n"
            f"- Registered users: {x.get('users',0)}\n"
            f"- Products: {x.get('products',0)}\n"
            f"- Orders: {x.get('orders',0)}\n"
            f"- Revenue: {money(x.get('revenue',0))}\n"
            f"- Low-stock products: {x.get('low_stock',0)}"
        ),
        "source": "php_bridge"
    }


def answer_database_overview():
    d = bridge_get("database_overview")
    data = d.get("data", {})
    if not data:
        return {"answer": "No database overview available.", "source": "php_bridge"}
    return {"answer": "Database overview:\n" + "\n".join([f"- {k}: {v} records" for k, v in data.items()]), "source": "php_bridge"}


def answer_unknown():
    return {
        "answer": (
            "I can answer business questions such as: show products, cheapest product, highest stock, "
            "low stock products, top selling products, total revenue, recent orders, SAP summary, "
            "recent SAP purchases, role counts, farmers, producers, customers, and business summary."
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
        "farmers": lambda: answer_people("farmers", "Farmers:"),
        "producers": lambda: answer_people("producers", "Producers:"),
        "customers": lambda: answer_people("customers", "Customers:"),
        "products": answer_products,
        "product_stats": answer_product_stats,
        "low_stock": answer_low_stock,
        "orders_summary": answer_orders_summary,
        "recent_orders": answer_recent_orders,
        "top_products": answer_top_products,
        "recent_sap_purchases": answer_recent_sap_purchases,
        "sap_summary": answer_sap_summary,
        "product_reviews": answer_reviews,
        "business_summary": answer_business_summary,
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
    user_id = data.get("user_id", 0)

    if not question:
        return jsonify({"success": False, "answer": "Question is required."}), 400

    result = generate_answer(question)

    # SAVE HISTORY 🔥
    save_query(question, result["answer"], user_id)

    return jsonify({
        "success": True,
        "question": question,
        "answer": result["answer"],
        "source": result["source"],
        "intent": result["intent"]
    })
