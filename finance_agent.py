from openai import OpenAI
import requests
import os
from dotenv import load_dotenv

# -----------------------------
# LOAD ENV VARIABLES
# -----------------------------

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# -----------------------------
# GROQ CLIENT
# -----------------------------

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# -----------------------------
# USER CONTEXT
# -----------------------------

amount = 899
weekly_food_spending = 3200

prompt = f"""
Generate a VERY SHORT financial warning.

Rules:
- Maximum 2 sentences
- Friendly tone
- Notification style

User is spending ₹{amount} on food.

Weekly food spending:
₹{weekly_food_spending}
"""

# -----------------------------
# GENERATE WARNING
# -----------------------------

response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ]
)

warning_message = response.choices[0].message.content

print("\nGenerated Warning:\n")
print(warning_message)

# -----------------------------
# SEND TO TELEGRAM
# -----------------------------

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

payload = {
    "chat_id": CHAT_ID,
    "text": warning_message
}

telegram_response = requests.post(url, json=payload)

print("\nTelegram Response:\n")
print(telegram_response.json())