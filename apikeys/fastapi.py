from typing import Optional

from fastapi import HTTPException, Request
from fastapi.responses import Response

from .exceptions import ExpiredKeyError, InsufficientScopeError, InvalidKeyError, QuotaError, RevokedKeyError
from .models import APIKey


class APIKeyDepends:
    """FastAPI dependency that reads X-API-Key, calls validate_key(), and maps exceptions to HTTP responses.

    Usage:
        @router.get("/resource")
        async def handler(key: APIKey = Depends(APIKeyDepends(required_scopes=["read:data"]))):
            ...

    The APIKeyClient must be available on request.state.<state_attr> (default: "apikeys_client").
    """

    def __init__(
        self,
        *,
        required_scopes: list[str] = [],
        required_scope: Optional[str] = None,  # deprecated alias
        org_id: Optional[str] = None,
        product_id: Optional[str] = None,
        state_attr: str = "apikeys_client",
    ) -> None:
        self._required_scopes = required_scopes
        self._required_scope = required_scope
        self._org_id = org_id
        self._product_id = product_id
        self._state_attr = state_attr

    async def __call__(self, request: Request) -> APIKey:
        raw_key = request.headers.get("X-API-Key")
        if not raw_key:
            raise HTTPException(status_code=401, detail="Missing X-API-Key header")

        client = getattr(request.state, self._state_attr, None)
        if client is None:
            raise RuntimeError(
                f"APIKeyClient not found on request.state.{self._state_attr}. "
                "Mount it in a middleware or lifespan handler."
            )

        try:
            return await client.validate_key(
                raw_key,
                org_id=self._org_id,
                product_id=self._product_id,
                required_scopes=self._required_scopes,
                required_scope=self._required_scope,
            )
        except InvalidKeyError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except ExpiredKeyError as e:
            detail = str(e)
            if e.expired_at is not None:
                detail = f"{e} (expired at {e.expired_at.isoformat()})"
            raise HTTPException(status_code=401, detail=detail)
        except RevokedKeyError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except InsufficientScopeError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except QuotaError as e:
            headers = {}
            if e.retry_after_seconds is not None:
                headers["Retry-After"] = str(e.retry_after_seconds)
            raise HTTPException(status_code=429, detail=str(e), headers=headers)
