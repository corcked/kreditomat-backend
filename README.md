# Kreditomat Backend API

Сервис-агрегатор микрозаймов - серверная часть.

## Технологический стек

- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL с SQLAlchemy ORM 2.0.23
- **Cache**: Redis 5.0.1
- **Authentication**: JWT + Telegram Gateway
- **Migrations**: Alembic 1.12.1
- **Testing**: Pytest

## Основные возможности

- Авторизация через Telegram Gateway
- Расчет показателя долговой нагрузки (ПДН) с автокоррекцией
- Система скоринга пользователей
- Реферальная программа
- Интеграция с банками-партнерами
- API для управления заявками на микрозаймы

## Структура проекта

```
kreditomat-backend/
├── app/
│   ├── core/           # Конфигурация, JWT, Redis
│   ├── db/             # База данных
│   ├── models/         # SQLAlchemy модели
│   ├── schemas/        # Pydantic схемы
│   ├── services/       # Бизнес-логика
│   ├── api/            # API endpoints
│   │   └── v1/         # Версия 1 API
│   └── main.py         # Главный файл приложения
├── alembic/            # Миграции БД
├── scripts/            # Утилиты и скрипты
├── tests/              # Тесты
├── Dockerfile          # Docker конфигурация
├── pyproject.toml      # Зависимости и настройки
└── README.md           # Этот файл
```

## Установка и запуск

### Требования

- Python 3.12+
- PostgreSQL 15+
- Redis 7+

### Локальная разработка

1. Клонировать репозиторий:
```bash
git clone https://github.com/[your-username]/kreditomat-backend.git
cd kreditomat-backend
```

2. Создать виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. Установить зависимости:
```bash
pip install -e .
```

4. Настроить переменные окружения:
```bash
cp .env.example .env
# Отредактировать .env файл
```

5. Применить миграции:
```bash
alembic upgrade head
```

6. Запустить сервер:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker build -t kreditomat-backend .
docker run -p 8000:8000 --env-file .env kreditomat-backend
```

## API Документация

После запуска сервера документация доступна по адресам:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Переменные окружения

- `DATABASE_URL` - URL подключения к PostgreSQL
- `REDIS_URL` - URL подключения к Redis
- `JWT_SECRET_KEY` - Секретный ключ для JWT токенов
- `TELEGRAM_GATEWAY_TOKEN` - Токен для Telegram Gateway
- `ENVIRONMENT` - Окружение (dev/prod)

## Тестирование

```bash
pytest tests/
```

## Deployment

Проект настроен для деплоя на Railway.app

## Лицензия

Proprietary