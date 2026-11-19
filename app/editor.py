from app import llm
from app.workers import CATALOG

EDITOR_PROMPT = """\
Ты – редактор ассистента облачного хостинга. Ты получаешь сообщение пользователя
и доклады агентов. Напиши ответ пользователю: кратко, по-русски, только по фактам
докладов. Суммы переноси из докладов как есть. Ничего не выдумывай. Если докладов
нет, ответь на сообщение сам.
"""


def build_editor(login: str):
    return llm.build_agent(f"редактор ({login})", EDITOR_PROMPT)


def editor_task(message: str, runs: list[dict]) -> str:
    lines = [f"Сообщение пользователя: {message}"]
    for i, run in enumerate(runs, 1):
        lines.append(f"{i}. {CATALOG[run['agent']]['title']}: {run['report']}")
    if not runs:
        lines.append("Докладов нет: агенты не запускались.")
    lines.append("Напиши ответ пользователю по фактам докладов.")
    return "\n".join(lines)
