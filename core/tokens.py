import httpx
import jwt

from core import config


class Tokens:
    def __init__(self, login: str) -> None:
        self.login = login
        self._tokens: dict[str, str] = {}
        self._claims: dict[str, dict] = {}

    async def get(self, resource_key: str) -> str:
        if resource_key not in self._tokens:
            await self._request(resource_key, config.TOKEN_TTL_SEC)
        return self._tokens[resource_key]

    async def claims(self, resource_key: str = "account") -> dict:
        await self.get(resource_key)
        return self._claims[resource_key]

    async def refresh(self, resource_key: str) -> str:
        self._tokens.pop(resource_key, None)
        self._claims.pop(resource_key, None)
        return await self.get(resource_key)

    async def force_short(self) -> None:
        for key in list(self._tokens):
            await self._request(key, ttl_sec=1)

    async def _request(self, resource_key: str, ttl_sec: int) -> None:
        async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
            r = await client.post(
                f"{config.ISSUER_URL}/token",
                json={"resource": config.RESOURCES[resource_key], "user": self.login, "ttl_sec": ttl_sec},
            )
            r.raise_for_status()
        token = r.json()["access_token"]
        self._tokens[resource_key] = token
        self._claims[resource_key] = jwt.decode(token, options={"verify_signature": False})
