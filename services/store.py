import secrets

from psycopg.types.json import Jsonb

from core import db
from core.config import DAILY_PLAN_CHANGE_LIMIT


def plans() -> list[dict]:
    return db.fetchall("select code, name, vcpu, ram_gb, disk_gb, price_kop from plans order by price_kop")


def services() -> list[dict]:
    return db.fetchall("select code, name, price_kop from services order by code")


def account(account_id: str) -> dict | None:
    row = db.fetchone("select id, name, email, phone from accounts where id = %s", (account_id,))
    if row is None:
        return None
    server = db.fetchone(
        "select s.id, s.hostname, s.disk_gb, p.code as plan_code, p.name as plan_name,"
        " p.vcpu, p.ram_gb, p.price_kop"
        " from servers s join plans p on p.code = s.plan_code where s.account_id = %s",
        (account_id,),
    )
    attached = db.fetchall(
        "select v.code, v.name, v.price_kop, a.enabled"
        " from account_services a join services v on v.code = a.service_code"
        " where a.account_id = %s order by v.code",
        (account_id,),
    )
    monthly = server["price_kop"] + sum(s["price_kop"] for s in attached if s["enabled"])
    return {**row, "server": server, "services": attached, "monthly_kop": monthly}


def charges(account_id: str, period: str | None = None) -> dict:
    rows = db.fetchall(
        "select period, label, amount_kop from charges"
        " where account_id = %s and (%s::text is null or period = %s) order by period desc, id",
        (account_id, period, period),
    )
    return {"charges": rows, "total_kop": sum(r["amount_kop"] for r in rows)}


def _plan_view(row: dict) -> dict:
    return {"plan": row["code"], "name": row["name"], "price_kop": row["price_kop"]}


def change_plan(account_id: str, plan_code: str, idempotency_key: str) -> dict:
    if not idempotency_key:
        return {"outcome": "idempotency_key_required"}
    with db.connect() as conn:
        conn.execute("select pg_advisory_xact_lock(hashtext(%s))", (account_id,))
        known = conn.execute(
            "select account_id, result from billing_operations where idempotency_key = %s", (idempotency_key,)
        ).fetchone()
        if known and known["account_id"] != account_id:
            return {"outcome": "idempotency_key_reused"}
        if known:
            return {**known["result"], "outcome": "duplicate"}
        server = conn.execute(
            "select s.disk_gb, p.code, p.name, p.price_kop from servers s"
            " join plans p on p.code = s.plan_code where s.account_id = %s",
            (account_id,),
        ).fetchone()
        if server is None:
            return {"outcome": "not_found"}
        target = conn.execute(
            "select code, name, disk_gb, price_kop from plans where code = %s", (plan_code,)
        ).fetchone()
        if target is None:
            available = [r["code"] for r in conn.execute("select code from plans order by price_kop")]
            return {"outcome": "unknown_plan", "available": available}
        if target["code"] == server["code"]:
            return {"outcome": "same_plan", "current": server["code"]}
        if target["disk_gb"] < server["disk_gb"]:
            return {"outcome": "disk_downgrade", "disk_gb": server["disk_gb"], "target_disk_gb": target["disk_gb"]}
        changes_today = conn.execute(
            "select count(*) as n from plan_changes where account_id = %s and created_at::date = current_date",
            (account_id,),
        ).fetchone()["n"]
        if changes_today >= DAILY_PLAN_CHANGE_LIMIT:
            return {"outcome": "daily_limit", "limit": DAILY_PLAN_CHANGE_LIMIT}
        conn.execute(
            "update servers set plan_code = %s, disk_gb = %s where account_id = %s",
            (target["code"], target["disk_gb"], account_id),
        )
        conn.execute(
            "insert into plan_changes(account_id, before, after, idempotency_key) values (%s, %s, %s, %s)",
            (account_id, server["code"], target["code"], idempotency_key),
        )
        view = {"before": _plan_view(server), "after": _plan_view(target)}
        conn.execute(
            "insert into billing_operations(idempotency_key, account_id, result) values (%s, %s, %s)",
            (idempotency_key, account_id, Jsonb(view)),
        )
    return {"outcome": "executed", **view}


def toggle_service(account_id: str, service_code: str, enabled: bool) -> dict:
    with db.connect() as conn:
        service = conn.execute("select code, name, price_kop from services where code = %s", (service_code,)).fetchone()
        if service is None:
            available = [r["code"] for r in conn.execute("select code from services order by code")]
            return {"outcome": "unknown_service", "available": available}
        row = conn.execute(
            "select enabled from account_services where account_id = %s and service_code = %s for update",
            (account_id, service_code),
        ).fetchone()
        before = bool(row and row["enabled"])
        if before == enabled:
            return {"outcome": "service_already_on" if enabled else "service_already_off", "service": service_code}
        conn.execute(
            "insert into account_services(account_id, service_code, enabled) values (%s, %s, %s)"
            " on conflict (account_id, service_code) do update set enabled = excluded.enabled",
            (account_id, service_code, enabled),
        )
    return {
        "outcome": "executed",
        "service": service_code,
        "price_kop": service["price_kop"],
        "before": {"enabled": before},
        "after": {"enabled": enabled},
    }


def set_contacts(account_id: str, email: str | None, phone: str | None) -> dict:
    with db.connect() as conn:
        before = conn.execute("select email, phone from accounts where id = %s for update", (account_id,)).fetchone()
        if before is None:
            return {"outcome": "not_found"}
        after = conn.execute(
            "update accounts set email = coalesce(%s, email), phone = coalesce(%s, phone)"
            " where id = %s returning email, phone",
            (email, phone, account_id),
        ).fetchone()
    return {"outcome": "executed", "before": before, "after": after}


def create_ticket(account_id: str, subject: str, note: str) -> dict:
    ticket_id = f"t_{secrets.token_hex(3)}"
    with db.connect() as conn:
        conn.execute(
            "insert into tickets(id, account_id, subject, note) values (%s, %s, %s, %s)",
            (ticket_id, account_id, subject, note),
        )
    return {"ticket_id": ticket_id, "status": "open"}


def tickets(account_id: str | None = None) -> list[dict]:
    return db.fetchall(
        "select id, account_id, subject, note, status, to_char(created_at, 'YYYY-MM-DD HH24:MI') as created_at"
        " from tickets where %s::text is null or account_id = %s order by created_at desc",
        (account_id, account_id),
    )


def set_daily_quota(account_id: str, remaining: int) -> dict:
    used = max(0, DAILY_PLAN_CHANGE_LIMIT - remaining)
    with db.connect() as conn:
        conn.execute(
            "delete from plan_changes where account_id = %s and created_at::date = current_date", (account_id,)
        )
        for i in range(used):
            conn.execute(
                "insert into plan_changes(account_id, before, after, idempotency_key) values (%s, '-', '-', %s)",
                (account_id, f"quota-{i}"),
            )
    return {"account_id": account_id, "remaining": DAILY_PLAN_CHANGE_LIMIT - used}


def counts() -> dict:
    tables = ("accounts", "users", "servers", "plans", "services", "charges", "tickets")
    return {t: db.fetchone(f"select count(*) as n from {t}")["n"] for t in tables}
