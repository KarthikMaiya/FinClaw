import os
import sys
import json
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from groq import Groq

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
BUDGET_FILE = os.path.join(BASE_DIR, "budget.json")
TRANSACTIONS_FILE = os.path.join(BASE_DIR, "transactions.json")
LAST_CHAT_ID_FILE = os.path.join(BASE_DIR, "last_chat_id.txt")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
BOT_TOKEN = os.getenv("BOT_TOKEN")

client = Groq(api_key=GROQ_API_KEY)


# -------------------------------------------------------------
# CORE DATA LAYER
# -------------------------------------------------------------

def load_budget():
    """Load current budget and currency."""
    if os.path.exists(BUDGET_FILE):
        try:
            with open(BUDGET_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"budget": 1000.0, "currency": "₹"}


def save_budget(amount, currency="₹"):
    """Update user budget."""
    os.makedirs(os.path.dirname(BUDGET_FILE), exist_ok=True)
    data = {"budget": float(amount), "currency": currency}
    with open(BUDGET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    return data


def load_transactions():
    """Load transaction records."""
    if os.path.exists(TRANSACTIONS_FILE):
        try:
            with open(TRANSACTIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_transaction(product, category, amount, status="COMPLETED"):
    """Save transaction record with timestamp and status."""
    os.makedirs(os.path.dirname(TRANSACTIONS_FILE), exist_ok=True)
    transactions = load_transactions()

    # Normalize numeric representation
    raw_clean = re.sub(r"[^\d.]", "", str(amount))
    try:
        numeric_amt = float(raw_clean) if raw_clean else 0.0
    except ValueError:
        numeric_amt = 0.0

    record = {
        "id": f"tx_{int(datetime.now().timestamp() * 1000)}",
        "product": product,
        "category": category,
        "amount": amount,
        "numeric_amount": numeric_amt,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status
    }
    transactions.append(record)

    with open(TRANSACTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(transactions, f, indent=4)

    return record


def clear_transactions():
    """Reset transactions."""
    if os.path.exists(TRANSACTIONS_FILE):
        with open(TRANSACTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4)
    return True


# -------------------------------------------------------------
# ANALYTICS & REASONING ENGINE
# -------------------------------------------------------------

def get_financial_health():
    """Calculate deep spending metrics: burn rate, velocity, remaining funds."""
    b_data = load_budget()
    budget = float(b_data.get("budget", 1000.0))
    currency = b_data.get("currency", "₹")

    txs = load_transactions()
    total_spent = sum(t.get("numeric_amount", 0.0) for t in txs if t.get("status") != "CANCELLED")
    remaining = budget - total_spent
    spent_pct = (total_spent / budget * 100.0) if budget > 0 else 0.0

    # Category breakdown & weekly count
    categories = {}
    weekly_count = 0
    now = datetime.now()
    seven_days_ago = now - timedelta(days=7)

    for t in txs:
        cat = t.get("category", "Others")
        amt = t.get("numeric_amount", 0.0)
        categories[cat] = categories.get(cat, 0.0) + amt

        t_time_str = t.get("timestamp")
        if t_time_str:
            try:
                t_time = datetime.strptime(t_time_str, "%Y-%m-%d %H:%M:%S")
                if t_time >= seven_days_ago:
                    weekly_count += 1
            except Exception:
                pass

    return {
        "budget": budget,
        "currency": currency,
        "total_spent": total_spent,
        "remaining": remaining,
        "spent_pct": spent_pct,
        "categories": categories,
        "transaction_count": len(txs),
        "weekly_velocity": weekly_count,
        "recent": txs[-5:]
    }


def evaluate_purchase_impact(product, amount, category="Shopping"):
    """
    Agentic risk and trade-off evaluation for a prospective purchase.
    """
    health = get_financial_health()
    curr = health["currency"]
    remaining = health["remaining"]
    budget = health["budget"]

    raw_clean = re.sub(r"[^\d.]", "", str(amount))
    try:
        amt = float(raw_clean) if raw_clean else 0.0
    except ValueError:
        amt = 0.0

    new_remaining = remaining - amt
    impact_pct = (amt / budget * 100.0) if budget > 0 else 0.0

    # Determine risk level
    if amt > remaining or new_remaining < 0:
        risk = "CRITICAL"
        verdict = f"Over budget! This purchase exceeds your remaining {curr}{remaining:,.2f} by {curr}{abs(new_remaining):,.2f}."
    elif amt > (remaining * 0.45):
        risk = "HIGH"
        verdict = f"High financial strain. This single purchase absorbs {impact_pct:.1f}% of your total budget."
    elif amt > (remaining * 0.20):
        risk = "MEDIUM"
        verdict = f"Moderate impact. Leaves {curr}{new_remaining:,.2f} for remaining expenses."
    else:
        risk = "LOW"
        verdict = f"Safe purchase within limits. Remaining buffer: {curr}{new_remaining:,.2f}."

    return {
        "product": product,
        "amount": amt,
        "category": category,
        "currency": curr,
        "risk_level": risk,
        "current_remaining": remaining,
        "new_remaining": new_remaining,
        "impact_percentage": impact_pct,
        "verdict": verdict
    }


# -------------------------------------------------------------
# AGENT TOOL DEFINITIONS (OpenAI Function Calling Schema)
# -------------------------------------------------------------

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_budget_status",
            "description": "Get current financial status, including budget, total spent, remaining balance, and recent category breakdown.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_expense",
            "description": "Log an already completed purchase or expense into transaction memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product": {"type": "string", "description": "Name of the item or service purchased."},
                    "amount": {"type": "number", "description": "Numeric purchase price."},
                    "category": {
                        "type": "string",
                        "enum": ["Food", "Shopping", "Electronics", "Daily Utility", "Others"],
                        "description": "Categorization of the purchase."
                    }
                },
                "required": ["product", "amount", "category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_budget",
            "description": "Set or update the user's monthly spending budget limit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "The new budget limit amount."}
                },
                "required": ["amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_purchase",
            "description": "Evaluate the financial impact, affordability, and risk of a prospective purchase before the user buys it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product": {"type": "string", "description": "The item or service considered for purchase."},
                    "amount": {"type": "number", "description": "Estimated or tagged price."},
                    "category": {"type": "string", "enum": ["Food", "Shopping", "Electronics", "Daily Utility", "Others"]}
                },
                "required": ["product", "amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reset_financial_data",
            "description": "Clear all recorded expenses and reset remaining balance back to full budget.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]


# -------------------------------------------------------------
# TOOL EXECUTOR
# -------------------------------------------------------------

def execute_tool(tool_name, arguments):
    """Execute the tool function determined by the Agent."""
    try:
        args = json.loads(arguments) if isinstance(arguments, str) else arguments
    except Exception:
        args = {}

    if tool_name == "get_budget_status":
        return get_financial_health()

    elif tool_name == "log_expense":
        product = args.get("product", "Item")
        amount = args.get("amount", 0.0)
        category = args.get("category", "Others")
        curr = load_budget().get("currency", "₹")
        record = save_transaction(product, category, f"{curr}{amount}")
        health = get_financial_health()
        return {
            "status": "success",
            "logged": record,
            "new_remaining_balance": health["remaining"],
            "currency": health["currency"]
        }

    elif tool_name == "set_budget":
        amount = args.get("amount", 1000.0)
        updated = save_budget(amount)
        health = get_financial_health()
        return {
            "status": "success",
            "new_budget": updated["budget"],
            "remaining_balance": health["remaining"]
        }

    elif tool_name == "evaluate_purchase":
        product = args.get("product", "Item")
        amount = args.get("amount", 0.0)
        category = args.get("category", "Shopping")
        return evaluate_purchase_impact(product, amount, category)

    elif tool_name == "reset_financial_data":
        clear_transactions()
        health = get_financial_health()
        return {
            "status": "success",
            "message": "All transactions wiped. Fresh budget active.",
            "budget": health["budget"],
            "remaining": health["remaining"]
        }

    return {"error": f"Unknown tool: {tool_name}"}


# -------------------------------------------------------------
# AUTONOMOUS AGENT RUNNER (ReAct Loop)
# -------------------------------------------------------------

AGENT_SYSTEM_PROMPT = """
You are FinClaw 🦞, an autonomous AI Financial Guardian.
You do not just give passive answers — you have direct access to financial tools and memory.

Your mission:
1. Actively protect the user from impulse spending and budget deficits.
2. When the user reports an expense, log it using the `log_expense` tool.
3. When the user asks about their balance, spending, or financial situation, inspect it using `get_budget_status`.
4. When the user considers buying an item (e.g. 'Should I buy X for Y?'), evaluate it using `evaluate_purchase` and provide clear, empathetic, pragmatic feedback with trade-offs.
5. When the user requests a budget change or reset, use `set_budget` or `reset_financial_data`.

Communication Style:
- Warm, concise, conversational, and direct (tailored for Telegram).
- Always include numbers and clear visual indicators when reporting balances.
- Discourage unnecessary debt and impulse spending constructively.
"""


def run_agentic_flow(user_message, conversation_history=None):
    """
    Full Autonomous ReAct execution loop:
    1. Sends message + tool definitions to LLM.
    2. If LLM requests tool execution, executes tool and provides tool response.
    3. LLM synthesizes final answer.
    """
    messages = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]

    if conversation_history:
        messages.extend(conversation_history)

    messages.append({"role": "user", "content": user_message})

    # Step 1: Initial invocation with tools
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            tools=AGENT_TOOLS,
            tool_choice="auto",
            temperature=0.3
        )

        response_msg = response.choices[0].message

        # Check if the model chose to invoke tools
        if response_msg.tool_calls:
            messages.append(response_msg)

            for tool_call in response_msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = tool_call.function.arguments
                print(f"🤖 [Agent Decision] Calling tool: {fn_name}({fn_args})", flush=True)

                tool_result = execute_tool(fn_name, fn_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })

            # Step 2: Final synthesis after tool execution
            second_response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.6,
                max_tokens=400
            )
            return second_response.choices[0].message.content.strip()

        # If no tool was needed, return direct response
        return response_msg.content.strip()

    except Exception as e:
        print(f"⚠ Agent execution error: {e}", flush=True)
        return f"FinClaw encountered a brief reasoning hitch: {e}"
