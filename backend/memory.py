import json
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSACTION_FILE = os.path.join(BASE_DIR, "transactions.json")


def load_transactions():

    if not os.path.exists(TRANSACTION_FILE):

        return []

    with open(
        TRANSACTION_FILE,
        "r"
    ) as file:

        return json.load(file)


def save_transaction(
    product,
    category,
    amount
):

    transactions = load_transactions()

    transaction = {

        "product": product,
        "category": category,
        "amount": amount
    }

    transactions.append(transaction)

    with open(
        TRANSACTION_FILE,
        "w"
    ) as file:

        json.dump(
            transactions,
            file,
            indent=4
        )

    print("✅ TRANSACTION SAVED")


def clear_transactions():
    """Clear all recorded transactions."""
    if os.path.exists(TRANSACTION_FILE):
        with open(TRANSACTION_FILE, "w") as file:
            json.dump([], file, indent=4)
    print("🗑 TRANSACTIONS CLEARED")