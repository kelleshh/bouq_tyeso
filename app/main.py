from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Request, status
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties


from .config import settings
from .alerts_service import validate_and_parse_payload, send_grouped_alerts_to_telegram
from pydantic import ValidationError


@asynccontextmanager
async def lifespan(app: FastAPI):
    # инициализируем бота один раз на всё приложение
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    app.state.bot = bot
    try:
        yield
    finally:
        await bot.session.close()



app = FastAPI(title="Уведомлятор", lifespan=lifespan)


def get_bot(request: Request) -> Bot:
    bot: Bot = request.app.state.bot
    return bot


@app.get("/health")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/alerts")
async def receive_alerts(
    request: Request,
    bot: Bot = Depends(get_bot),
):
    
        # LOG RAW BODY
    body = await request.body()
    print("=== RAW ALERTS PAYLOAD ===")
    print(body.decode('utf-8'))
    print("=== END PAYLOAD ===")

    
    # 1. Проверяем shared secret
    token = request.headers.get("X-Alerts-Token")
    if token != settings.alerts_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid alerts token",
        )

    # 2. Читаем JSON
    try:
        payload: Any = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        )

    # 3. Пустой массив — без ошибок, без сообщений
    if payload == []:
        return {"status": "ok", "alerts_count": 0}

    # 4. Pydantic-валидация
    try:
        alerts = validate_and_parse_payload(payload)
    except ValidationError as e:
        # Вернём детальную инфу по ошибкам схемы
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.errors(),
        )

    if not alerts:
        return {"status": "ok", "alerts_count": 0}

    # 5. Отправка в Telegram
    try:
        sent = await send_grouped_alerts_to_telegram(bot, settings, alerts)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send alerts: {e}",
        )

    return {
        "status": "ok",
        "alerts_count": len(alerts),
        "messages_sent": [
            {"shop": shop, "message_id": msg_id} for shop, msg_id in sent
        ],
    }
