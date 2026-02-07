"""
Cognito JWT authentication for the Duo Mapping API.

Validates access tokens from the Cognito User Pool using the issuer and
app client ID. Uses JWKS from the issuer for signature verification.
"""
import os
from typing import Annotated

import jwt
from fastapi import Header, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED

# Cognito configuration (must match the frontend SPA)
COGNITO_ISSUER = os.getenv(
    "COGNITO_ISSUER",
    "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_oPCgNjR0o",
)
COGNITO_APP_CLIENT_ID = os.getenv(
    "COGNITO_APP_CLIENT_ID",
    "7889jq6rloftibcqp7jhemj6rn",
)
JWKS_URI = f"{COGNITO_ISSUER.rstrip('/')}/.well-known/jwks.json"

# Lazy-initialized JWKS client (avoids network at import time in Lambda)
_jwks_client: jwt.PyJWKClient | None = None


def _get_jwks_client() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(JWKS_URI)
    return _jwks_client


def require_cognito_token(
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """
    FastAPI dependency: require a valid Cognito access token in the
    Authorization header (Bearer <token>). Validates signature (JWKS),
    issuer, expiry, token_use=access, and client_id. Returns decoded
    claims; raises 401 if missing or invalid.
    """
    if not authorization:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    parts = authorization.split("Bearer ")
    if len(parts) < 2:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    token = parts[1].strip()
    if not token:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    jwks_client = _get_jwks_client()
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
    except jwt.exceptions.InvalidTokenError as e:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        ) from e

    try:
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=COGNITO_ISSUER.rstrip("/"),
            options={
                "verify_aud": False,
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
                "require": ["token_use", "exp", "iss", "sub"],
            },
        )
    except jwt.exceptions.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        ) from e
    except jwt.exceptions.InvalidTokenError as e:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        ) from e

    if claims.get("token_use") != "access":
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    if claims.get("client_id") != COGNITO_APP_CLIENT_ID:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    return claims
