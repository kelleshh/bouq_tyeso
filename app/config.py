import os
from dataclasses import dataclass


@dataclass
class Settings:
    bot_token: str
    alerts_token: str
    tyeso_chat_id: int
    bouq_chat_id: int

    @property
    def chat_map(self) -> dict[str, int]:
        return {
            "Tyeso": self.tyeso_chat_id,
            "BOUQ": self.bouq_chat_id,
        }


def _must_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def load_settings() -> Settings:
    bot_token = _must_env("BOT_TOKEN")
    alerts_token = _must_env("ALERTS_TOKEN")

    try:
        tyeso_chat_id = int(_must_env("TYESO_CHAT_ID"))
        bouq_chat_id = int(_must_env("BOUQ_CHAT_ID"))
    except ValueError as e:
        raise RuntimeError("Chat IDs must be integers") from e

    return Settings(
        bot_token=bot_token,
        alerts_token=alerts_token,
        tyeso_chat_id=tyeso_chat_id,
        bouq_chat_id=bouq_chat_id,
    )


settings = load_settings()
