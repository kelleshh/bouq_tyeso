from __future__ import annotations

import os
import re
from getpass import getpass
from pathlib import Path
from typing import Dict, List, Tuple

import typer

app = typer.Typer(add_completion=False)

@app.callback()
def main() -> None:
    """MP alerts bot CLI."""
    return


DEFAULT_ENV_PATH = Path.cwd() / ".env"
KEY_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")


def _load_env_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines(True)  # keep \n


def _upsert_env(lines: List[str], updates: Dict[str, str], chat_comment: str) -> List[str]:
    found = set()
    out: List[str] = []

    for line in lines:
        m = KEY_RE.match(line)
        if not m:
            out.append(line)
            continue

        key = m.group(1)
        if key not in updates:
            out.append(line)
            continue

        found.add(key)

        if key in ("TYESO_CHAT_ID", "BOUQ_CHAT_ID"):
            out.append(f"{key}={updates[key]} {chat_comment}\n")
        else:
            out.append(f"{key}={updates[key]}\n")

    def ensure_line(key: str, value: str, with_comment: bool = False) -> None:
        if key in found:
            return
        if out and not out[-1].endswith("\n"):
            out[-1] += "\n"
        if out and out[-1].strip() != "":
            out.append("\n")
        if with_comment:
            out.append(f"{key}={value} {chat_comment}\n")
        else:
            out.append(f"{key}={value}\n")

    ensure_line("BOT_TOKEN", updates["BOT_TOKEN"])
    ensure_line("ALERTS_TOKEN", updates["ALERTS_TOKEN"])
    ensure_line("TYESO_CHAT_ID", updates["TYESO_CHAT_ID"], with_comment=True)
    ensure_line("BOUQ_CHAT_ID", updates["BOUQ_CHAT_ID"], with_comment=True)

    return out


def _read_current_value(lines: List[str], key: str) -> str:
    for line in lines:
        if not KEY_RE.match(line):
            continue
        if line.lstrip().startswith(key + "="):
            left = line.split("=", 1)[1].strip()
            if " #" in left:
                left = left.split(" #", 1)[0].strip()
            elif "\t#" in left:
                left = left.split("#", 1)[0].strip()
            return left
    return ""


@app.command()
def configure(
    env_path: Path = typer.Option(DEFAULT_ENV_PATH, "--env", "-e", help="Путь до .env (по умолчанию ./.env)"),
) -> None:
    lines = _load_env_lines(env_path)

    typer.echo("Настройка .env. Можно жать Enter, чтобы оставить старое значение (если оно уже было).")

    cur_bot = _read_current_value(lines, "BOT_TOKEN")
    cur_alerts = _read_current_value(lines, "ALERTS_TOKEN")
    cur_chat = _read_current_value(lines, "TYESO_CHAT_ID") or _read_current_value(lines, "BOUQ_CHAT_ID")

    bot_token = getpass("BOT_TOKEN (вставьте токен из Telegram BotFather): ").strip() or cur_bot
    alerts_token = getpass("ALERTS_TOKEN (должен быть идентичен токену в AppScript Google Sheets): ").strip() or cur_alerts
    chat_id = input("CHAT_ID (айди чата/профиля, куда слать уведомления): ").strip() or cur_chat

    if not bot_token or not alerts_token or not chat_id:
        typer.secho("Не хватает значений. BOT_TOKEN, ALERTS_TOKEN и CHAT_ID должны быть заполнены.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not re.fullmatch(r"-?\d+", chat_id):
        typer.secho("CHAT_ID должен быть числом (например 926295513).", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    chat_comment = "# профиль куда слать уведомления владельцу магазина"

    updates = {
        "BOT_TOKEN": bot_token,
        "ALERTS_TOKEN": alerts_token,
        "TYESO_CHAT_ID": chat_id,
        "BOUQ_CHAT_ID": chat_id,
    }

    new_lines = _upsert_env(lines, updates, chat_comment)

    env_path.write_text("".join(new_lines), encoding="utf-8")

    try:
        os.chmod(env_path, 0o600)
    except Exception:
        pass

    typer.secho(f"Готово. Обновлен файл: {env_path}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
