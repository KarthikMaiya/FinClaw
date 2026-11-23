import os
import sys
import time
import json
import re
import requests
from dotenv import load_dotenv
from groq import Groq

# Add backend to path so agent_core can be imported
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# -------------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES & CONFIG
# -------------------------------------------------------------

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEFAULT_CHAT_ID = os.getenv("CHAT_ID")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing from .env file!")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY is missing from .env file!")

# -------------------------------------------------------------
# PATHS & CLIENT
# -------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LAST_CHAT_ID_FILE = os.path.join(BASE_DIR, "backend", "last_chat_id.txt")
BUDGET_FILE = os.path.join(BASE_DIR, "backend", "budget.json")
TRANSACTIONS_PATHS = [
    os.path.join(BASE_DIR, "backend", "transactions.json"),
    os.path.join(BASE_DIR, "transactions.json")
]

client = Groq(api_key=GROQ_API_KEY)
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# FinClaw System Persona
SYSTEM_PROMPT = """
You are FinClaw 🦞, a smart, emotionally intelligent personal financial guardian AI.
Your mission is to help users maintain financial discipline, avoid impulsive spending,
and make wise budgeting decisions.

Guidelines:
- Keep responses concise, practical, and conversational (well-suited for Telegram).
- Use friendly, encouraging formatting with emojis where appropriate.
- If the user asks whether they should purchase an item, evaluate the necessity, emotional impulse, and financial impact against their budget.
- If asked about general money management, give crisp, actionable advice.
"""


# -------------------------------------------------------------
# BUDGET & TRANSACTION STORAGE HELPERS
# -------------------------------------------------------------

def get_transactions_file():
    """Get the preferred absolute path for transactions.json."""
    return TRANSACTIONS_PATHS[0]


def record_active_chat_id(chat_id):
    """Save the most recent chat_id so backend alerts know who to message."""
    try:
        os.makedirs(os.path.dirname(LAST_CHAT_ID_FILE), exist_ok=True)
        with open(LAST_CHAT_ID_FILE, "w", encoding="utf-8") as f:
            f.write(str(chat_id))
    except Exception:
        pass


def load_budget():
    """Load budget configuration from backend/budget.json."""
    if os.path.exists(BUDGET_FILE):
        try:
            with open(BUDGET_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"budget": 1000.0, "currency": "₹"}


def save_budget(amount, currency="₹"):
    """Save updated budget to backend/budget.json."""
    os.makedirs(os.path.dirname(BUDGET_FILE), exist_ok=True)
    data = {"budget": float(amount), "currency": currency}
    with open(BUDGET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"🎯 Budget set to {currency}{amount:,.2f}", flush=True)
    return data


def load_transactions():
    """Load recorded transactions from file if present."""
    for path in TRANSACTIONS_PATHS:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return []


def save_transaction(product, category, amount):
    """Save a single transaction to backend/transactions.json."""
    target_path = get_transactions_file()
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    transactions = load_transactions()

    transaction = {
        "product": product,
        "category": category,
        "amount": amount
    }
    transactions.append(transaction)

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(transactions, f, indent=4)

    print(f"✅ Saved transaction: {product} ({amount}) [{category}]", flush=True)
    return transaction


def clear_transactions():
    """Wipe all recorded transactions."""
    for path in TRANSACTIONS_PATHS:
        if os.path.exists(path):
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=4)
            except Exception:
                pass
    print("🗑 Cleared all transactions.", flush=True)


def calculate_budget_summary():
    """Calculate total spent and remaining balance against budget."""
    budget_data = load_budget()
    total_budget = budget_data.get("budget", 1000.0)
    currency = budget_data.get("currency", "₹")

    transactions = load_transactions()
    total_spent = 0.0
    category_breakdown = {}

    for t in transactions:
        raw_amt = str(t.get("amount", "0")).strip()
        cat = t.get("category", "Others")
        clean_num = re.sub(r"[^\d.]", "", raw_amt)
        try:
            num = float(clean_num) if clean_num else 0.0
        except ValueError:
            num = 0.0

        total_spent += num
        category_breakdown[cat] = category_breakdown.get(cat, 0.0) + num

    remaining = total_budget - total_spent
    spent_pct = (total_spent / total_budget * 100) if total_budget > 0 else 0.0

    return {
        "budget": total_budget,
        "currency": currency,
        "total_spent": total_spent,
        "remaining": remaining,
        "spent_pct": spent_pct,
        "transactions_count": len(transactions),
        "category_breakdown": category_breakdown,
        "recent_transactions": transactions[-5:]
    }


