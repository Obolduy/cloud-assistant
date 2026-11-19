import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app import orchestrator, sessions
from core import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.setup_model()
    yield


app = FastAPI(title="cloud-assistant", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "backend"}


@app.post("/api/session")
async def create_session(body: dict) -> dict:
    try:
        session = await sessions.open_session(body.get("user", ""))
    except KeyError as e:
        raise HTTPException(status_code=400, detail="неизвестный пользователь") from e
    return {
        "session_id": session.session_id,
        "name": session.user["name"],
        "role": session.user["role"],
        "visible_tools": session.pool.tool_names(),
    }


@app.post("/api/chat")
async def chat(body: dict) -> StreamingResponse:
    session = sessions.get(body.get("session_id", ""))
    if session is None:
        raise HTTPException(status_code=404, detail="сессия не найдена")
    message = str(body.get("message", "")).strip()
    if not message:
        raise HTTPException(status_code=400, detail="пустое сообщение")

    queue: asyncio.Queue = asyncio.Queue()

    async def run() -> None:
        try:
            await orchestrator.run_turn(session, message, queue.put)
        except Exception as e:
            await queue.put({"type": "error", "detail": str(e)[:200]})
        finally:
            await queue.put(None)

    task = asyncio.create_task(run())

    async def stream():
        try:
            while (event := await queue.get()) is not None:
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield 'data: {"type": "done"}\n\n'
        finally:
            task.cancel()

    return StreamingResponse(stream(), media_type="text/event-stream")
