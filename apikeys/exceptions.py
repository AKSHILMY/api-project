from datetime import datetime
from typing import Optional


class APIKeyError(Exception): ...


class InvalidKeyError(APIKeyError): ...


class ExpiredKeyError(APIKeyError):
    def __init__(self, message: str = "Key has expired", expired_at: Optional[datetime] = None):
        super().__init__(message)
        self.expired_at = expired_at


class RevokedKeyError(APIKeyError): ...


class QuotaError(APIKeyError):
    def __init__(self, message: str = "Rate limit exceeded", retry_after_seconds: Optional[int] = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class InsufficientScopeError(APIKeyError): ...


class AlreadyExistsError(APIKeyError):
    def __init__(self, message: str, existing_id: Optional[str] = None):
        super().__init__(message)
        self.existing_id = existing_id
