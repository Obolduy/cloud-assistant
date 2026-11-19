from contextlib import AsyncExitStack, asynccontextmanager

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from core import config
from core.issuer import issuer_routes
from services import rest
from services.account import account
from services.billing import billing
from services.kb import kb

SERVERS = {"account": account, "billing": billing, "kb": kb}


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "stand"})


async def web_config(request: Request) -> Response:
    return Response(f"window.BACKEND = '{config.BACKEND_URL}';", media_type="text/javascript")


@asynccontextmanager
async def lifespan(app: Starlette):
    async with AsyncExitStack() as stack:
        for server in SERVERS.values():
            await stack.enter_async_context(server.session_manager.run())
        yield


def build_app() -> Starlette:
    routes = [
        Route("/health", health, methods=["GET"]),
        Route("/config.js", web_config, methods=["GET"]),
        *issuer_routes(),
        *rest.mock_routes(),
        *(Mount(f"/{name}", app=server.streamable_http_app()) for name, server in SERVERS.items()),
        Mount("/", app=StaticFiles(directory=config.ROOT / "web", html=True)),
    ]
    return Starlette(routes=routes, lifespan=lifespan)
