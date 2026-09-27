from pathlib import Path

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"


def _env_encoding(path: Path) -> str:
    """PowerShell 5.1 (`echo ... > .env`) writes UTF-16 with a BOM; editors usually write UTF-8."""
    try:
        head = path.read_bytes()[:2]
    except OSError:
        return "utf-8"
    return "utf-16" if head in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding=_env_encoding(ENV_FILE), extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # backend/.env beats the process environment: the project's own file must win over a stale
        # machine-wide variable (e.g. an old ANTHROPIC_API_KEY). Without a .env (production), the
        # environment is used as usual.
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    # Postgres in docker-compose; SQLite fallback for quick local dev.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'trends.db').as_posix()}"

    # LLM: provider-agnostic interface, Anthropic implementation by default.
    llm_provider: str = "anthropic"
    # Put ANTHROPIC_API_KEY=sk-ant-... in backend/.env (git-ignored). When set here it is passed to the
    # client explicitly, so a stray ANTHROPIC_API_KEY in the process environment cannot override it.
    anthropic_api_key: str | None = None
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
    max_extract_per_run: int = 500  # articles Claude analyses per run (cost guard; ~$0.01 each on Sonnet 5)

    # Frontend origin for CORS
    frontend_origin: str = "http://localhost:3000"


settings = Settings()
