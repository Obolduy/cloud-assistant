import uuid
from dataclasses import dataclass, field

from core.mcpclient import McpPool
from core.tokens import Tokens
from services import store


@dataclass
class Session:
    login: str
    user: dict
    tokens: Tokens
    pool: McpPool
    claims: dict
    thread: list = field(default_factory=list)
    planner: object | None = None
    session_id: str = field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:8]}")


SESSIONS: dict[str, Session] = {}


async def open_session(login: str) -> Session:
    user = store.user(login)
    if user is None:
        raise KeyError(login)
    tokens = Tokens(login)
    claims = await tokens.claims("account")
    pool = McpPool(tokens, resource_keys=("account", "billing", "kb"))
    await pool.connect()
    session = Session(login=login, user=user, tokens=tokens, pool=pool, claims=claims)
    SESSIONS[session.session_id] = session
    return session


def get(session_id: str) -> Session | None:
    return SESSIONS.get(session_id)
