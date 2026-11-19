from core.config import RESOURCES
from core.money import with_rub
from core.server_auth import caller, make_mcp_server, require_role
from services import store

account = make_mcp_server(
    "account",
    resource=RESOURCES["account"],
    instructions="Аккаунт, сервер и каталог конфигураций. Аккаунт определяется токеном вызова.",
)


def _my_account() -> str | None:
    sub, _ = caller()
    return store.account_of(sub)


@account.tool(
    description="Аккаунт вызывающего: название, контакты для уведомлений, подключенные услуги, плата в месяц."
)
def get_my_account() -> dict:
    row = store.account(_my_account() or "")
    if row is None:
        return {"error": "no_account"}
    return with_rub({k: row[k] for k in ("id", "name", "email", "phone", "services", "monthly_kop")})


@account.tool(description="Сервер вызывающего: имя, конфигурация, vCPU, память, диск, цена конфигурации.")
def get_my_server() -> dict:
    row = store.account(_my_account() or "")
    if row is None:
        return {"error": "no_account"}
    return with_rub(row["server"])


@account.tool(description="Каталог конфигураций серверов: код, название, vCPU, память, диск, цена в копейках.")
def list_plans() -> dict:
    return {"plans": with_rub(store.plans())}


@account.tool(description="Обзор любого аккаунта для инженера поддержки (роль support).")
def get_account_overview(account_id: str) -> dict:
    require_role("support")
    row = store.account(account_id)
    if row is None:
        return {"error": "not_found"}
    return with_rub(
        {"id": row["id"], "name": row["name"], "plan": row["server"]["plan_name"], "monthly_kop": row["monthly_kop"]}
    )
