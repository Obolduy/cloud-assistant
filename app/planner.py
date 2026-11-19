from agents import Runner
from pydantic import AliasChoices, BaseModel, Field

from app import llm

READ_AGENTS = ("data", "kb")


class Step(BaseModel):
    agent: str = Field(validation_alias=AliasChoices("agent", "agentName"), description="id агента из каталога")
    task: str = Field(
        validation_alias=AliasChoices("task", "job"), description="задача агенту одним предложением по-русски"
    )
    why: str = Field(default="", description="зачем этот шаг, одна короткая фраза")
    action: bool = Field(default=False, description="true, только если шаг изменит данные")


class Plan(BaseModel):
    steps: list[Step] = Field(description="шаги в порядке выполнения, пустой список, если агенты не нужны")
    question: str | None = Field(default=None, description="уточняющий вопрос, если данных для плана мало")


PLANNER_PROMPT = """\
Ты – планировщик ассистента облачного хостинга. С пользователем ты не общаешься:
по его сообщению составляешь план – каких агентов запустить и с какими задачами.
Отвечай строго схемой Plan, без текста вокруг.

Каталог агентов:
- data – агент данных аккаунта: аккаунт, сервер и его конфигурация, каталог
  конфигураций, списания. Инструменты: get_my_account, get_my_server, list_plans,
  list_my_charges.
- kb – агент базы знаний: правила списаний и смены конфигурации, услуги, описания
  конфигураций, контакты. Инструмент: search_kb.

Правила:
- вопрос о данных аккаунта – один шаг data, даже если вопросов несколько;
- вопрос о правилах и последствиях – шаг kb;
- «почему списали» – два шага: data (факты списаний) и kb (правила списаний);
- сравнение конфигураций – шаг data;
- данных для плана не хватает – заполни question и оставь steps пустым;
- приветствие и благодарность – пустые steps.

Пример. Сообщение: «почему в ноябре списали 1 240?»
План: data – «найти списания аккаунта за 2026-11»; kb – «найти правила списаний».
"""


def build_planner():
    return llm.build_agent("планировщик", PLANNER_PROMPT, output_type=Plan)


def gate(plan: Plan) -> tuple[Plan, list[str]]:
    clean, dropped = [], []
    for step in plan.steps:
        if step.agent not in READ_AGENTS:
            dropped.append(f"{step.agent}: агента нет в каталоге")
            continue
        clean.append(step.model_copy(update={"action": False}))
    return Plan(steps=clean, question=plan.question), dropped


async def next_plan(planner, history: list, message: str) -> tuple[Plan, list]:
    run_input = [*history, {"role": "user", "content": message}] if history else message
    result = await Runner.run(planner, run_input)
    return result.final_output, result.to_input_list()
