import json

from agents import FunctionTool
from agents.run_context import RunContextWrapper
from mcp.shared.exceptions import MCPError

from app.sessions import Session


def wrap_mcp_tool(session: Session, name: str) -> FunctionTool:
    async def invoke(ctx: RunContextWrapper, input_json: str) -> str:
        try:
            args = json.loads(input_json) if input_json and input_json.strip() else {}
        except ValueError:
            return json.dumps({"error": "bad_arguments", "detail": "аргументы не JSON, повтори вызов по схеме"})
        try:
            result = await session.pool.call(session.pool.resource_of(name), name, args)
        except MCPError as e:
            data = e.data if isinstance(e.data, dict) else {}
            result = {"error": e.message, **data}
        except Exception as e:
            result = {"error": "tool_failed", "detail": str(e)[:160]}
        return json.dumps(result, ensure_ascii=False)

    return FunctionTool(
        name=name,
        description=session.pool.tool_description(name),
        params_json_schema=session.pool.tool_schema(name),
        on_invoke_tool=invoke,
    )


def wrap_tools(session: Session, names: list[str]) -> list[FunctionTool]:
    known = set(session.pool.tool_names())
    return [wrap_mcp_tool(session, n) for n in names if n in known]
