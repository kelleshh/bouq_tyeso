from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

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
<<<<<<< HEAD
    Валидация входа через Pydantic AlertsPayload
    и конвертация в список Alert.
=======
    Валидируем вход через Pydantic AlertsPayload
    и конвертируем в список Alert.
>>>>>>> ae9b6ce (refactor(alerts): send per-marketplace reports and improve Russian day pluralization)
    """
    try:
        parsed = AlertsPayload.model_validate(payload)
    except ValidationError:
        # пусть FastAPI уже превратит это в 400
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
         "Ozon (Кластеры)": [...],
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


def _days_word_ru(n: int) -> str:
    """
    Морфология для 'день/дня/дней'.
    """
    n_abs = abs(n)
    last_two = n_abs % 100
    last = n_abs % 10

    if 11 <= last_two <= 14:
        return "дней"
    if last == 1:
        return "день"
    if last in (2, 3, 4):
        return "дня"
    return "дней"


def _marketplace_block_title(mp: str) -> str:
    """
    Заголовок блока для маркетплейса.
    """
    if mp == "Ozon":
        return "Остатки Ozon (склады):\n"
    if mp == "Ozon (Кластеры)":
        return "Остатки Ozon (кластеры):\n"
    if mp == "WB":
        return "Остатки ВБ (склады):\n"
    return f"Остатки {mp}:"


<<<<<<< HEAD
def build_message_for_shop(shop: str, mp_map: Dict[str, List[Alert]]) -> str:
    """
    Собираем итоговый текст для одного магазина в виде:

    МАГАЗИН "Tyeso"

    Остатки Ozon (склады/кластеры):

    ❗️<b>VacuumCupMilk</b>
    СОФЬИНО <b>0 дней</b>
    ГРИВНО <b>5 дней</b>
    ...
=======
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
    Собираем текст для одного магазина и одного маркетплейса.
>>>>>>> ae9b6ce (refactor(alerts): send per-marketplace reports and improve Russian day pluralization)
    """
    if not alerts:
        return ""

    lines: List[str] = []
    lines.append(f'МАГАЗИН "{shop}"')
    lines.append("")

<<<<<<< HEAD
    # Фиксированный порядок маркетплейсов
    marketplace_order = ["WB", "Ozon", "Ozon (Кластеры)"]
    extra_mps = sorted(set(mp_map.keys()) - set(marketplace_order))
    marketplace_order.extend(extra_mps)

    for mp in marketplace_order:
        mp_alerts = mp_map.get(mp, [])
        if not mp_alerts:
            continue

        # заголовок блока маркетплейса
        lines.append(_marketplace_block_title(mp))

        # сортируем и группируем по артикулу
        mp_alerts_sorted = sorted(
            mp_alerts,
            key=lambda a: (a.article, a.location, a.days),
        )
        article_map: Dict[str, List[Alert]] = {}
        for alert in mp_alerts_sorted:
            article_map.setdefault(alert.article, []).append(alert)

        # проходим по артикулам в алфавитном порядке
        for article in sorted(article_map.keys()):
            article_alerts = article_map[article]

            # строка с артикулом
            lines.append(f'❗️<b>{article}</b>')

            # склады/кластеры по возрастанию дней, потом по названию
            for alert in sorted(article_alerts, key=lambda a: (a.days, a.location)):
                location_caps = alert.location.upper()
                word = _days_word_ru(alert.days)
                lines.append(f"{location_caps} <b>{alert.days} {word}</b>")

            lines.append("")  # пустая строка между артикулами

        lines.append("")  # пустая строка между маркетплейсами

    # убираем возможный лишний \n в конце
    while lines and lines[-1] == "":
        lines.pop()
=======
    display_name = _marketplace_display_name(marketplace)
    lines.append(f"{display_name}:")  # например, "ВБ:" или "Ozon:" и т.п.

    # сортируем по дням, потом по артикулу, чтобы не было хаоса
    alerts_sorted = sorted(alerts, key=lambda a: (a.days, a.article))

    for alert in alerts_sorted:
        lines.append(_format_alert_line(alert))
>>>>>>> ae9b6ce (refactor(alerts): send per-marketplace reports and improve Russian day pluralization)

    return "\n".join(lines)


async def send_grouped_alerts_to_telegram(
    bot: Bot,
    settings: Settings,
    alerts: List[Alert],
) -> List[Tuple[str, int]]:
    """
<<<<<<< HEAD
    Рассылает сообщения по магазинам.
    Для каждого shop формируем один большой текст (по всем маркетплейсам)
    и при необходимости режем его на части под лимит Telegram.
=======
    Рассылает сообщения по магазинам и маркетплейсам.
    ВАЖНО: для каждого (shop, marketplace) формируется ОТДЕЛЬНОЕ сообщение.
    Если оно слишком длинное, режем его на несколько кусков, чтобы Телега не упала.
    Возвращает список (shop, message_id) для отладки.
>>>>>>> ae9b6ce (refactor(alerts): send per-marketplace reports and improve Russian day pluralization)
    """
    grouped = group_alerts_by_shop_and_marketplace(alerts)
    sent: List[Tuple[str, int]] = []

    for shop, mp_map in grouped.items():
        chat_id = settings.chat_map.get(shop)
        if chat_id is None:
            # Конфигурация сломана, это уже ошибка разработчика
            raise RuntimeError(f"No chat id configured for shop '{shop}'")

<<<<<<< HEAD
        text = build_message_for_shop(shop, mp_map)
        if not text.strip():
            continue

        chunks = split_text_for_telegram(text)
        for chunk in chunks:
            msg = await bot.send_message(chat_id, chunk)
            sent.append((shop, msg.message_id))
=======
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
>>>>>>> ae9b6ce (refactor(alerts): send per-marketplace reports and improve Russian day pluralization)

    return sent
