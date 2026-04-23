from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/", methods=["GET"])
def root():
    return jsonify({"success": True, "message": "RAG service is live"})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"success": True, "message": "Health route is working"})

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    return jsonify({
        "success": True,
        "answer": f"You asked: {question}"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
