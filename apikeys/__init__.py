__version__ = "0.1.2"

from .client import APIKeyClient
from .db.session import create_tables
from .exceptions import APIKeyError, InsufficientScopeError, InvalidKeyError, QuotaError, RevokedKeyError
from .models import APIKey, APIKeyCreated, KeyMetadata, Organization, Product, Project

__all__ = [
    "APIKeyClient",
    "create_tables",
    "Organization",
    "Project",
    "Product",
    "KeyMetadata",
    "APIKey",
    "APIKeyCreated",
    "APIKeyError",
    "InvalidKeyError",
    "RevokedKeyError",
    "QuotaError",
    "InsufficientScopeError",
]
