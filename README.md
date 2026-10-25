# AI-тренажёр для абитуриента и стажёра

Универсальный AI-тренажёр с двумя режимами: информационный поиск по базе знаний и тренажёр-экзаменатор с экспертной обратной связью, адаптивным подбором кейсов и экспортом отчёта в PDF.

## 🛠 Стек

* **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async)
* **БД:** SQLite (dev) → Postgres + pgvector (prod)
* **LLM:** Абстракция `LLMGateway` (Circuit Breaker, кэш, fallback, cost control)
* **RAG:** Chunking + hashing-эмбеддинги (заменяются на реальный провайдер одной строкой)
* **Безопасность (Guardrails):** PII-маскирование, обязательный дисклеймер
* **Наблюдаемость:** Prometheus, JSON-логи, W3C traceparent
* **Frontend:** Streamlit
* **Тесты:** 45+ unit-тестов

## 🚀 Быстрый старт (локально, без Docker)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

cp .env.example .env
# В .env убедиться: DATABASE_URL=sqlite+aiosqlite:///./mentor.db

alembic upgrade head
python -m scripts.ingest

# Запуск бэкенда
uvicorn app.main:app --reload

# Запуск фронтенда (во втором терминале)
streamlit run frontend/app.py
```

**Доступные адреса:**
* API-доки: [http://localhost:8000/docs](http://localhost:8000/docs)
* Метрики: [http://localhost:8000/metrics](http://localhost:8000/metrics)
* Фронтенд: [http://localhost:8501](http://localhost:8501)

## 🐳 Запуск через Docker

```bash
docker compose up --build
```

## 🧪 Тесты

```bash
pytest -q
```

## 🔌 Эндпоинты

| Метод | Путь | Назначение |
|-------|------|------------|
| `GET` | `/api/health/live` | Liveness-проба |
| `GET` | `/api/health/ready` | Readiness-проба (проверка БД) |
| `GET` | `/api/scenarios` | Список активных сценариев |
| `POST` | `/api/rag/search` | Поиск по базе знаний с citations |
| `POST` | `/api/dialog/sessions` | Создать сессию (info/trainer) |
| `POST` | `/api/dialog/sessions/{id}/messages` | Отправить сообщение |
| `GET` | `/api/dialog/sessions/{id}/export.pdf` | Экспорт отчёта в PDF |
| `GET` | `/metrics` | Prometheus-метрики |

## 🏗 Ключевые архитектурные решения

* **PII маскируется до сохранения в БД и до отправки в LLM** — принцип минимизации ПДн «по умолчанию».
* **LLM за абстракцией** — смена провайдера (YandexGPT, GigaChat, локальная модель) без изменений в бизнес-логике.
* **Circuit Breaker + fallback на правила** — при отказе LLM диалог не падает, а отвечает по шаблону.
* **Адаптивность (Lead)** — ошибки пользователя записываются в `WeakZone`, приоритизация следующих кейсов по слабым зонам.
* **Экспорт PDF** — диалог + вердикты + слабые зоны + дисклеймер, чтобы можно было вернуться к советам перед реальным собеседованием.

## ⚖️ Этика
* Только открытые источники, у каждого ответа RAG есть citations.
* Дисклеймер добавляется в каждый ответ наставника.
* Голосовые данные не сохраняются (текстовый режим по умолчанию).
* Минимизация ПДн: PII маскируется, `anonymous_id` не связан с личностью.