import httpx
import jwt
from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.shared.exceptions import MCPError

from core.config import ISSUER_URL

FORBIDDEN_CODE = -32003


class JwkCache:
    def __init__(self, jwks_url: str) -> None:
        self.jwks_url = jwks_url
        self._keys: dict[str, dict] = {}

    async def get(self, kid: str | None) -> dict:
        if not self._keys or (kid and kid not in self._keys):
            async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
                r = await client.get(self.jwks_url)
                r.raise_for_status()
            self._keys = {k["kid"]: k for k in r.json()["keys"] if k.get("use", "sig") == "sig"}
        return self._keys.get(kid or "", {})


class JwtVerifier(TokenVerifier):
    def __init__(self, resource: str) -> None:
        self.resource = resource
        self.jwks = JwkCache(f"{ISSUER_URL}/jwks.json")

    async def verify_bearer(self, token: str) -> dict | None:
        try:
            key = await self.jwks.get(jwt.get_unverified_header(token).get("kid"))
            if not key:
                return None
            return jwt.decode(
                token,
                key=jwt.algorithms.RSAAlgorithm.from_jwk(key),
                algorithms=["RS256"],
                audience=self.resource,
                issuer=ISSUER_URL,
            )
        except (jwt.PyJWTError, httpx.HTTPError):
            return None

    async def verify_token(self, token: str) -> AccessToken | None:
        claims = await self.verify_bearer(token)
        if claims is None:
            return None
        return AccessToken(
            token=token,
            client_id="backend",
            scopes=claims.get("scope", "").split(),
            expires_at=claims.get("exp"),
            resource=claims.get("aud"),
            subject=claims.get("sub"),
            claims=claims,
        )


def make_mcp_server(name: str, *, resource: str, instructions: str) -> MCPServer:
    return MCPServer(
        name=name,
        instructions=instructions,
        auth=AuthSettings(issuer_url=ISSUER_URL, resource_server_url=resource, validate_token_resource=True),
        token_verifier=JwtVerifier(resource),
    )


def caller() -> tuple[str, dict]:
    token = get_access_token()
    if token is None:
        raise MCPError(code=FORBIDDEN_CODE, message="unauthenticated")
    return token.subject, token.claims


def require_role(*roles: str) -> tuple[str, dict]:
    sub, claims = caller()
    if claims.get("role") not in roles:
        raise MCPError(
            code=FORBIDDEN_CODE,
            message="forbidden",
            data={"error": "forbidden", "required_roles": list(roles)},
        )
    return sub, claims
