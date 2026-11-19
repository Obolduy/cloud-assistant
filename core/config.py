import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

PG_DSN = os.environ.get("PG_DSN", "postgresql://hosting:hosting@127.0.0.1:5436/hosting")

STAND_PORT = int(os.environ.get("STAND_PORT", "8100"))
STAND_URL = f"http://127.0.0.1:{STAND_PORT}"
ISSUER_URL = STAND_URL
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8000"))
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"

RESOURCES = {
    "account": f"{STAND_URL}/account",
    "billing": f"{STAND_URL}/billing",
    "kb": f"{STAND_URL}/kb",
}

TOKEN_TTL_SEC = int(os.environ.get("TOKEN_TTL_SEC", "3600"))
DAILY_PLAN_CHANGE_LIMIT = 3

EMBED_URL = os.environ.get("EMBED_URL", "http://127.0.0.1:1234/v1/embeddings")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-nomic-embed-text-v1.5")
EMBED_QUERY_PREFIX = os.environ.get("EMBED_QUERY_PREFIX", "search_query: ")
EMBED_DOC_PREFIX = os.environ.get("EMBED_DOC_PREFIX", "search_document: ")

MODEL_NAME = ""
MODEL = None


def setup_model():
    global MODEL, MODEL_NAME
    base_url = os.environ.get("LLM_BASE_URL")
    MODEL_NAME = os.environ.get("LLM_MODEL", "")
    if not base_url or not MODEL_NAME:
        raise SystemExit("Нет LLM_BASE_URL или LLM_MODEL: скопируйте .env.example в .env")

    import httpx
    from agents import OpenAIChatCompletionsModel, set_tracing_disabled
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        base_url=base_url,
        api_key=os.environ.get("LLM_API_KEY", "none"),
        http_client=httpx.AsyncClient(trust_env=False, timeout=180),
    )
    set_tracing_disabled(True)
    MODEL = OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client)
    return MODEL
