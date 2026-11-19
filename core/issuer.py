import time

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from core import db
from core.config import ISSUER_URL, TOKEN_TTL_SEC

KID = "issuer-key-1"

_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_PEM = _key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
_PUBLIC_JWK = jwt.algorithms.RSAAlgorithm.to_jwk(_key.public_key(), as_dict=True) | {
    "kid": KID,
    "alg": "RS256",
    "use": "sig",
}


def issue_token(*, resource: str, sub: str, role: str, scopes: list[str], ttl_sec: int) -> tuple[str, int]:
    now = int(time.time())
    claims = {
        "iss": ISSUER_URL,
        "sub": sub,
        "aud": resource,
        "role": role,
        "scope": " ".join(scopes),
        "iat": now,
        "exp": now + ttl_sec,
    }
    return jwt.encode(claims, _PRIVATE_PEM, algorithm="RS256", headers={"kid": KID}), claims["exp"]


async def token_endpoint(request: Request) -> JSONResponse:
    body = await request.json()
    resource = body.get("resource", "")
    user = db.fetchone("select sub, role, scopes from users where login = %s", (body.get("user", ""),))
    if user is None or not resource:
        return JSONResponse({"error": "invalid_request"}, status_code=400)
    token, exp = issue_token(
        resource=resource,
        sub=user["sub"],
        role=user["role"],
        scopes=list(user["scopes"]),
        ttl_sec=int(body.get("ttl_sec", TOKEN_TTL_SEC)),
    )
    return JSONResponse({"access_token": token, "token_type": "Bearer", "expires_at": exp})


async def jwks_endpoint(request: Request) -> JSONResponse:
    return JSONResponse({"keys": [_PUBLIC_JWK]})


def issuer_routes() -> list[Route]:
    return [
        Route("/token", token_endpoint, methods=["POST"]),
        Route("/jwks.json", jwks_endpoint, methods=["GET"]),
    ]
