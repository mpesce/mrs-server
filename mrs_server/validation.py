"""Validation helpers for untrusted protocol inputs."""

from __future__ import annotations

from urllib.parse import urlsplit

_MAX_URI_LEN = 2048
_ALLOWED_SCHEMES = {"https"}


def validate_service_point_uri(value: str) -> str:
    """Validate and normalize a service_point URI.

    Security-oriented policy (stricter than generic URI syntax):
    - absolute URI with scheme + host
    - https scheme only
    - no userinfo
    - no fragment
    - no control chars / whitespace
    - max length 2048 chars

    Returns normalized URI (trimmed) or raises ValueError.
    """
    uri = value.strip()

    if not uri:
        raise ValueError("service_point must not be empty")
    if len(uri) > _MAX_URI_LEN:
        raise ValueError("service_point is too long")
    if any(ch.isspace() for ch in uri):
        raise ValueError("service_point must not contain whitespace")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in uri):
        raise ValueError("service_point contains control characters")

    parsed = urlsplit(uri)

    if not parsed.scheme:
        raise ValueError("service_point must include a URI scheme")
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValueError("service_point scheme must be https")
    if not parsed.netloc:
        raise ValueError("service_point must include a host")
    if parsed.username or parsed.password:
        raise ValueError("service_point must not include user credentials")
    if parsed.fragment:
        raise ValueError("service_point must not include fragments")

    # urlsplit().hostname handles IPv6 brackets and strips credentials safely.
    if not parsed.hostname:
        raise ValueError("service_point host is invalid")

    return uri
