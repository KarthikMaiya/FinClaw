from tools.groq_tool import generate_warning
from tools.telegram_tool import send_telegram_message
from memory import save_transaction


class OpenClawFinanceAgent:

    def process_transaction(
        self,
        app_name,
        amount,
        product
    ):

        print("\n🦞 OPENCLAW AI REASONING")
        print("━━━━━━━━━━━━━━━━━━━━━━")

        print(f"📱 App: {app_name}")
        print(f"💰 Amount: {amount}")
        print(f"🛒 Product: {product}")

        category = self.categorize_product(
            product
        )

        print(f"📂 Category: {category}")

        # Save categorized transaction
        save_transaction(
            product,
            category,
            amount
        )

        print("✅ TRANSACTION SAVED")

        risk = self.evaluate_risk(amount)

        print(f"⚠ Risk Level: {risk}")

        prompt = f"""
You are an emotionally intelligent financial guardian AI.

The user is on a checkout/payment page.

Product:
{product}

Category:
{category}

Amount:
{amount}

Risk Level:
{risk}

Generate:
- a SHORT emotional intervention
- maximum 2 lines
- emotionally persuasive
- natural human tone
"""

        warning = generate_warning(prompt)

        print(f"🤖 AI Warning: {warning}")

        telegram_message = (
            "🦞 Finance Guardian Alert\n"
            f"App: {app_name}\n"
            f"Product: {product}\n"
            f"Amount: {amount}\n"
            f"Category: {category}\n"
            f"Risk: {risk}\n\n"
            f"{warning}"
        )

        if send_telegram_message(telegram_message):

            print("📨 Telegram alert sent")

        print("━━━━━━━━━━━━━━━━━━━━━━")

        return warning, category

    # ─── Categorization ───────────────────────────────────────────────

    def categorize_product(
        self,
        product
    ):

        product = product.lower()

        # Food
        if any(word in product for word in [

            "burger",
            "pizza",
            "biryani",
            "meal",
            "combo",
            "fries",
            "chicken",
            "paneer",
            "coffee",
            "tea",
            "juice",
            "coke",
            "pepsi"

        ]):

            return "Food"

        # Electronics
        elif any(word in product for word in [

            "iphone",
            "laptop",
            "macbook",
            "camera",
            "tv",
            "airpods",
            "headphones"

        ]):

            return "Electronics"

        # Utilities
        elif any(word in product for word in [

            "soap",
            "milk",
            "rice",
            "detergent",
            "oil",
            "toothpaste"

        ]):

            return "Daily Utility"

        # Shopping
        elif any(word in product for word in [

            "shoes",
            "watch",
            "shirt",
            "jeans",
            "hoodie",
            "bag"

        ]):

            return "Shopping"

        return "Others"

    # ─── Risk Engine ─────────────────────────────────────────────────

    def evaluate_risk(
        self,
        amount
    ):

        numeric_amount = int(
            amount
            .replace("₹", "")
            .replace(",", "")
            .strip()
        )

        if numeric_amount > 10000:

            return "HIGH"

        elif numeric_amount > 3000:

            return "MEDIUM"

        return "LOW"