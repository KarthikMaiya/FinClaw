import requests
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
LAST_CHAT_ID_FILE = os.path.join(os.path.dirname(__file__), "..", "last_chat_id.txt")

def get_target_chat_id(explicit_chat_id=None):
    if explicit_chat_id:
        return explicit_chat_id
    if os.path.exists(LAST_CHAT_ID_FILE):
        try:
            with open(LAST_CHAT_ID_FILE, "r", encoding="utf-8") as f:
                cid = f.read().strip()
                if cid:
                    return cid
        except Exception:
            pass
    # Avoid sending to bot's own ID which causes Telegram Bad Request
    if CHAT_ID and str(CHAT_ID) != "9086302698":
        return CHAT_ID
    return None

def send_telegram_message(message, chat_id=None):
    target_chat_id = get_target_chat_id(chat_id)
    if not BOT_TOKEN or not target_chat_id:
        print("⚠ Telegram is not configured or no valid recipient chat_id found; message was not sent")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": target_chat_id,
        "text": message
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return True
    except requests.RequestException as error:
        print(f"⚠ Telegram message failed: {error}")
        return False