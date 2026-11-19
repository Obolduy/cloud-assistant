import asyncio
import sys
import uuid

import httpx

from core.config import STAND_URL
from core.money import format_rub

ACCOUNT = "acc_1001"
RESULTS: list[bool] = []


def check(group: str, name: str, ok: bool, detail: object = "") -> None:
    RESULTS.append(bool(ok))
    print(f"[{'ok ' if ok else 'FAIL'}] {group}/{name} {detail}".rstrip())


def change(c: httpx.Client, plan: str, key: str | None = None) -> dict:
    body = {"account": ACCOUNT, "plan": plan, "idempotency_key": key or str(uuid.uuid4())}
    return c.post("/mock/billing/plan-change", json=body).json()


def group_0(c: httpx.Client) -> None:
    check("0", "stand_health", c.get("/health").status_code == 200)
    check("0", "reset", c.post("/mock/admin/reset").json().get("ok") is True)

    account = c.get("/mock/account", params={"account": ACCOUNT}).json()
    check("0", "account_plan", account["server"]["plan_code"] == "standard", account["server"]["plan_code"])
    check("0", "account_monthly", account["monthly_kop"] == 124000, format_rub(account["monthly_kop"]))
    check("0", "unknown_account_404", c.get("/mock/account", params={"account": "acc_x"}).status_code == 404)

    charges = c.get("/mock/billing/charges", params={"account": ACCOUNT, "period": "2026-11"}).json()
    check("0", "charges_total", charges["total_kop"] == 124000, format_rub(charges["total_kop"]))
    check("0", "money_format", format_rub(124000) == "1 240 ₽" and format_rub(1490050) == "14 900,50 ₽")

    key = str(uuid.uuid4())
    first = change(c, "pro", key)
    check(
        "0",
        "plan_change_executed",
        first["outcome"] == "executed",
        f"{first['before']['plan']} → {first['after']['plan']}",
    )
    again = change(c, "pro", key)
    check("0", "plan_change_duplicate", again["outcome"] == "duplicate" and again["after"] == first["after"])
    other = c.post("/mock/billing/plan-change", json={"account": "acc_x", "plan": "pro", "idempotency_key": key})
    check("0", "key_reused_other_account", other.json()["outcome"] == "idempotency_key_reused")
    check("0", "same_plan", change(c, "pro")["outcome"] == "same_plan")
    check("0", "disk_downgrade", change(c, "standard")["outcome"] == "disk_downgrade")
    unknown = change(c, "luxe")
    check("0", "unknown_plan", unknown["outcome"] == "unknown_plan" and "gpu" in unknown["available"])
    no_key = c.post("/mock/billing/plan-change", json={"account": ACCOUNT, "plan": "gpu"})
    check("0", "key_required", no_key.status_code == 400)

    c.post("/mock/admin/billing-quota", json={"account": ACCOUNT, "remaining": 0})
    check("0", "daily_limit", change(c, "gpu")["outcome"] == "daily_limit")
    server = c.get("/mock/account", params={"account": ACCOUNT}).json()["server"]
    check("0", "plan_after_limit", server["plan_code"] == "pro", server["plan_code"])

    def toggle(code: str, enabled: bool) -> str:
        body = {"account": ACCOUNT, "service": code, "enabled": enabled}
        return c.post("/mock/account/services", json=body).json()["outcome"]

    check("0", "service_already_on", toggle("backup", True) == "service_already_on")
    check("0", "service_on", toggle("ipv4", True) == "executed")
    check(
        "0", "service_off_twice", toggle("ipv4", False) == "executed" and toggle("ipv4", False) == "service_already_off"
    )
    check("0", "unknown_service", toggle("music", True) == "unknown_service")

    contacts = c.post("/mock/account/contacts", json={"account": ACCOUNT, "email": "ops@example.ru"}).json()
    ok = contacts["before"]["email"] == "anna@example.ru" and contacts["after"]["email"] == "ops@example.ru"
    check("0", "contacts_before_after", ok)

    ticket = c.post("/mock/tickets", json={"account": ACCOUNT, "subject": "сервер не отвечает", "note": "web-1"}).json()
    listed = [t["id"] for t in c.get("/mock/tickets", params={"account": ACCOUNT}).json()["tickets"]]
    check("0", "ticket_created", ticket["ticket_id"] in listed, ticket["ticket_id"])

    c.post("/mock/admin/reset")
    account = c.get("/mock/account", params={"account": ACCOUNT}).json()
    ok = account["server"]["plan_code"] == "standard" and account["email"] == "anna@example.ru"
    check("0", "reset_restores_seed", ok and not c.get("/mock/tickets").json()["tickets"])


