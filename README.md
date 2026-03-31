# 🌟 Astro TMA — Telegram Mini App

Астрологическое приложение с натальными картами, таро, совместимостью и оплатой в Telegram Stars.

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
│   │   ├── astro/         # natal, transits, moon, compatibility
│   │   ├── tarot/         # engine, seed_data
│   │   ├── users/         # repository
│   │   └── payments/      # stars.py
│   ├── api/
│   │   ├── middleware/    # telegram_auth.py
│   │   ├── routes/        # users, horoscope, tarot, compatibility, payments
│   │   └── schemas/       # pydantic schemas
│   ├── tests/
│   ├── Dockerfile
│   └── main.py
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── screens/   # Onboarding, Home, Tarot, Compatibility, Moon, Natal
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
# Заполните .env — минимум: TELEGRAM_BOT_TOKEN, APP_SECRET_KEY
```

### 3. Запуск backend
```bash
docker compose up -d postgres redis
docker compose up -d backend

# Применить миграции
docker compose exec backend alembic upgrade head

# Засеять таро-колоду (78 карт)
docker compose exec backend python infra/scripts/seed_tarot.py
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
| GET  | `/api/horoscope/today` | TG | Гороскоп на сегодня |
| GET  | `/api/horoscope/period?period=week` | TG + Premium | Гороскоп на период |
| GET  | `/api/horoscope/moon` | TG | Фаза луны |
| GET  | `/api/horoscope/moon/calendar` | TG | Лунный календарь |
| POST | `/api/tarot/draw` | TG | Расклад таро |
| POST | `/api/compatibility` | TG | Совместимость знаков |
| GET  | `/api/payments/products` | TG | Список продуктов |
| POST | `/api/payments/invoice` | TG | Создать инвойс Stars |
| POST | `/api/payments/webhook` | HMAC | Вебхук Telegram |
| GET  | `/health` | — | Health check |

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
