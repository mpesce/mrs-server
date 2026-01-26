"""
Configuration management for MRS server.

Uses pydantic-settings for environment variable loading with sensible defaults.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """MRS Server configuration."""

    # Server identity
    server_url: str = "http://localhost:8000"
    server_domain: str = "localhost"
    admin_email: str = "admin@localhost"

    # Database
    database_path: str = "./mrs.db"

    # Server options
    host: str = "0.0.0.0"
    port: int = 8000
    max_radius: float = 1_000_000  # meters (1000km max)
    max_results: int = 100
    max_registrations_per_user: int = 0  # 0 = unlimited

    # Federation
    bootstrap_peers: list[str] = []  # Manually configured peer URLs

    # Auth
    token_expiry_hours: int = 24 * 7  # 1 week default
    key_cache_ttl_seconds: int = 3600  # 1 hour

    # For future HTTP signature support
    enable_http_signatures: bool = False

    model_config = {
        "env_prefix": "MRS_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# Global settings instance
settings = Settings()
