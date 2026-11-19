import contextlib
import json

import httpx2
from agents.mcp import MCPServerStreamableHttp
from mcp.shared.exceptions import MCPError

from core import config
from core.server_auth import FORBIDDEN_CODE


def client_factory(headers=None, timeout=None, auth=None, **kwargs) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(headers=headers, timeout=timeout, auth=auth, trust_env=False)


class McpPool:
    def __init__(self, tokens, resource_keys: tuple[str, ...]) -> None:
        self.tokens = tokens
        self.resource_keys = resource_keys
        self._servers: dict[str, MCPServerStreamableHttp] = {}
        self._tools: dict[str, tuple[str, object]] = {}

    async def connect(self) -> None:
        for key in self.resource_keys:
            server = await self._connect(key)
            for tool in await server.list_tools():
                self._tools[tool.name] = (key, tool)

    async def _connect(self, key: str) -> MCPServerStreamableHttp:
        token = await self.tokens.get(key)
        server = MCPServerStreamableHttp(
            params={
                "url": f"{config.RESOURCES[key]}/mcp",
                "headers": {"Authorization": f"Bearer {token}"},
                "httpx_client_factory": client_factory,
            }
        )
        await server.__aenter__()
        self._servers[key] = server
        return server

    def tool_names(self) -> list[str]:
        return sorted(self._tools)

    def resource_of(self, name: str) -> str:
        return self._tools[name][0]

    def tool_schema(self, name: str) -> dict:
        return dict(self._tools[name][1].input_schema)

    def tool_description(self, name: str) -> str:
        return self._tools[name][1].description or name

    async def call(self, resource_key: str, tool: str, args: dict | None = None) -> dict:
        try:
            return await self._call_once(resource_key, tool, args)
        except MCPError as e:
            if e.code == FORBIDDEN_CODE:
                raise
            return await self._reconnect_and_retry(resource_key, tool, args)
        except Exception:
            return await self._reconnect_and_retry(resource_key, tool, args)

    async def _reconnect_and_retry(self, resource_key: str, tool: str, args: dict | None) -> dict:
        await self.tokens.refresh(resource_key)
        old = self._servers.pop(resource_key, None)
        if old is not None:
            with contextlib.suppress(Exception):
                await old.__aexit__(None, None, None)
        await self._connect(resource_key)
        return await self._call_once(resource_key, tool, args)

    async def _call_once(self, resource_key: str, tool: str, args: dict | None) -> dict:
        result = await self._servers[resource_key].call_tool(tool, args or {})
        text = result.content[0].text if result.content else "{}"
        try:
            return json.loads(text)
        except ValueError:
            return {"raw": text}

    async def close(self) -> None:
        for server in self._servers.values():
            with contextlib.suppress(Exception):
                await server.__aexit__(None, None, None)
        self._servers.clear()
