# Используем официальный образ Python 3.12
FROM python:3.12-slim

# Устанавливаем uv (быстрый менеджер пакетов)
RUN pip install --no-cache-dir uv

# Задаём рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей и лок-файл
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости (без dev-пакетов)
RUN uv sync --frozen --no-dev

# Копируем код приложения
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

# Создаём виртуальное окружение и добавляем uv в PATH (опционально)
ENV PATH="/app/.venv/bin:$PATH"

# По умолчанию запускаем API сервер (consumer будет переопределён в docker-compose)
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
