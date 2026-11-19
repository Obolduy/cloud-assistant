import json
import time

from agents import Agent, AgentOutputSchema, Runner

from core import config


def build_agent(name: str, instructions: str, tools: list | None = None, output_type=None) -> Agent:
    return Agent(
        name=name,
        instructions=instructions,
        tools=list(tools or []),
        output_type=AgentOutputSchema(output_type, strict_json_schema=False) if output_type else None,
        model=config.MODEL or config.setup_model(),
    )


def _field(raw, key):
    return raw.get(key) if isinstance(raw, dict) else getattr(raw, key, None)


def _loads(value):
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value) if value.strip() else {}
    except ValueError:
        return value


async def run_agent(agent: Agent, task: str) -> dict:
    started = time.perf_counter()
    result = await Runner.run(agent, task, max_turns=6)
    outputs = {
        _field(item.raw_item, "call_id"): _loads(item.output)
        for item in result.new_items
        if item.type == "tool_call_output_item"
    }
    tools = [
        {
            "tool": item.tool_name or _field(item.raw_item, "name"),
            "args": _loads(_field(item.raw_item, "arguments")) or {},
            "result": outputs.get(_field(item.raw_item, "call_id")),
        }
        for item in result.new_items
        if item.type == "tool_call_item"
    ]
    report = result.final_output
    if not isinstance(report, str):
        report = json.dumps(report, ensure_ascii=False, default=str)
    return {"report": report, "tools": tools, "seconds": round(time.perf_counter() - started, 2)}
