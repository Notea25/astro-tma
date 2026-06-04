# Натальный PDF — баланс стихий с фронтовыми орбами

## Цель

Страница «Баланс стихий» в PDF должна выглядеть **точь-в-точь как вкладка
«Стихии» в приложении**: те же шары-орбы (`CosmicElementOrb`), те же подписи,
те же проценты (по 3 точкам), те же описания. Донат-кольцо убираем.

## Источник истины (фронт)

Из `frontend/src/components/screens/Natal.tsx` и `utils/natalFallbacks.ts`:

- Порядок: `ELEMENT_ORDER = ["fire", "earth", "air", "water"]`.
- Метки: Огонь / Земля / Воздух / Вода.
- Подписи (`ELEMENT_META.subtitle`): «Энергия · Действие», «Стабильность ·
  Тело», «Мысли · Общение», «Эмоции · Интуиция».
- Акценты (`ELEMENT_META.accent`): `#ff8b66`, `#93ee82`, `#bb7cff`, `#67c9ff`.
- Описания: `ELEMENT_FALLBACK_DESC[key]` (4 готовых абзаца).
- **Проценты считаются по 3 точкам** — Солнце / Луна / Асцендент — а не по 10
  планетам. `count = сколько из {Sun, Moon, Asc} попадает в знаки стихии`,
  `total = 3` (или меньше, если асцендент неизвестен). На фронте показывается
  `count / total`; в PDF дублируем эту же дробь и процент от неё.
- Орб: `<CosmicElementOrb element={key} size=...>` — самодостаточный SVG,
  палитры захардкожены, **не зависит от CSS-переменных** (в отличие от круга),
  поэтому сериализация проще — чистый `XMLSerializer` без inline-paint.

## Архитектура (зеркалит работающий wheel-SVG flow)

### 1. Фронт — сериализация орбов

`exportSvg.ts`: новая `serializeElementOrbs(): Promise<Record<ElementId,string>>`.
Рендерит 4 `CosmicElementOrb` во временный off-DOM контейнер (через
`createRoot` + `flushSync`), берёт `<svg>` каждого, прогоняет через
`XMLSerializer`, возвращает `{fire, earth, air, water}`. Размер орба под печать
— `size=240` (плотный, чёткий в PDF).

`api.ts`: провайдер `setNatalElementOrbsProvider()` + `ensureElementOrbsUploaded()`
по аналогии с wheel. `downloadPdf()` ждёт **обе** загрузки (круг + орбы) перед
скачиванием. Ошибка заливки — не фатальна (PDF нарисует fallback-орб).

`Natal.tsx`: в том же `useEffect`, что регистрирует wheel-провайдер,
регистрируем и orbs-провайдер; снимаем оба в cleanup.

### 2. Бэк — приём и кеш

`core/cache.py`: `key_natal_element_orbs(user_id) -> "natal:element-orbs:{id}"`.

`api/routes/natal.py`: `POST /natal/element-orbs`, Pydantic-модель
`ElementOrbsPayload` с 4 строками (`fire/earth/air/water`, каждая optional,
min_length при наличии). Каждый SVG: `startswith("<svg")`, лимит 256 КБ на орб,
санитайз через существующий `_sanitize_wheel_svg`. Кладём dict в Redis,
TTL 24ч. Лог `natal.element_orbs_stored` (какие ключи пришли, размеры).

`_build_natal_pdf_bytes`: читает орбы из кеша, прокидывает `element_orbs:
dict[str,str] | None` в `generate_natal_pdf_html`.

### 3. PDF — новый `_elements_page`

Убираем `_donut_svg` из страницы (саму функцию можно оставить неиспользуемой
или удалить — удаляем, YAGNI).

Макет — 4 карточки в столбик (`.element-cards-v2`), порядок `ELEMENT_ORDER`.
Каждая карточка (`.element-card-v2`):

```
[ОРБ 26мм] | Огонь            72%   ← название + процент в одной строке
           | Энергия · Действие     ← подпись (приглушённая)
           | <описание ELEMENT_COPY/fallback>
```

- Орб слева: если `element_orbs[key]` есть — вставляем фронтовый SVG в
  фикс-бокс (`width/height: 26mm`, `svg{width:100%}`); иначе fallback — простой
  радиальный круг цвета стихии.
- Процент: `round(count / total * 100)`, рядом — дробь `count/total` мелким
  приглушённым (как на фронте `count / total`).
- Подпись (`subtitle`) и описание — из тех же строк, что фронт.
- Цвет акцента стихии — `ELEMENT_META.accent` (добавляем мапу в natal_pdf.py
  или natal_pdf_html.py, чтобы совпадало с фронтом; сейчас в PDF
  `ELEMENT_COLORS` другие — приводим к фронтовым).

Блок «отсутствующая стихия» (0%) и теги-качества — **оставляем** как есть.

Проценты в PDF считаем новой `_element_points_breakdown(sun, moon, asc)` →
`{key: count}`, `total`. Старую `_element_percentages` (по 10 планетам)
оставляем для других мест (донат удалён, но функция может использоваться в
key-points — проверить; если только в донате — удалить).

### 4. Логирование

`natal.pdf_html_render_start` — добавить `has_element_orbs=bool(element_orbs)`.
`POST /natal/element-orbs` — лог приёма/отказа.

## Деградация

Нет орбов в кеше (прямой curl или фронт не залил) → fallback-круги цвета
стихии. Страница не ломается. Та же логика, что у wheel_svg.

## Тестирование

1. Сгенерировать PDF без орбов (curl) → fallback-круги, страница цела.
2. В приложении открыть Natal → Скачать PDF → орбы залились, в кеше 4 SVG.
3. Скриншот страницы стихий из PDF → визуально сверить с вкладкой «Стихии».
4. Проверить логи: `has_element_orbs=True`, `renderer=html_playwright`.
5. `ruff check` бэка, `npm run typecheck` фронта.
