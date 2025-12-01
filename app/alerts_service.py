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

# deprecated ???
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
    Рассылает сообщения по магазинам и маркетплейсам.
    Если текст слишком длинный, режем на несколько сообщений.
    Возвращает список (shop, message_id) для отладки.
    """
    grouped = group_alerts_by_shop_and_marketplace(alerts)
    sent: List[Tuple[str, int]] = []

    for shop, mp_map in grouped.items():
        chat_id = settings.chat_map.get(shop)
        if chat_id is None:
            raise RuntimeError(f"No chat id configured for shop '{shop}'")

        # фиксированный порядок маркетплейсов
        marketplace_order = ["WB", "Ozon", "Ozon (Кластеры)"]
        extra_mps = sorted(set(mp_map.keys()) - set(marketplace_order))
        marketplace_order.extend(extra_mps)

        for mp in marketplace_order:
            mp_alerts = mp_map.get(mp, [])
            if not mp_alerts:
                continue

            display_name = _marketplace_display_name(mp)

            # сортируем для красоты
            mp_alerts_sorted = sorted(mp_alerts, key=lambda a: (a.days, a.article))

            # строим текст только для одного маркетплейса
            lines: list[str] = []
            lines.append(f'МАГАЗИН "{shop}"')
            lines.append("")
            lines.append(f"{display_name}:")
            for alert in mp_alerts_sorted:
                lines.append(_format_alert_line(alert))

            text = "\n".join(lines)
            if not text.strip():
                continue

            # если слишком длинно – режем
            chunks = split_text_for_telegram(text)
            for chunk in chunks:
                msg = await bot.send_message(chat_id, chunk)
                sent.append((shop, msg.message_id))

    return sent

