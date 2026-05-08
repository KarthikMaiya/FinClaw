from memory import AgentMemory
from tools.groq_tool import generate_warning
from tools.telegram_tool import send_telegram_message

memory = AgentMemory()

class FinanceGuardianAgent:

    def process_transaction(
        self,
        app_name,
        amount
    ):

        print("\n--- OpenClaw Agent Activated ---")

        memory.update(amount)

        summary = memory.get_summary()

        risk = self.evaluate_risk(amount)

        prompt = f"""
        User is about to spend {amount} on {app_name}.

        Total spending today:
        ₹{summary['total_spending']}

        Food orders today:
        {summary['food_orders']}

        Risk Level:
        {risk}

        Generate a short financial warning.
        """

        warning = generate_warning(prompt)

        print(f"Risk Level: {risk}")
        print(f"AI Warning: {warning}")

        send_telegram_message(warning)

    def evaluate_risk(self, amount):

        numeric_amount = int(
            amount.replace("₹", "")
        )

        if numeric_amount > 700:
            return "HIGH"

        elif numeric_amount > 300:
            return "MEDIUM"

        return "LOW"