__version__ = "0.2.0"

from .client import APIKeyClient
from .db.session import create_tables
from .exceptions import (
    AlreadyExistsError,
    APIKeyError,
    ExpiredKeyError,
    InsufficientScopeError,
    InvalidKeyError,
    QuotaError,  # enforced when rate_limit is set on KeyMetadata
    RevokedKeyError,
)
from .models import (
    APIKey,
    APIKeyCreated,
    KeyMetadata,
    KeyStatus,
    Organization,
    Product,
    Project,
    RateLimit,
    RateLimitWindow,
)

__all__ = [
    "APIKeyClient",
    "create_tables",
    "Organization",
    "Project",
    "Product",
    "KeyMetadata",
    "KeyStatus",
    "RateLimit",
    "RateLimitWindow",
    "APIKey",
    "APIKeyCreated",
    "APIKeyError",
    "InvalidKeyError",
    "ExpiredKeyError",
    "RevokedKeyError",
    "QuotaError",
    "InsufficientScopeError",
    "AlreadyExistsError",
]

try:
    from .fastapi import APIKeyDepends
    __all__ = [*__all__, "APIKeyDepends"]
except ImportError:
    pass
