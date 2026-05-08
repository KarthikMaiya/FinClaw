from flask import Flask, request, jsonify
from openclaw_agent import OpenClawFinanceAgent
import time

app = Flask(__name__)

# Duplicate prevention
last_amount = None
last_time = 0

# OpenClaw Agent
agent = OpenClawFinanceAgent()


@app.route("/")
def home():

    return "Finance Guardian Server Running"


@app.route("/payment-alert", methods=["POST"])
def payment_alert():

    global last_amount, last_time

    data = request.json

    app_name = data.get("app")

    amount = data.get("amount")

    product = data.get("product", "")

    print("\n🦞 OPENCLAW AGENT SESSION")
    print("🦞 Observing transaction")
    print(f"📱 App: {app_name}")
    print(f"💰 Amount: {amount}")
    print(f"🛒 Product: {product}")

    current_time = time.time()

    # Prevent duplicate spam
    if (
        amount == last_amount and
        current_time - last_time < 30
    ):

        print("⚠ Duplicate transaction ignored")

        return jsonify({
            "message": "Duplicate ignored"
        })

    # Update cooldown
    last_amount = amount
    last_time = current_time

    # OpenClaw AI Processing
    warning, category = agent.process_transaction(
        app_name,
        amount,
        product
    )

    return jsonify({
        "status": "success",
        "warning": warning,
        "category": category
    })


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )