# Async Payment Processing Service

Асинхронный микросервис для обработки платежей с гарантированной доставкой событий через RabbitMQ и паттерн Outbox.

## Стек технологий
- **FastAPI** + Pydantic V2
- **SQLAlchemy 2.0** (асинхронный режим) + asyncpg
- **PostgreSQL**
- **RabbitMQ** (FastStream)
- **Alembic** (миграции)
- **Docker + docker-compose**
- **uv** (менеджер зависимостей)

## Функциональность
- Создание платежа с идемпотентностью (`Idempotency-Key`)
- Получение информации о платеже
- Асинхронная обработка через очередь `payments.new`
- Эмуляция обработки (2–5 сек, 90% успех)
- Отправка webhook-уведомления с retry (3 попытки, экспоненциальная задержка)
- Dead Letter Queue для необработанных сообщений
- Outbox pattern для гарантированной публикации событий

## Архитектура
1. **API (FastAPI)** принимает запросы, создаёт платёж и атомарно записывает событие в таблицу `outbox`.
2. **Outbox Poller** (фоновый процесс в consumer) читает pending-события из БД и публикует их в RabbitMQ.
3. **Consumer** (FastStream) обрабатывает сообщения: эмулирует платёж, обновляет статус, отправляет webhook.
4. При ошибках webhook выполняются повторные попытки; после исчерпания лимита сообщение уходит в DLQ.
5. Все компоненты разворачиваются через Docker Compose.

## Переменные окружения
Создайте файл `.env` на основе `.env.example`:

| Переменная | Назначение | Значение по умолчанию |
|------------|------------|------------------------|
| `API_KEY` | Статический ключ для доступа к API | `change_me` |
| `DATABASE_URL` | URL подключения к PostgreSQL | `postgresql+asyncpg://user:pass@localhost:5432/payments` |
| `RABBITMQ_URL` | URL подключения к RabbitMQ | `amqp://guest:guest@localhost:5672/` |
| `WEBHOOK_TIMEOUT` | Таймаут отправки webhook (сек) | `5` |

## Запуск

### 1. Клонирование репозитория
```bash
git clone https://github.com/Dexter2038/async-payment-processing-service.git
cd async-payment-processing-service
```

### 2. Запуск через Docker Compose
```bash
docker compose up -d
```
Будут запущены:
- PostgreSQL (порт 5432)
- RabbitMQ (порт 5672 + management UI на 15672)
- API (порт 8000)
- Consumer

Миграции применяются автоматически при старте API.

### 3. Ручное применение миграций (если потребуется)
```bash
docker compose exec api uv run alembic upgrade head
```

## Примеры использования API

### Аутентификация
Все эндпоинты (кроме `/health`) требуют заголовок `X-API-Key: ваш-ключ`.

### Создание платежа
```bash
curl -X POST "http://localhost:8000/api/v1/payments" \
  -H "X-API-Key: dev-api-key" \
  -H "Idempotency-Key: test-key-001" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "100.00",
    "currency": "USD",
    "description": "Тестовый платёж",
    "metadata": {"order_id": "12345"},
    "webhook_url": "https://webhook.site/your-uuid"
  }'
```
**Ответ (202 Accepted):**
```json
{
  "payment_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "pending",
  "created_at": "2024-12-20T12:00:00Z"
}
```

### Получение информации о платеже
```bash
curl "http://localhost:8000/api/v1/payments/f47ac10b-58cc-4372-a567-0e02b2c3d479" \
  -H "X-API-Key: dev-api-key"
```
**Ответ (200 OK):**
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "amount": "100.00",
  "currency": "USD",
  "description": "Тестовый платёж",
  "metadata": {"order_id": "12345"},
  "status": "succeeded",
  "idempotency_key": "test-key-001",
  "webhook_url": "https://webhook.site/your-uuid",
  "created_at": "2024-12-20T12:00:00Z",
  "processed_at": "2024-12-20T12:00:04Z"
}
```

## Мониторинг
- RabbitMQ Management UI: http://localhost:15672 (guest/guest)
- Swagger документация API: http://localhost:8000/docs
- Healthcheck: http://localhost:8000/health

## Тестирование
```bash
# Запуск всех тестов
uv run pytest

# Только модульные тесты
uv run pytest tests/test_models.py tests/test_schemas.py

# Интеграционные тесты (требуют запущенных сервисов)
uv run pytest tests/test_payment_api.py tests/test_outbox_publisher.py
```
