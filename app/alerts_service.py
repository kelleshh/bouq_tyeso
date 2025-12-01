from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Iterable, Tuple

from aiogram import Bot
from pydantic import ValidationError

from .config import Settings
from .models import AlertsPayload


@dataclass
class Alert:
    shop: str               # "Tyeso" или "Bouq"
    marketplace: str        # "WB", "Ozon", "Ozon (Кластеры)"
    location: str           # склад или кластер
    article: str            # артикул
    days: int               # дни до исчерпания


def validate_and_parse_payload(payload: Any) -> List[Alert]:
    """
    Завалидационим вход через Pydantic AlertsPayload
    и конвертнём в Alert.
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


def _format_alert_line(alert: Alert) -> str:
    if alert.marketplace == "Ozon (Кластеры)":
        return (
            f"товара {alert.article} в кластере {alert.location} "
            f"осталось на {alert.days} дней"
        )
    else:
        return (
            f"товара {alert.article} на складе {alert.location} "
            f"осталось на {alert.days} дней"
        )


def build_message_for_shop(shop: str, mp_map: Dict[str, List[Alert]]) -> str:
    """
    Собираем итоговый текст для одного магазина.
    """

    lines: List[str] = []
    lines.append(f'МАГАЗИН "{shop}"')
    lines.append("")

    # Фиксированный порядок, чтобы не прыгало
    marketplace_order = ["WB", "Ozon", "Ozon (Кластеры)"]
    # добавляем неожиданное, если вдруг появится
    for mp in sorted(set(mp_map.keys()) - set(marketplace_order)):
        marketplace_order.append(mp)

    for mp in marketplace_order:
        alerts = mp_map.get(mp, [])
        if not alerts:
            # Если хочешь вообще не писать маркетплейсы без проблем - можно пропустить этот блок
            continue

        display_name = _marketplace_display_name(mp)
        lines.append(f"{display_name}:")
        # сортируем по дням, потом по артикулу чисто для красоты
        alerts_sorted = sorted(alerts, key=lambda a: (a.days, a.article))

        for alert in alerts_sorted:
            lines.append(_format_alert_line(alert))
        lines.append("")  # пустая строка между разделами

    # убираем возможный лишний \n в конце
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


async def send_grouped_alerts_to_telegram(
    bot: Bot,
    settings: Settings,
    alerts: List[Alert],
) -> List[Tuple[str, int]]:
    """
    Рассылает сообщения по магазинам.
    Возвращает список (shop, message_id) для отладки.
    """
    grouped = group_alerts_by_shop_and_marketplace(alerts)
    sent: List[Tuple[str, int]] = []

    for shop, mp_map in grouped.items():
        chat_id = settings.chat_map.get(shop)
        if chat_id is None:
            # Конфигурация сломана, это уже ошибка разработчика
            raise RuntimeError(f"No chat id configured for shop '{shop}'")

        text = build_message_for_shop(shop, mp_map)
        if not text.strip():
            # Нечего слать
            continue

        msg = await bot.send_message(chat_id, text)
        sent.append((shop, msg.message_id))

    return sent
