import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

PG_DSN = os.environ.get("PG_DSN", "postgresql://hosting:hosting@127.0.0.1:5436/hosting")

STAND_PORT = int(os.environ.get("STAND_PORT", "8100"))
STAND_URL = f"http://127.0.0.1:{STAND_PORT}"

DAILY_PLAN_CHANGE_LIMIT = 3
