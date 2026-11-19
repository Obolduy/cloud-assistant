from collections.abc import Awaitable, Callable

from app import planner
from app.editor import build_editor, editor_task
from app.llm import run_agent
from app.sessions import Session
from app.workers import build_workers

Emit = Callable[[dict], Awaitable[None]]


async def run_turn(session: Session, message: str, emit: Emit) -> None:
    if session.planner is None:
        session.planner = planner.build_planner()
    raw_plan, session.thread = await planner.next_plan(session.planner, session.thread, message)
    plan, dropped = planner.gate(raw_plan)
    await emit(
        {
            "type": "plan",
            "agents": [f"{s.agent}: {s.task}" for s in plan.steps] or ["без агентов"],
            "dropped": dropped,
        }
    )

    runs = []
    workers = build_workers(session, tuple(dict.fromkeys(s.agent for s in plan.steps)))
    for step in plan.steps:
        run = await run_agent(workers[step.agent], step.task)
        runs.append({"agent": step.agent, "task": step.task, **run})

    reply = await run_agent(build_editor(session.login), editor_task(message, runs))
    await emit({"type": "reply", "text": reply["report"]})
