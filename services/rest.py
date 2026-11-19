from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from core import seed
from services import store


def _account(request: Request) -> str:
    return request.query_params.get("account", "")


async def get_account(request: Request) -> JSONResponse:
    row = store.account(_account(request))
    if row is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return JSONResponse(row)


async def get_plans(request: Request) -> JSONResponse:
    return JSONResponse({"plans": store.plans()})


async def get_services(request: Request) -> JSONResponse:
    return JSONResponse({"services": store.services()})


async def get_charges(request: Request) -> JSONResponse:
    return JSONResponse(store.charges(_account(request), request.query_params.get("period")))


async def post_plan_change(request: Request) -> JSONResponse:
    body = await request.json()
    result = store.change_plan(body.get("account", ""), body.get("plan", ""), body.get("idempotency_key", ""))
    status = {"not_found": 404, "idempotency_key_required": 400}.get(result["outcome"], 200)
    return JSONResponse(result, status_code=status)


async def post_service(request: Request) -> JSONResponse:
    body = await request.json()
    return JSONResponse(
        store.toggle_service(body.get("account", ""), body.get("service", ""), bool(body.get("enabled")))
    )


async def post_contacts(request: Request) -> JSONResponse:
    body = await request.json()
    result = store.set_contacts(body.get("account", ""), body.get("email"), body.get("phone"))
    return JSONResponse(result, status_code=404 if result["outcome"] == "not_found" else 200)


async def get_tickets(request: Request) -> JSONResponse:
    return JSONResponse({"tickets": store.tickets(_account(request) or None)})


async def post_ticket(request: Request) -> JSONResponse:
    body = await request.json()
    return JSONResponse(store.create_ticket(body.get("account", ""), body.get("subject", ""), body.get("note", "")))


async def admin_reset(request: Request) -> JSONResponse:
    return JSONResponse({"ok": True, **seed.seed()})


async def admin_quota(request: Request) -> JSONResponse:
    body = await request.json()
    return JSONResponse(store.set_daily_quota(body.get("account", ""), int(body.get("remaining", 0))))


async def admin_counts(request: Request) -> JSONResponse:
    return JSONResponse(store.counts())


def mock_routes() -> list[Route]:
    return [
        Route("/mock/account", get_account, methods=["GET"]),
        Route("/mock/account/services", post_service, methods=["POST"]),
        Route("/mock/account/contacts", post_contacts, methods=["POST"]),
        Route("/mock/plans", get_plans, methods=["GET"]),
        Route("/mock/services", get_services, methods=["GET"]),
        Route("/mock/billing/charges", get_charges, methods=["GET"]),
        Route("/mock/billing/plan-change", post_plan_change, methods=["POST"]),
        Route("/mock/tickets", get_tickets, methods=["GET"]),
        Route("/mock/tickets", post_ticket, methods=["POST"]),
        Route("/mock/admin/reset", admin_reset, methods=["POST"]),
        Route("/mock/admin/billing-quota", admin_quota, methods=["POST"]),
        Route("/mock/admin/counts", admin_counts, methods=["GET"]),
    ]
