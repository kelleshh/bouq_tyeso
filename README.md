
# MP Alerts Bot

Сервис принимает алерты из Google Apps Script и отправляет сгруппированные сообщения в Telegram по магазинам и маркетплейсам.

## Формат входных данных

HTTP `POST /alerts`

Заголовок:
- `X-Alerts-Token: <секрет>`

Тело запроса (JSON):

```json
[
  ["Магазин1", "Ozon", "ПУШКИНО", "SomeAnyArticle1", 3],
  ["Магазин2", "WB", "КРАСНОДАР", "SomeArticle2", 2]
]
```

Каждый элемент массива:
- `shop` — магазин
- `marketplace` — `"WB"`, `"Ozon"`, `"Ozon (Кластеры)"`
- `location` — склад или кластер (строка)
- `article` — артикул (строка)
- `days` — дни до исчерпания (целое число, `>= 0`)

Пустой массив `[]` считается валидным и просто игнорируется.

## Переменные окружения

Бот настраивается через переменные окружения (например, в `.env`):

```bash
BOT_TOKEN=123456:telegram-bot-token
ALERTS_TOKEN=custom-secret-token-like-in-scheduler-gs-in-google-sheets

TYESO_CHAT_ID=111111111
BOUQ_CHAT_ID=222222222
```

- `BOT_TOKEN` — токен Telegram-бота
- `ALERTS_TOKEN` — shared secret для защиты эндпоинта `/alerts`
- `TYESO_CHAT_ID` — chat id для магазина `Tyeso`
- `BOUQ_CHAT_ID` — chat id для магазина `Bouq`

## Запуск через Docker

### 1. Сборка образа

```bash
docker build -t mp-alerts-bot .
```

### 2. Запуск контейнера

Пример запуска с пробросом порта 80 на хост:

```bash
docker compose up -d --build
```

Теперь сервис доступен по адресу:

- `http://<IP_СЕРВЕРА>:8000/health` — проверка живости
- `http://<IP_СЕРВЕРА>:8000/alerts` — приём алертов (только `POST`)

### 3. Логи контейнера

```bash
docker logs -f mp-alerts-bot
```

## Пример docker-compose

```yaml
version: "3.9"

services:
  mp-alerts-bot:
    build: .
    container_name: mp-alerts-bot
    env_file:
      - .env
    ports:
      - "80:8000"
    restart: unless-stopped
```

Запуск:

```bash
docker compose up -d
```

## Настройка Google Apps Script

В скрипте для таблицы нужно указать эндпоинт и токен, совпадающий с `ALERTS_TOKEN`:

```js
const ALERTS_ENDPOINT = 'http://<IP_СЕРВЕРА>/alerts';
const ALERTS_TOKEN = 'custom-secret-token-like-in-scheduler-gs-in-google-sheets';
```

Отправка:

```js
const options = {
  method: 'post',
  contentType: 'application/json',
  payload: JSON.stringify(alerts || []),
  muteHttpExceptions: true,
  headers: {
    'X-Alerts-Token': ALERTS_TOKEN,
  },
};

const response = UrlFetchApp.fetch(ALERTS_ENDPOINT, options);
```

Рекомендуется использовать порт 80 или 443 (за reverse-proxy), чтобы не упираться в ограничения Google Apps Script по нестандартным портам.