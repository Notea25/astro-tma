# 🌟 Astro TMA — Telegram Mini App

Астрологическое приложение с натальными картами, таро, совместимостью, транзитами, синастрией, астро-новостями, глоссарием, push-уведомлениями и оплатой в Telegram Stars.

## Стек

| Слой | Технология |
|------|-----------|
| Frontend | React 18 + Vite + TypeScript + Framer Motion |
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) |
| Астро-движок | Kerykeion + Swiss Ephemeris (NASA JPL) |
| БД | PostgreSQL 16 |
| Кэш | Redis 7 |
| Контейнеры | Docker + Docker Compose |
| Reverse proxy | Nginx |
| Оплата | Telegram Stars (XTR) |

## Структура проекта

```
astro-tma/
├── backend/
│   ├── core/              # settings, logging, cache
│   ├── db/                # ORM models, migrations, database.py
│   ├── services/
│   │   ├── astro/         # natal, transits, synastry, moon, compatibility
│   │   ├── tarot/         # engine, seed_data
│   │   ├── users/         # repository
│   │   ├── payments/      # stars.py
│   │   ├── notifications/ # push.py, scheduler.py (Telegram Bot API)
│   │   ├── glossary/      # seed.py
│   │   └── news/          # events.py, generator.py, scheduler.py
│   ├── api/
│   │   ├── middleware/    # telegram_auth.py
│   │   ├── routes/        # users, horoscope, tarot, compatibility, natal, payments,
│   │   │                  # transits, synastry, glossary, news
│   │   └── schemas/       # pydantic schemas
│   ├── tests/
│   ├── Dockerfile
│   └── main.py
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── screens/   # Onboarding, Home, Discover, Tarot, Compatibility, Moon,
│       │   │              # Natal, Mac, Profile, Transits, Synastry, SynastryInvite,
│       │   │              # Glossary, GlossaryTerm, News, NewsDetail
│       │   └── ui/        # BottomNav, PremiumGate, EnergyBars, ZodiacPicker
│       ├── hooks/         # useTelegram, usePayment
│       ├── services/      # api.ts
│       ├── stores/        # app.ts (Zustand)
│       ├── types/         # index.ts
│       └── styles/        # globals.css
├── infra/
│   ├── nginx/
│   └── scripts/           # setup.sh, seed_tarot.py
├── docker-compose.yml
├── docker-compose.override.yml
└── .env.example
```

## Порты в dev-режиме

`docker-compose.override.yml` пробрасывает Postgres на `localhost:5433` и Redis на `localhost:6380` (5432/6379 часто заняты другими локальными сервисами). Внутри docker-сети контейнеры общаются по `postgres:5432` и `redis:6379` — это на хостовые порты не влияет.

## HTTPS-туннель для Telegram в dev

Vite настроен с `server.allowedHosts: ['.ngrok-free.dev', '.ngrok.io', '.trycloudflare.com', 'localhost']` (см. `vite.config.ts`) — можно пробросить dev-фронт через ngrok/cloudflare-tunnel и подключить к боту через BotFather без ошибки «Blocked request. This host is not allowed».

## Быстрый старт (локально)

### 1. Предварительные требования
- Docker + Docker Compose
- Node.js 20+
- Python 3.12+ (только если запускать backend без Docker)

### 2. Настройка
```bash
git clone <repo>
cd astro-tma
cp .env.example .env
# Заполните .env — минимум: TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_USERNAME (для синастрии),
# APP_SECRET_KEY, LLM_API_KEY, LLM_BASE_URL и LLM_MODEL
```

LLM-провайдер должен поддерживать OpenAI Chat Completions. Для переключения
провайдера достаточно изменить три переменные и пересоздать `backend`/`worker`:

```bash
# DeepSeek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
LLM_API_KEY=...

# Groq, пример альтернативы
# LLM_BASE_URL=https://api.groq.com/openai/v1
# LLM_MODEL=openai/gpt-oss-20b
```