async def mcp_checks() -> None:
    from mcp.shared.exceptions import MCPError

    from core.mcpclient import McpPool
    from core.tokens import Tokens

    anna = McpPool(Tokens("anna"), ("account", "billing", "kb"))
    olga = McpPool(Tokens("olga"), ("account",))
    await anna.connect()
    await olga.connect()
    try:
        names = set(anna.tool_names())
        expected = {"get_my_account", "get_my_server", "list_plans", "list_my_charges", "search_kb"}
        check("0", "mcp_tools", expected <= names, sorted(names))
        server = await anna.call("account", "get_my_server")
        check("0", "mcp_my_server", server.get("plan_code") == "standard" and server.get("price_rub") == "990 ₽")
        charges = await anna.call("billing", "list_my_charges", {"period": "2026-11"})
        check("0", "mcp_my_charges", charges.get("total_rub") == "1 240 ₽", charges.get("total_rub"))
        hits = await anna.call("kb", "search_kb", {"query": "почему списали деньги за сервер"})
        sources = [h["source"] for h in hits.get("results", [])]
        check("0", "kb_search", "charge_rules" in sources, sources)
        overview = await olga.call("account", "get_account_overview", {"account_id": ACCOUNT})
        check("0", "support_overview", overview.get("plan") == "Стандарт")
        try:
            await anna.call("account", "get_account_overview", {"account_id": ACCOUNT})
            check("0", "owner_overview_forbidden", False)
        except MCPError as e:
            check("0", "owner_overview_forbidden", e.message == "forbidden")
    finally:
        await anna.close()
        await olga.close()


def group_0_stand(c: httpx.Client) -> None:
    from core.config import RESOURCES

    r = c.post("/token", json={"resource": RESOURCES["account"], "user": "anna"})
    token = r.json().get("access_token", "")
    check("0", "issuer_token", r.status_code == 200 and bool(token))
    check(
        "0",
        "issuer_unknown_user",
        c.post("/token", json={"resource": RESOURCES["account"], "user": "x"}).status_code == 400,
    )
    check("0", "issuer_jwks", bool(c.get("/jwks.json").json().get("keys")))
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    headers = {"Accept": "application/json, text/event-stream"}
    check("0", "mcp_401_without_bearer", c.post("/account/mcp", json=init, headers=headers).status_code == 401)
    foreign = c.post("/token", json={"resource": RESOURCES["kb"], "user": "anna"}).json()["access_token"]
    r = c.post("/account/mcp", json=init, headers=headers | {"Authorization": f"Bearer {foreign}"})
    check("0", "mcp_401_foreign_audience", r.status_code == 401)
    asyncio.run(mcp_checks())


GROUPS = {"0": lambda c: (group_0(c), group_0_stand(c))}

if __name__ == "__main__":
    selected = sys.argv[1:] or list(GROUPS)
    with httpx.Client(base_url=STAND_URL, trust_env=False, timeout=15) as client:
        for group in selected:
            GROUPS[group](client)
    print(f"\n{sum(RESULTS)}/{len(RESULTS)} ok")
    sys.exit(0 if all(RESULTS) else 1)
