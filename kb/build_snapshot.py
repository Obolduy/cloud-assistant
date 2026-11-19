import json
from pathlib import Path

import httpx

from core import config

KB_DIR = config.ROOT / "data" / "kb"
OUT_FILE = Path(__file__).resolve().parent / "vectors.json"


def read_articles() -> list[dict]:
    articles = []
    for md in sorted(KB_DIR.glob("*.md")):
        lines = md.read_text(encoding="utf-8").splitlines()
        articles.append(
            {"source": md.stem, "title": lines[0].lstrip("# ").strip(), "body": "\n".join(lines[1:]).strip()}
        )
    return articles


def embed(texts: list[str]) -> list[list[float]]:
    with httpx.Client(trust_env=False, timeout=120) as client:
        r = client.post(config.EMBED_URL, json={"model": config.EMBED_MODEL, "input": texts})
        r.raise_for_status()
    return [item["embedding"] for item in sorted(r.json()["data"], key=lambda d: d["index"])]


def main() -> None:
    articles = read_articles()
    vectors = embed([f"{config.EMBED_DOC_PREFIX}{a['title']}\n{a['body']}" for a in articles])
    OUT_FILE.write_text(
        json.dumps([{**a, "vector": v} for a, v in zip(articles, vectors, strict=True)], ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"ok: {len(articles)} статей, dim={len(vectors[0])}")


if __name__ == "__main__":
    main()
