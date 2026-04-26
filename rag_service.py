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
        response = requests.get(
            BRIDGE_URL,
            params={"action": action},
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


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

    if "products" in q or "show products" in q or "available products" in q:
        return "product_info"

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
            "of Gigaquit, Surigao del Norte. The system modernizes local business operations through a "
            "digital databank and marketplace."
        ),
        "source": "knowledge_base"
    }


def answer_total_users():
    data = bridge_get("total_users")

    if data.get("success") and "data" in data:
        total = data["data"].get("total_users", 0)
        return {
            "answer": f"There are currently {total} registered users in the system.",
            "source": "php_bridge"
        }

    return {
        "answer": "Unable to fetch total users from the databank at the moment.",
        "source": "php_bridge"
    }


def answer_product_info():
    return {
        "answer": (
            "Product lookup is ready for bridge expansion. Currently, the assistant can answer system "
            "information and total users. Next, add a products action in db_bridge.php so I can show real "
            "product names, prices, and stock."
        ),
        "source": "assistant"
    }


def answer_unknown():
    return {
        "answer": (
            "I could not confidently match that question yet. You may ask about Gigaquit Rhum, its history, "
            "or how many users are registered in the system."
        ),
        "source": "assistant"
    }


def generate_answer(question):
    intent = detect_intent(question)

    if intent == "system_info":
        result = answer_system_info()
    elif intent == "history_info":
        result = answer_history_info()
    elif intent == "total_users":
        result = answer_total_users()
    elif intent == "product_info":
        result = answer_product_info()
    else:
        result = answer_unknown()

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
        "bridge": "not_checked"
    })


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
