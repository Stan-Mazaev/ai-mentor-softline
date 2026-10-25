# Архитектура

## Общая схема

```text
┌──────────────┐       ┌──────────────────────────────────────────────────┐
│  Streamlit   │──────▶│ FastAPI (app/)                                   │
│   frontend   │       │                                                  │
└──────────────┘       │  ┌────────────┐  ┌────────────┐  ┌─────────────┐ │
                       │  │  /dialog   │  │    /rag    │  │ /scenarios  │ │
                       │  └─────┬──────┘  └─────┬──────┘  └─────────────┘ │
                       │        │               │                         │
                       │        ▼               ▼                         │
                       │  ┌──────────────────────────────┐                │
                       │  │         DialogService        │                │
                       │  │ ┌──────────┐  ┌──────────┐   │                │
                       │  │ │evaluator │  │ machine  │   │                │
                       │  │ └──────────┘  └──────────┘   │                │
                       │  │ ┌──────────┐  ┌──────────┐   │                │
                       │  │ │adaptivity│  │   PDF    │   │                │
                       │  │ └──────────┘  └──────────┘   │                │
                       │  └────────┬─────────────────────┘                │
                       │           │                                      │
                       │  ┌────────▼───────┐      ┌───────────────────────┐│
                       │  │   RagService   │      │      Guardrails       ││
                       │  │   chunking     │      │      PII-masking      ││
                       │  │   embeddings   │      │      disclaimer       ││
                       │  │   retrieval    │      └───────────────────────┘│
                       │  └────────┬───────┘                               │
                       │           │                                      │
                       │  ┌────────▼───────┐      ┌───────────────────────┐│
                       │  │   LLMGateway   │      │     Observability     ││
                       │  │     cache      │      │      Prometheus       ││
                       │  │    circuit     │      │       JSON logs       ││
                       │  │    fallback    │      │      traceparent      ││
                       │  └────────┬───────┘      └───────────────────────┘│
                       └───────────┼──────────────────────────────────────┘
                                   │
                       ┌───────────▼───────────┐
                       │      LLMProvider      │
                       │  Stub / Yandex / GG   │
                       └───────────┬───────────┘
                                   │
                       ┌───────────▼───────────┐
                       │ DB: SQLite → Postgres │
                       │    pgvector (prod)    │
                       └───────────────────────┘
```

## Слои

### API (`app/api/`)
* `health.py` — liveness/readiness.
* `scenarios.py` — список активных сценариев.
* `rag.py` — поиск по базе знаний с citations.
* `dialog.py` — создание сессии, сообщения, PDF-экспорт.

### Dialog (`app/dialog/`)
* `states.py` — режимы (`info`/`trainer`) и состояния (`idle`/`info_ready`/`awaiting_answer`/`finished`).
* `machine.py` — детерминированные переходы между состояниями.
* `cases.py` — загрузка кейсов из `knowledge_base/<scenario>/cases.json`.
* `evaluator.py` — оценка ответа: `verdict`, `mistakes`, `improvements`, `exemplar`, `score`.
* `adaptivity.py` — запись `WeakZone` и приоритизация кейсов.
* `service.py` — оркестрация: PII → state machine → ветка (info/trainer) → сохранение turn → ответ.

### RAG (`app/rag/`)
* `chunking.py` — разбиение текста на чанки с перекрытием.
* `embeddings.py` — `EmbeddingProvider` Protocol + `HashingEmbeddingProvider` (dev).
* `retrieval.py` — cosine top-K (в проде → pgvector).
* `service.py` — ingestion + retrieve.

### LLM (`app/llm/`)
* `base.py` — `LLMProvider` Protocol, `LLMRequest`/`LLMResponse`.
* `stub.py` — детерминированный провайдер для локальной работы и тестов.
* `cache.py` — TTL-кэш.
* `circuit_breaker.py` — Circuit Breaker с состояниями `closed`/`open`/`half_open`.
* `gateway.py` — обёртка: cache + breaker + fallback + метрики.
* `factory.py` — точка подключения реального провайдера.

### Guardrails (`app/guardrails/`)
* `pii.py` — маскирование email, телефонов, ФИО, школ, классов.
* `disclaimer.py` — единый текст и хелпер для добавления к ответам.

### Export (`app/export/`)
* `pdf.py` — отчёт: сценарий, режим, слабые зоны, диалог, вердикты, citations, дисклеймер.

### Observability (`app/observability/`)
* `metrics.py` — Prometheus-счётчики и гистограммы LLM.

## Потоки данных

### Trainer
1. Клиент создаёт сессию → `POST /api/dialog/sessions`.
2. `DialogService.create_session` → загружает `cases.json`, приоритизирует по слабым зонам, создаёт `DialogSession`.
3. Клиент отправляет ответ → `POST /api/dialog/sessions/{id}/messages`.
4. `DialogService.post_message` → `mask_pii(content)` → сохранение turn → `_handle_trainer`.
5. `evaluate_answer` сравнивает ответ с `expected_hints`/`typical_mistakes` → `Evaluation`.
6. Если вердикт ≠ good и есть профиль → `record_weak_zone`.
7. В ответе — `evaluation`, `content` (следующий кейс или финал), `disclaimer`.

### Info
1. Создание сессии → greeting.
2. Ответ пользователя → `mask_pii` → сохранение.
3. `RagService.retrieve` → top-K чанков.
4. `LLMGateway.generate(task="info")` → ответ с citations.
5. `with_disclaimer` → ответ с дисклеймером и ссылками.

## Безопасность, этика и отказоустойчивость
* PII маскируется до сохранения и до LLM — «минимизация по умолчанию».
* `anonymous_id` — UUID на клиенте, не связан с личностью.
* `CircuitBreaker` открывается после N ошибок LLM, через timeout → `half_open`.
* При открытом breaker — `StubLLMProvider` отвечает по шаблону.
* Кэш TTL снижает стоимость и latency повторных запросов.

## Масштабирование (prod)
* SQLite → Postgres + pgvector, `embedding` как `vector(384)`.
* `HashingEmbeddingProvider` → реальный провайдер (Yandex/GigaChat/local).
* `TTLCache` → Redis.
* Один инстанс FastAPI → несколько за reverse-proxy, stateless-сервис.
* LLM-провайдер абстрагирован — переключение без изменений в `DialogService`.