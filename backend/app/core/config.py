import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class LongCatConfigurationError(RuntimeError):
    """Raised when the real model integration is not configured."""


@dataclass(frozen=True)
class LongCatSettings:
    api_key: str
    base_url: str
    model: str


def get_cors_origins() -> list[str]:
    configured_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]


def get_longcat_settings() -> LongCatSettings:
    api_key = os.getenv("LONGCAT_API_KEY", "").strip()
    if not api_key or api_key == "replace-with-your-local-api-key":
        raise LongCatConfigurationError(
            "LONGCAT_API_KEY is not configured. Add it to backend/.env before sending chat messages."
        )

    return LongCatSettings(
        api_key=api_key,
        base_url=os.getenv("LONGCAT_BASE_URL", "https://api.longcat.chat/openai"),
        model=os.getenv("LONGCAT_MODEL", "LongCat-2.0"),
    )
