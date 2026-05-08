from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

# This script lives in: <repo>/backend/tools/
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "README.md"

EXCLUDE_DIR_PREFIXES = {".git"}


def iter_repo_files(root: Path):
    for path in root.rglob("*"):
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue

        parts = rel.parts
        if parts and parts[0] in EXCLUDE_DIR_PREFIXES:
            continue

        if path.is_file():
            yield rel.as_posix()


files = sorted(iter_repo_files(ROOT))
created_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")

header = """# FinClaw AI

FinClaw is a mobile-first **financial guardian** concept: it monitors pending checkout spends, estimates risk against your budget, and triggers short “pause and reconsider” interventions.

This workspace contains:

- **FinClaw Android app** (Gradle/Kotlin): [FinClaw/](FinClaw/)
- **Python backend (Flask)** that generates AI warnings and stores categorized transactions: [backend/](backend/)
- A full copy of the upstream **OpenClaw** TypeScript gateway repo under [backend/openclaw/](backend/openclaw/) (not currently wired into the Python backend flow; it’s included as a reference/codebase).

## Features (from the screenshots)

- **Dashboard:** budget, spent, available funds, and “% of budget used”.
- **Risk level indicator:** gauge-style risk percentage with labels like “Safe” / “Caution”.
- **Adjust budget / add salary:** input + “Update Budget”.
- **Pending payment confirmation:** a “Pending Payment” card prompting “Did you complete this transaction?” with **YES, PAID** / **NO, SKIP**.
- **Impulse detected intervention:** a modal (“IMPULSE DETECTED”) showing the flagged amount and an auto-dismiss countdown.
- **Checkout-page warning delivery:** a short, notification-style message shown over an active checkout flow.

## Architecture (current)

### Python backend (prototype guardian)

- HTTP endpoint: `POST /payment-alert` in [backend/server.py](backend/server.py)
- Core agent logic: [backend/openclaw_agent.py](backend/openclaw_agent.py)
- LLM call (Groq): [backend/tools/groq_tool.py](backend/tools/groq_tool.py)
- Transaction persistence: [backend/memory.py](backend/memory.py) (writes `transactions.json` in the backend working directory)

### Android app

- Android project root: [FinClaw/](FinClaw/)

### Upstream OpenClaw (vendored)

- Upstream docs entry: [backend/openclaw/README.md](backend/openclaw/README.md)

## Quickstart (local dev)

### 1) Backend (Python)

From the `backend/` folder:

- Install deps (example): `pip install flask python-dotenv groq`
- Create env vars in `.env` (either repo root `.env` or `backend/.env` depending on how you run):
  - `GROQ_API_KEY`
  - (optional) `BOT_TOKEN`, `CHAT_ID` if using Telegram
- Run the server: `python server.py`

Then POST a sample transaction:

```bash
curl -X POST http://localhost:5000/payment-alert \
    -H "Content-Type: application/json" \
    -d '{"app":"Zomato","amount":"₹3750","product":"Paneer Biryani"}'
```

### 2) Android app

- Open [FinClaw/](FinClaw/) in Android Studio
- Or from a terminal:

```bash
cd FinClaw
./gradlew assembleDebug
```

## Notes

- The repository contains files with **hardcoded tokens** in test scripts. Treat anything committed here as potentially public and prefer `.env`-based secrets.

## Full file index

The section below lists every file in this workspace (excluding the `.git/` directory).

<details>
""" + f"<summary><strong>All files (generated)</strong> — {len(files)} files</summary>\n\n```text\n"

footer = """
```

</details>

---

Generated: """ + created_utc + """ (UTC)
"""

OUT.write_text(header + "\n".join(files) + footer, encoding="utf-8")
print(f"Wrote {OUT} with {len(files)} file paths")
