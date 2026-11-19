from core.config import RESOURCES
from core.money import with_rub
from core.server_auth import caller, make_mcp_server
from services import store

billing = make_mcp_server(
    "billing",
    resource=RESOURCES["billing"],
    instructions="Списания аккаунта. Аккаунт определяется токеном вызова.",
)


@billing.tool(
    description="Списания аккаунта вызывающего: период, строка выписки, сумма в копейках и итог. period – ГГГГ-ММ."
)
def list_my_charges(period: str | None = None) -> dict:
    sub, _ = caller()
    account_id = store.account_of(sub)
    if account_id is None:
        return {"error": "no_account"}
    return with_rub(store.charges(account_id, period))
