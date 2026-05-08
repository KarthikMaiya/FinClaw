import json
import os


TRANSACTION_FILE = "transactions.json"


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