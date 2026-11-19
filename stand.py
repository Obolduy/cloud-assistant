from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from services import rest


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "stand"})


def build_app() -> Starlette:
    return Starlette(routes=[Route("/health", health, methods=["GET"]), *rest.mock_routes()])
