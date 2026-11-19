import yaml

from core import db
from core.config import ROOT

DEMO_FILE = ROOT / "data" / "demo.yaml"

TABLES = (
    "billing_operations",
    "plan_changes",
    "tickets",
    "charges",
    "account_services",
    "servers",
    "users",
    "accounts",
    "services",
    "plans",
)


def seed() -> dict:
    demo = yaml.safe_load(DEMO_FILE.read_text(encoding="utf-8"))
    plans = {p["code"]: p for p in demo["plans"]}
    with db.connect() as conn:
        for table in TABLES:
            conn.execute(f"delete from {table}")
        for p in demo["plans"]:
            conn.execute(
                "insert into plans(code, name, vcpu, ram_gb, disk_gb, price_kop) values (%s, %s, %s, %s, %s, %s)",
                (p["code"], p["name"], p["vcpu"], p["ram_gb"], p["disk_gb"], p["price_kop"]),
            )
        for s in demo["services"]:
            conn.execute(
                "insert into services(code, name, price_kop) values (%s, %s, %s)",
                (s["code"], s["name"], s["price_kop"]),
            )
        for a in demo["accounts"]:
            conn.execute(
                "insert into accounts(id, name, email, phone) values (%s, %s, %s, %s)",
                (a["id"], a["name"], a["email"], a["phone"]),
            )
            server = a["server"]
            conn.execute(
                "insert into servers(id, account_id, hostname, plan_code, disk_gb) values (%s, %s, %s, %s, %s)",
                (server["id"], a["id"], server["hostname"], server["plan"], plans[server["plan"]]["disk_gb"]),
            )
            for s in a["services"]:
                conn.execute(
                    "insert into account_services(account_id, service_code, enabled) values (%s, %s, %s)",
                    (a["id"], s["code"], s["enabled"]),
                )
        for u in demo["users"]:
            conn.execute(
                "insert into users(login, sub, name, role, scopes, account_id) values (%s, %s, %s, %s, %s, %s)",
                (u["login"], u["sub"], u["name"], u["role"], u["scopes"], u["account"]),
            )
        for c in demo["charges"]:
            conn.execute(
                "insert into charges(account_id, period, label, amount_kop) values (%s, %s, %s, %s)",
                (c["account"], c["period"], c["label"], c["amount_kop"]),
            )
    return {"accounts": len(demo["accounts"]), "users": len(demo["users"]), "plans": len(demo["plans"])}


if __name__ == "__main__":
    print("seed:", seed())
