# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Команда `bot`
RUN printf '#!/bin/sh\nexec python -m app.cli "$@"\n' > /usr/local/bin/bot \
 && chmod +x /usr/local/bin/bot

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--access-log"]
