from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Iterable, Tuple

from aiogram import Bot
from pydantic import ValidationError

from .config import Settings
from .models import AlertsPayload
from .text_split import split_text_for_telegram


@dataclass
class Alert:
    shop: str               # "Tyeso" или "Bouq"
    marketplace: str        # "WB", "Ozon", "Ozon (Кластеры)"
    location: str           # склад или кластер
    article: str            # артикул
    days: int               # дни до исчерпания


def validate_and_parse_payload(payload: Any) -> List[Alert]:
    """
    Валидируем вход через Pydantic AlertsPayload
    и конвертируем в список Alert.
    """
    try:
        parsed = AlertsPayload.model_validate(payload)
    except ValidationError:
        # пробрасываем дальше, пусть FastAPI уже превращает в 400
        raise

    alerts: List[Alert] = []
    for item in parsed.root:
        alerts.append(
            Alert(
                shop=item.shop,
                marketplace=item.marketplace,
                location=item.location,
                article=item.article,
                days=item.days,
            )
        )
    return alerts


def group_alerts_by_shop_and_marketplace(
    alerts: Iterable[Alert],
) -> Dict[str, Dict[str, List[Alert]]]:
    """
    Группируем в структуру:
    {
      "Tyeso": {
         "WB": [Alert, ...],
         "Ozon": [...],
         ...
      },
      "Bouq": { ... }
    }
    """
    result: Dict[str, Dict[str, List[Alert]]] = {}
    for alert in alerts:
        shop_map = result.setdefault(alert.shop, {})
        mp_list = shop_map.setdefault(alert.marketplace, [])
        mp_list.append(alert)
    return result


def _marketplace_display_name(mp: str) -> str:
    if mp == "WB":
        return "ВБ"
    return mp


def _plural_days_ru(n: int) -> str:
    """
    Склонение "день/дня/дней".
    """
    n_abs = abs(n) % 100
    n1 = n_abs % 10
    if 11 <= n_abs <= 14:
        return "дней"
    if n1 == 1:
        return "день"
    if 2 <= n1 <= 4:
        return "дня"
    return "дней"


def _format_alert_line(alert: Alert) -> str:
    """
    Одна строка с остатком.
    """
    days_word = _plural_days_ru(alert.days)

    if alert.marketplace == "Ozon (Кластеры)":
        return (
            f"товара {alert.article} в кластере {alert.location} "
            f"осталось на {alert.days} {days_word}"
        )
    else:
        return (
            f"товара {alert.article} на складе {alert.location} "
            f"осталось на {alert.days} {days_word}"
        )


def _build_message_for_shop_and_marketplace(
    shop: str,
    marketplace: str,
    alerts: List[Alert],
) -> str:
    """
    Собираем текст ТОЛЬКО для одного магазина и одного маркетплейса.
    Это и есть "одно сообщение на WB / Ozon / Ozon (Кластеры)".
    """
    if not alerts:
        return ""

    lines: List[str] = []
    lines.append(f'МАГАЗИН "{shop}"')
    lines.append("")

    display_name = _marketplace_display_name(marketplace)
    lines.append(f"{display_name}:")  # например, "ВБ:" или "Ozon:" и т.п.

    # сортируем по дням, потом по артикулу, чтобы не было хаоса
    alerts_sorted = sorted(alerts, key=lambda a: (a.days, a.article))

    for alert in alerts_sorted:
        lines.append(_format_alert_line(alert))

    return "\n".join(lines)


async def send_grouped_alerts_to_telegram(
    bot: Bot,
    settings: Settings,
    alerts: List[Alert],
) -> List[Tuple[str, int]]:
    """
    Рассылает сообщения по магазинам и маркетплейсам.
    ВАЖНО: для каждого (shop, marketplace) формируется ОТДЕЛЬНОЕ сообщение.
    Если оно слишком длинное, режем его на несколько кусков, чтобы Телега не упала.
    Возвращает список (shop, message_id) для отладки.
    """
    grouped = group_alerts_by_shop_and_marketplace(alerts)
    sent: List[Tuple[str, int]] = []

    for shop, mp_map in grouped.items():
        chat_id = settings.chat_map.get(shop)
        if chat_id is None:
            # Конфигурация сломана, это уже ошибка разработчика
            raise RuntimeError(f"No chat id configured for shop '{shop}'")

        # фиксированный порядок маркетов, затем любые неожиданные
        base_order = ["WB", "Ozon", "Ozon (Кластеры)"]
        extra_mps = sorted(set(mp_map.keys()) - set(base_order))
        marketplace_order = [mp for mp in base_order if mp in mp_map]
        marketplace_order.extend(extra_mps)

        for mp in marketplace_order:
            mp_alerts = mp_map.get(mp, [])
            if not mp_alerts:
                continue

            text = _build_message_for_shop_and_marketplace(shop, mp, mp_alerts)
            if not text.strip():
                continue

            # если слишком длинно – режем, но В РАМКАХ одного маркетплейса
            chunks = split_text_for_telegram(text)
            for chunk in chunks:
                msg = await bot.send_message(chat_id, chunk)
                sent.append((shop, msg.message_id))

    return sent