Ключ хранится только в production `.env` на VPS и не передаётся во frontend.

### 3. Запуск backend
```bash
docker compose up -d postgres redis
docker compose up -d backend

# Применить миграции
docker compose exec backend alembic upgrade head

# Засеять таро-колоду (78 карт)
docker cp infra/scripts/seed_tarot.py astro-tma-backend-1:/tmp/seed_tarot.py
docker compose exec -e PYTHONPATH=/app backend python /tmp/seed_tarot.py

# Засеять глоссарий (~45 терминов; требует LLM_API_KEY для полных описаний)
docker compose exec -e PYTHONPATH=/app backend python -m services.glossary.seed
```

### 4. Запуск frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### 5. Telegram Bot настройка

1. Создайте бота через [@BotFather](https://t.me/BotFather) → `/newbot`
2. Скопируйте токен в `.env` → `TELEGRAM_BOT_TOKEN`
3. Для разработки установите [ngrok](https://ngrok.com):
   ```bash
   ngrok http 8000
   # Скопируйте HTTPS URL → TELEGRAM_WEBHOOK_URL в .env
   ```
4. Зарегистрируйте вебхук:
   ```bash
   curl "https://api.telegram.org/bot{TOKEN}/setWebhook" \
     -d "url={WEBHOOK_URL}/api/payments/webhook" \
     -d "secret_token={TELEGRAM_WEBHOOK_SECRET}"
   ```
5. Создайте Mini App: BotFather → `/newapp` → укажите URL фронтенда

## Деплой на VPS

```bash
# На сервере (Ubuntu 24.04)
bash infra/scripts/setup.sh

# Получить SSL сертификат
certbot --nginx -d api.yourdomain.com

# Запустить всё
docker compose up -d

# Задеплоить фронтенд на Vercel
cd frontend && vercel deploy --prod
```

## API эндпоинты

| Method | Path | Auth | Описание |
|--------|------|------|----------|
| POST | `/api/users/me` | TG | Upsert пользователя |
| POST | `/api/users/me/birth` | TG | Установить данные рождения |
| PATCH | `/api/users/me/push` | TG | Вкл/выкл push-уведомления |
| GET  | `/api/horoscope/today` | TG | Гороскоп на сегодня |
| GET  | `/api/horoscope/period?period=week` | TG + Premium | Гороскоп на период |
| GET  | `/api/horoscope/moon` | TG | Фаза луны |
| GET  | `/api/horoscope/moon/calendar` | TG | Лунный календарь |
| GET  | `/api/natal/summary` | TG | Краткая натальная карта |
| GET  | `/api/natal/full` | TG + Premium | Полная натальная карта |
| GET  | `/api/natal/pdf` | TG + Premium | PDF натальной карты |
| GET  | `/api/transits/current` | TG | Текущие транзиты без условных процентов |
| GET  | `/api/transits/date?date=YYYY-MM-DD` | TG | Транзиты на произвольную дату |
| POST | `/api/synastry/request` | TG + Purchase | Создать invite-токен |
| POST | `/api/synastry/accept/{token}` | TG | Принять приглашение, рассчитать |
| GET  | `/api/synastry/pending` | TG | Входящие приглашения |
| GET  | `/api/synastry/result/{id}` | TG | Результат (обоим участникам) |
| GET  | `/api/glossary` | TG | Список терминов (фильтр `?category=`, `?q=`) |
| GET  | `/api/glossary/{slug}` | TG | Детали термина |
| GET  | `/api/news` | TG | Лента астро-новостей |
| GET  | `/api/news/{id}` | TG | Детали новости |
| POST | `/api/tarot/draw` | TG | Расклад таро |
| POST | `/api/compatibility` | TG | Совместимость знаков |
| GET  | `/api/payments/products` | TG | Список продуктов |
| POST | `/api/payments/invoice` | TG | Создать инвойс Stars |
| POST | `/api/payments/webhook` | HMAC | Вебхук Telegram |
| GET  | `/health` | — | Health check |

## Scheduled jobs (APScheduler)

| Job | Расписание | Назначение |
|-----|-----------|-----------|
| `daily_horoscopes` | 00:05 UTC | Прегенерация 12 знаков через LLM |
| `daily_pushes` | каждый час | Утренний гороскоп через Bot API юзерам у кого local hour = `PUSH_DAILY_HOUR` |
| `daily_news` | 06:00 UTC | Детекция событий на 48ч вперёд + LLM-генерация новостей |

## Deep-link: Синастрия

Приглашение партнёра: `https://t.me/{TELEGRAM_BOT_USERNAME}?startapp=syn_<token>`.
Фронтенд читает `WebApp.initDataUnsafe.start_param`, извлекает токен и автоматически открывает экран принятия.

## Миграция контента safety-v1

Поля `energy`, `scores` и `position_meaning_ru` удалены из клиентских
контрактов. При раздельном деплое сначала выкатывается frontend, который их
больше не читает, затем применяется миграция `022_content_version`, после неё
перезапускаются backend и worker.

Перед массовой регенерацией обязателен backup и ручная проверка dry-run:

```bash
docker compose exec backend python scripts/regenerate_content.py --dry-run
pg_dump -Fc -d astro_tma -f /backups/astro-before-safety-v1.dump
docker compose exec backend python scripts/regenerate_content.py --execute \
  --backup-file /backups/astro-before-safety-v1.dump \
  --confirm-version 2026-07-safety-v1
```

`--execute` обрабатывает только контент нецелевой версии, ограничивает LLM
concurrency до `2` и поэтому безопасно продолжается после перезапуска.

Натальный отчёт генерируется четырьмя параллельными structured-батчами: core,
10 планет, 12 домов (только при известном времени) и полный набор основных
аспектов. Backend добавляет точные факты из Swiss Ephemeris, а LLM возвращает
только смысловые narrative-блоки. Канонический JSON, собранный текст и уже
отрендеренный PDF сохраняются в PostgreSQL. Экран «Полный отчёт», PDF и
Telegram используют этот один payload без повторных LLM-вызовов. Кеш
инвалидируется по SHA-256 при изменении данных рождения, пола, карты, версии
контента или PDF-шаблона.

## Локальная сверка с GeoCult

Синтетический профиль `Astro QA` (`777777777`) разрешено создавать только в
development/staging. Команда с `--reset` пересчитывает его карту и удаляет
только связанный с ним локальный generated content:

```bash
cd backend
python scripts/seed_comparison_user.py --reset
python scripts/compare_geocult.py
```

В сравнении зафиксированы профиль `20.02.2000 14:30 Europe/Moscow`, партнёр
`15.08.1995 09:30 Europe/Moscow` (исторический offset `+04:00`) и транзиты
`2026-07-12T12:30:00Z`. Команда ничего не пишет в БД и завершается с кодом `1`,
если долготы расходятся больше чем на `0.001°`, а орбисы — больше чем на
`0.01°`. Для UI-проверки скопируйте `frontend/.env.example` и установите
`VITE_USE_LOCAL_FIXTURES=false`.

## Тесты

```bash
cd backend
pip install -e ".[dev]"
pytest tests/ -v --cov=services
```

## Монетизация (Telegram Stars)

| Продукт | Цена |
|---------|------|
| Гороскоп завтра | 25 ⭐ |
| Гороскоп на неделю | 50 ⭐ |
| Гороскоп на месяц | 75 ⭐ |
| Таро Кельтский Крест | 30 ⭐ |
| Таро на неделю | 40 ⭐ |
| Полная натальная карта | 150 ⭐ |
| Синастрия | 100 ⭐ |
| Premium 30 дней | 299 ⭐ |
| Premium 365 дней | 1990 ⭐ |

> Telegram берёт ~30% комиссии. Оставшееся выводится в TON через Fragment.
