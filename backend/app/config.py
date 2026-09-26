from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # Postgres in docker-compose; SQLite fallback for quick local dev.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'trends.db').as_posix()}"

    # LLM: provider-agnostic interface, Anthropic implementation by default.
    llm_provider: str = "anthropic"
    extraction_model: str = "claude-sonnet-5"
    summary_model: str = "claude-sonnet-5"
    extraction_effort: str = "low"  # low | medium | high — extraction is a routine task
    prompt_version: str = "v1"

    # Market: Google Trends / news geo. Retailer country is still an open decision.
    market_geo: str = "FR"

    # Collection
    request_timeout: float = 20.0
    user_agent: str = "EyewearTrendsBot/0.1 (+internal retail trend monitoring)"
    max_articles_per_run: int = 60

    # Frontend origin for CORS
    frontend_origin: str = "http://localhost:3000"


settings = Settings()
