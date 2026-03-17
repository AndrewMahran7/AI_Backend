"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings sourced from .env / environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = "AI Backend"
    APP_VERSION: str = "0.1.0"
    ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api/v1"

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_backend"

    # ── Gemini LLM ───────────────────────────────────────────────────────
    # GEMINI_TIER controls authentication and rate-limit defaults.
    # "dev"        – standard API key (google.genai with api_key)
    # "enterprise" – Vertex AI + Application Default Credentials
    GEMINI_TIER:             str = "dev"
    GEMINI_API_KEY:          str = ""
    GEMINI_MODEL:            str = "gemini-2.5-pro"
    GEMINI_EMBEDDING_MODEL:  str = "gemini-embedding-001"
    EMBEDDING_DIMENSION:     int = 768

    # Vertex AI – only required when GEMINI_TIER=enterprise.
    GEMINI_VERTEX_PROJECT:   str = ""
    GEMINI_VERTEX_LOCATION:  str = "us-central1"

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
    )

    # ── SAP PLM integration ───────────────────────────────────────────────
    SAP_BASE_URL:         str  = ""
    SAP_USERNAME:         str  = ""
    SAP_PASSWORD:         str  = ""
    SAP_CLIENT:           str  = "100"
    SAP_AUTH_TYPE:        str  = "basic"   # "basic" or "oauth2"
    SAP_OAUTH_TOKEN:      str  = ""
    SAP_TIMEOUT_SECONDS:  int  = 30

    # ── Worker rate limiting ────────────────────────────────────────────
    # Set WORKER_RATE_LIMIT_RPM to 0 to use the tier-aware default
    # (dev=10, enterprise=60).  Override explicitly for fine control.
    WORKER_RATE_LIMIT_RPM:   int   = 0
    WORKER_MIN_JOB_DELAY:    float = -1.0   # -1 = use tier default
    WORKER_BACKOFF_INITIAL:  float = 5.0
    WORKER_BACKOFF_MAX:      float = 120.0

    # ── Derived helpers ──────────────────────────────────────────────────
    @property
    def is_enterprise(self) -> bool:
        """Return True when running against Vertex AI (enterprise tier)."""
        return self.GEMINI_TIER.lower() == "enterprise"

    @property
    def effective_rpm(self) -> int:
        """Jobs-per-minute cap for the background worker.

        Uses explicit WORKER_RATE_LIMIT_RPM when set (non-zero), otherwise
        falls back to a sensible default per Gemini tier:

        - dev        → 10 RPM  (conservative for free-tier quotas)
        - enterprise → 60 RPM  (safe starting point; raise once confirmed)
        """
        if self.WORKER_RATE_LIMIT_RPM > 0:
            return self.WORKER_RATE_LIMIT_RPM
        return 60 if self.is_enterprise else 10

    @property
    def effective_min_job_delay(self) -> float:
        """Minimum pause between jobs, defaulting per tier if not set."""
        if self.WORKER_MIN_JOB_DELAY >= 0:
            return self.WORKER_MIN_JOB_DELAY
        return 0.2 if self.is_enterprise else 2.0

    @property
    def database_configured(self) -> bool:
        """Return True when a non-default DATABASE_URL is set."""
        return bool(self.DATABASE_URL) and "localhost" in self.DATABASE_URL

    @property
    def gemini_configured(self) -> bool:
        """Return True when Gemini credentials are available."""
        if self.is_enterprise:
            return bool(self.GEMINI_VERTEX_PROJECT)
        return bool(self.GEMINI_API_KEY) and self.GEMINI_API_KEY != "your_gemini_api_key_here"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()