def generate_progress_bar(percentage, length=10):
    """Generate a visual text progress bar."""
    pct = max(0.0, min(100.0, percentage))
    filled = int(round(length * pct / 100.0))
    return "█" * filled + "░" * (length - filled)


# -------------------------------------------------------------
# TELEGRAM HELPER FUNCTIONS
# -------------------------------------------------------------

def send_chat_action(chat_id, action="typing"):
    """Send typing action to Telegram."""
    try:
        requests.post(
            f"{TELEGRAM_API}/sendChatAction",
            json={"chat_id": chat_id, "action": action},
            timeout=5
        )
    except Exception:
        pass


def send_telegram_message(chat_id, text):
    """Send text message to a specific Telegram chat_id."""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        # If Markdown parsing fails due to special characters, fallback to plain text
        if response.status_code == 400 and "can't parse entities" in response.text:
            payload.pop("parse_mode", None)
            response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"⚠ Error sending Telegram message: {e}", flush=True)
        return None


# -------------------------------------------------------------
# AI GENERATION & INTENT EXTRACTION
# -------------------------------------------------------------

def ask_groq(user_message, chat_history=None):
    """Generate intelligent response using Groq LLM."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if chat_history:
        messages.extend(chat_history)

    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=350,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠ Groq generation error: {e}", flush=True)
        return f"Sorry, I encountered an issue while thinking: {e}"


def extract_amount_from_text(text):
    """Regex helper to extract amount with currency from text."""
    match = re.search(r'([₹$€£]\s*[\d,]+(?:\.\d{1,2})?)|([\d,]+(?:\.\d{1,2})?\s*(?:dollars?|rupees?|rs|inr|usd))', text, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    num_match = re.search(r'\b\d+(?:\.\d{1,2})?\b', text)
    if num_match:
        return num_match.group(0).strip()
    return None


def check_and_extract_expense(text):
    """
    Check if the user message describes a completed purchase/expense.
    If yes, extract product, amount, and category via Groq JSON.
    """
    lower = text.lower()
    keywords = ["bought", "purchased", "spent", "paid", "ordered", "got a new", "billed", "charged"]
    if not any(kw in lower for kw in keywords):
        return None

    extracted_amount = extract_amount_from_text(text)

    prompt = f"""You are a financial parsing assistant.
Analyze this user statement: "{text}"

Determine if the user is stating that they already purchased, bought, spent money on, or paid for an item/service.
If YES:
- is_expense: true
- product: short name of the item or service (e.g. "Watch", "Chicken Burger", "Shoes")
- amount: formatted amount including currency symbol if present (e.g. "$30", "₹450", "25")
- category: one of ["Food", "Shopping", "Electronics", "Daily Utility", "Others"]

If NO (for example, if they are asking whether to buy something, asking for advice, or speaking hypothetically):
- is_expense: false

