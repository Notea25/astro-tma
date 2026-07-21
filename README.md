# Astro TMA

Telegram Mini App: гороскопы, натальная карта, Матрица Судьбы, таро, синастрия и транзиты.  
Бот: [@astrologiyatut_bot](https://t.me/astrologiyatut_bot)

**Стек:** React + Vite · FastAPI · PostgreSQL · Redis · Kerykeion / Swiss Ephemeris · LLM-интерпретации · Telegram Stars + ЮKасса

Нагрузочное тестирование: [`LOAD_TESTING.md`](LOAD_TESTING.md).

---

## Фичи

### Бесплатно
| Раздел | Что есть |
|--------|----------|
| **Главная** | Гороскоп на сегодня, карта дня Таро, фаза Луны |
| **Гороскопы** | Сегодня / завтра / неделя / месяц по любому знаку |
| **Луна** | Текущая фаза + календарь лунных дней |
| **Таро** | Все расклады с LLM-разбором (карта дня, 3 карты, Кельтский крест, неделя, отношения) |
| **МАК-карты** | Карта дня и колода по категориям |
| **Натал** | Колесо, Солнце/Луна/ASC, планеты и аспекты без длинных текстов |
| **Матрица Судьбы** | Октаграмма + 2 бесплатных раздела разбора |
| **Транзиты** | Обзор на сегодня |
| **Синастрия** | Приглашение партнёра (результат — платный) |
| **Глоссарий / новости** | Справочник терминов и лента астрособытий |
| **Пуши** | Утренний гороскоп ~9:00 (по умолчанию вкл.) |



## Быстрый старт

```bash
cp .env.example .env   # TELEGRAM_BOT_TOKEN, APP_SECRET_KEY, LLM_*, ADMIN_*
docker compose up -d
docker compose exec backend alembic upgrade head

cd frontend && npm i && npm run dev
```

Прод: `docker compose -f docker-compose.yml up -d` (без `override.yml`).  
Локальный reload/порты — только в `docker-compose.override.yml`.

Админка: `https://<host>/admin/` · цены · Stars-отчёт.

---

## Структура

```
backend/     FastAPI, астро-сервисы, платежи, пуши, worker (PDF)
frontend/    React Mini App
infra/       nginx, postgres conf, setup-скрипты
scripts/     деплой, смок, load-тесты
```