Respond ONLY with valid JSON."""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        data = json.loads(response.choices[0].message.content)
        if data.get("is_expense"):
            amount = data.get("amount") or extracted_amount or "₹0"
            return {
                "product": data.get("product", "Item"),
                "amount": str(amount),
                "category": data.get("category", "Others")
            }
    except Exception as e:
        print(f"⚠ Expense extraction error: {e}", flush=True)

    return None


# -------------------------------------------------------------
# COMMAND & MESSAGE HANDLERS
# -------------------------------------------------------------

def handle_command(command_text, chat_id, user_first_name=""):
    """Handle standard slash commands."""
    parts = command_text.strip().split()
    cmd = parts[0].lower()

    if cmd in ["/start", "/help"]:
        greeting = f"Hi {user_first_name}! " if user_first_name else "Hi! "
        budget_info = load_budget()
        b_curr = budget_info.get("currency", "₹")
        b_amt = budget_info.get("budget", 1000.0)

        return (
            f"🦞 *FinClaw AI Guardian*\n\n"
            f"{greeting}I'm your real-time financial spending guardian.\n\n"
            f"🎯 *Current Budget:* {b_curr}{b_amt:,.2f}\n\n"
            f"Here is how I can help you:\n"
            f"• 📝 *Log Purchases Automatically*: Just tell me what you bought!\n"
            f"  _Example:_ `I purchased a watch for $30` or `Bought biryani for ₹250`\n"
            f"• 📊 */balance*: View your remaining budget and spending breakdown.\n"
            f"• 🎯 */budget <amount>*: Set or change your budget (e.g. `/budget 1000`).\n"
            f"• 🛑 *Impulse Check*: Ask me before you spend!\n"
            f"  _Example:_ `Thinking of buying ₹900 shoes on impulse, should I?`\n"
            f"• ➕ */add <amount> <product>*: Quick manual log (e.g. `/add 250 Food Biryani`).\n"
            f"• 🗑 */reset* or */clear*: Reset recorded spending to ₹0.\n"
            f"• ℹ */help*: Show this guide again.\n\n"
            f"Go ahead and test me!"
        )

    elif cmd in ["/budget", "/setbudget"]:
        if len(parts) > 1:
            raw_val = re.sub(r"[^\d.]", "", parts[1])
            try:
                new_budget = float(raw_val)
                save_budget(new_budget)
                summary = calculate_budget_summary()
                return (
                    f"🎯 *Budget Updated Successfully!*\n\n"
                    f"• *New Budget:* ₹{new_budget:,.2f}\n"
                    f"• *Total Spent:* ₹{summary['total_spent']:,.2f}\n"
                    f"• *Remaining Balance:* ₹{summary['remaining']:,.2f}\n\n"
                    f"📊 Check `/balance` anytime to see your spending progress."
                )
            except ValueError:
                return "⚠ Please enter a valid number, e.g. `/budget 1000` or `/budget 2500`."
        else:
            summary = calculate_budget_summary()
            return (
                f"🎯 *Current Budget Details*\n\n"
                f"• *Total Budget:* ₹{summary['budget']:,.2f}\n"
                f"• *Total Spent:* ₹{summary['total_spent']:,.2f}\n"
                f"• *Remaining Balance:* ₹{summary['remaining']:,.2f}\n\n"
                f"💡 *Tip:* To update your budget, type `/budget <amount>` (e.g. `/budget 1500`)."
            )

    elif cmd in ["/reset", "/clear"]:
        clear_transactions()
        budget_info = load_budget()
        curr = budget_info.get("currency", "₹")
        amt = budget_info.get("budget", 1000.0)
        return (
            f"🗑 *Budget & Expenses Reset!*\n\n"
            f"• *Target Budget:* {curr}{amt:,.2f}\n"
            f"• *Total Spent:* {curr}0.00\n"
            f"• *Remaining Balance:* {curr}{amt:,.2f}\n\n"
            f"✨ You have a clean slate! Log new expenses anytime."
        )

    elif cmd in ["/add", "/spend"]:
        # Format: /add <amount> [category] <product>
        if len(parts) < 3:
            return "💡 Usage: `/add <amount> <product>` (e.g. `/add 250 Biryani` or `/add $30 Watch`)"

        amount_arg = parts[1]
        remaining = parts[2:]

        valid_cats = ["food", "shopping", "electronics", "daily utility", "utility", "others"]
        if remaining[0].lower() in valid_cats:
            cat = remaining[0].capitalize()
            prod = " ".join(remaining[1:])
        else:
            cat = "Shopping" if any(w in " ".join(remaining).lower() for w in ["watch", "shoes", "shirt"]) else "Food" if any(w in " ".join(remaining).lower() for w in ["pizza", "burger", "food"]) else "Others"
            prod = " ".join(remaining)

        save_transaction(prod, cat, amount_arg)
        summary = calculate_budget_summary()

        return (
            f"✅ *Expense Logged!*\n\n"
            f"🛒 *Item:* {prod}\n"
            f"💰 *Amount:* {amount_arg}\n"
            f"📂 *Category:* {cat}\n\n"
            f"💵 *Remaining Balance:* ₹{summary['remaining']:,.2f} / ₹{summary['budget']:,.2f}\n"
            f"📊 Use `/balance` to view full summary."
        )

    elif cmd in ["/balance", "/summary", "/transactions"]:
        summary = calculate_budget_summary()
        curr = summary["currency"]
        budget_amt = summary["budget"]
        total_spent = summary["total_spent"]
        remaining = summary["remaining"]
        spent_pct = summary["spent_pct"]
        bar = generate_progress_bar(spent_pct)

        lines = [
            f"📊 *Financial Guardian Balance*\n",
            f"🎯 *Total Budget:* {curr}{budget_amt:,.2f}",
            f"💸 *Total Spent:* {curr}{total_spent:,.2f} ({spent_pct:.1f}%)"
        ]

        if remaining >= 0:
            lines.append(f"💵 *Remaining Balance:* {curr}{remaining:,.2f}")
            lines.append(f"`[{bar}]` {spent_pct:.1f}% used\n")
        else:
            lines.append(f"🚨 *Over Budget by:* {curr}{abs(remaining):,.2f}!")
            lines.append(f"`[{bar}]` {spent_pct:.1f}% used ⚠\n")

        if summary["transactions_count"] == 0:
            lines.append("✨ *No expenses recorded yet!*")
            lines.append("💡 *Tip:* Tell me what you bought (e.g. _'I purchased shoes for ₹400'_) to log an expense.")
            return "\n".join(lines)

        lines.append("*By Category:*")
        for cat, amt in summary["category_breakdown"].items():
            lines.append(f"• *{cat}:* {curr}{amt:,.2f}")

        lines.append("\n*Recent Transactions:*")
        for t in summary["recent_transactions"]:
            lines.append(f"• {t.get('product', 'Item')} — *{t.get('amount', '')}* ({t.get('category', 'Others')})")

        return "\n".join(lines)

    return None


def process_user_message(text, chat_id, user_first_name=""):
    """Process incoming message and return the reply."""
    # 1. Slash commands get fast deterministic handling (no LLM round-trip)
    if text.startswith("/"):
        command_reply = handle_command(text, chat_id, user_first_name)
        if command_reply:
            return command_reply

    # 2. Everything else goes through the autonomous Agentic ReAct loop.
    #    The agent autonomously decides whether to:
    #      - log_expense (if user is reporting a purchase)
    #      - evaluate_purchase (if user is asking "should I buy…")
    #      - get_budget_status (if user asks about balance/budget)
    #      - set_budget / reset_financial_data (if user wants changes)
    #      - or just answer conversationally (general finance advice)
    try:
        from agent_core import run_agentic_flow
        reply = run_agentic_flow(text)
        return reply
    except Exception as e:
        print(f"⚠ Agentic flow error, falling back to basic Groq: {e}", flush=True)
        return ask_groq(text)



# -------------------------------------------------------------
# BOT POLLING LOOP
# -------------------------------------------------------------

def start_bot():
    """Continuously poll Telegram for updates and reply to user messages."""
    budget_data = load_budget()
    print("=" * 55, flush=True)
    print("🦞 FinClaw Telegram Bot is ACTIVE and listening...", flush=True)
    print(f"🤖 Groq Model: {GROQ_MODEL}", flush=True)
    print(f"🎯 Current Budget: {budget_data.get('currency', '₹')}{budget_data.get('budget', 1000.0):,.2f}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    print("=" * 55, flush=True)

    offset = None

    while True:
        try:
            params = {"timeout": 25}
            if offset is not None:
                params["offset"] = offset

            response = requests.get(
                f"{TELEGRAM_API}/getUpdates",
                params=params,
                timeout=30
            )

            if response.status_code != 200:
                print(f"⚠ Telegram API getUpdates status {response.status_code}: {response.text}", flush=True)
                time.sleep(3)
                continue

            data = response.json()
            if not data.get("ok"):
                print(f"⚠ Telegram response not ok: {data}", flush=True)
                time.sleep(3)
                continue

            updates = data.get("result", [])

            for update in updates:
                offset = update["update_id"] + 1

                message = update.get("message")
                if not message:
                    continue

                chat = message.get("chat", {})
                chat_id = chat.get("id")
                from_user = message.get("from", {})
                first_name = from_user.get("first_name", "User")
                username = from_user.get("username", "")
                text = message.get("text", "").strip()

                if not text or not chat_id:
                    continue

                # Remember active user chat ID for future alerts
                record_active_chat_id(chat_id)

                user_identifier = f"@{username}" if username else first_name
                print(f"\n📩 Message from {user_identifier} (Chat ID {chat_id}): '{text}'", flush=True)

                # Show typing indicator
                send_chat_action(chat_id, "typing")

                # Process message and generate reply
                reply = process_user_message(text, chat_id, first_name)

                # Send reply back to the user
                send_telegram_message(chat_id, reply)
                preview = reply.replace('\n', ' ')[:70]
                print(f"📤 Sent reply to {user_identifier}: {preview}...", flush=True)

        except requests.exceptions.RequestException as e:
            print(f"⚠ Network error in polling loop: {e}. Retrying in 5s...", flush=True)
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n🛑 FinClaw Bot stopped by user.", flush=True)
            break
        except Exception as e:
            print(f"⚠ Unexpected error: {e}", flush=True)
            time.sleep(3)


# -------------------------------------------------------------
# MAIN ENTRYPOINT
# -------------------------------------------------------------

if __name__ == "__main__":
    start_bot()