"""
Destiny Matrix calculator — pure math, no I/O, no LLM.

Источник методики: книга «Матрица судьбы от А до Я» (Н. Бастиков, метод Л. Ладини).
Традиция арканов: Marseille (8=Справедливость, 11=Сила, 22=Шут/Свобода).

ВАЛИДАЦИЯ: формулы проверены на эталонном примере из книги (23.01.1987)
плюс на трёх независимых публичных источниках (Халва 10.04.1988,
Dzen 09.01.2001, ИнфоХит 22.11.1983). Полный тест-сьют — в
tests/test_calculator.py (28 тестов).

Используются английские code-ключи (`day`, `month`, `top_left`, …) —
display labels на русском живут в UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


# ── Свёртка ─────────────────────────────────────────────────────────────────

def reduce(n: int) -> int:
    """Свёртка к диапазону арканов 1..22 сложением цифр.
    Примеры: 25→7, 26→8, 23→5, 30→3. Месяцы (1..12) и суммы ≤22 не сворачиваются."""
    while n > 22:
        n = sum(int(d) for d in str(n))
    return n


def reduce1(n: int) -> int:
    """Ведическая свёртка до 1..9 — используется для расчёта варн."""
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n


# ── Авторские названия арканов из книги ────────────────────────────────────

ARCANA_NAMES: dict[int, str] = {
    1: "Маг", 2: "Единство", 3: "Императрица", 4: "Император",
    5: "Учитель", 6: "Любовь", 7: "Воин",
    8: "Справедливость", 9: "Мудрец", 10: "Фортуна",
    11: "Сила", 12: "Новое видение", 13: "Трансформация",
    14: "Искусство", 15: "Проявление", 16: "Духовное преображение",
    17: "Звезда", 18: "Магия", 19: "Солнце",
    20: "Ясно знание", 21: "Мир", 22: "Уровневая свобода",
}


# ── Касты для расчёта варны (по числам кармы 1..9) ──────────────────────────

VARNA = {
    1: "Кшатрий", 9: "Кшатрий",
    3: "Брахман", 6: "Брахман",
    2: "Вайшью", 5: "Вайшью",
    4: "Шудра", 7: "Шудра", 8: "Шудра",
}


# ── Структуры данных ────────────────────────────────────────────────────────

@dataclass
class Channel:
    """Канал-«ключ» из трёх энергий: начало, середина, итог."""
    a: int
    b: int
    c: int

    def as_list(self) -> list[int]:
        return [self.a, self.b, self.c]


@dataclass
class DestinyMatrix:
    # §1 Личностный (диагональный) ромб
    day: int
    month: int
    year: int
    bottom: int
    center: int

    # §2 Родовой (прямой) квадрат
    anc_top_left: int
    anc_top_right: int
    anc_bottom_right: int
    anc_bottom_left: int

    # §3 Линии и предназначения
    sky: int
    earth: int
    line_father: int
    line_mother: int
    purpose_personal: int
    purpose_social: int
    purpose_spiritual: int
    purpose_planetary: int

    # §4 Каналы (3 энергии каждый)
    karmic_tail: Channel
    talents: Channel
    relationships: Channel
    finance: Channel
    material_karma: Channel
    parental: Channel
    ancestral_father: Channel   # таланты по линии отца (ATL)
    ancestral_father2: Channel  # карма по линии отца (ABR)
    ancestral_mother: Channel   # таланты по линии матери (ATR)
    ancestral_mother2: Channel  # карма по линии матери (ABL)

    # Дополнительные точки
    cross_point: int
    material_karma_point: int


# ── Расчёт ──────────────────────────────────────────────────────────────────

def calculate(birth: date) -> DestinyMatrix:
    """Полный расчёт Матрицы Судьбы по дате рождения. Чистая математика,
    детерминированная: одна дата → одна матрица."""

    # §1 Личностный квадрат (диагональный ромб)
    D = reduce(birth.day)
    M = reduce(birth.month)
    Y = reduce(sum(int(c) for c in str(birth.year)))
    B = reduce(D + M + Y)
    C = reduce(D + M + Y + B)

    # §2 Родовой квадрат (прямой)
    atl = reduce(D + M)
    atr = reduce(M + Y)
    abr = reduce(Y + B)
    abl = reduce(B + D)

    # §3 Линии и предназначения
    sky = reduce(M + B)
    earth = reduce(D + Y)
    line_father = reduce(atl + abr)
    line_mother = reduce(atr + abl)
    lp = reduce(sky + earth)            # личное (до 40 лет)
    sp = reduce(line_father + line_mother)  # социальное (40-60)
    dp = reduce(lp + sp)                # духовное (после 60)
    pp = reduce(sp + dp)                # планетарное (миссия)

    # §4.1 Кармический хвост (приём «вершина + C, затем + вершина»)
    kt = Channel(B, reduce(B + C), reduce(B + reduce(B + C)))

    # §4.2 Зона талантов
    tal = Channel(M, reduce(M + C), reduce(M + reduce(M + C)))

    # §4.3 Линия благополучия: отношения + финансы (пересекаются)
    mk_point = reduce(Y + C)                 # точка материальной кармы (стык)
    cross = reduce(kt.b + mk_point)
    rel_center = reduce(kt.b + cross)
    fin_center = reduce(mk_point + cross)
    relationships = Channel(kt.b, rel_center, cross)
    finance = Channel(mk_point, fin_center, cross)

    # §4.4 Материальная карма
    mk_center = reduce(Y + mk_point)
    material_karma = Channel(Y, mk_center, mk_point)

    # §4.5 Детско-родительский (на линии Земли)
    parental = Channel(D, reduce(D + C), reduce(D + reduce(D + C)))

    # §4.6 Родовые каналы (приём «вершина + C, затем + вершина»)
    af1 = reduce(atl + C); af2 = reduce(atl + af1)
    af3 = reduce(abr + C); af4 = reduce(abr + af3)
    am1 = reduce(atr + C); am2 = reduce(atr + am1)
    am3 = reduce(abl + C); am4 = reduce(abl + am3)

    return DestinyMatrix(
        day=D, month=M, year=Y, bottom=B, center=C,
        anc_top_left=atl, anc_top_right=atr,
        anc_bottom_right=abr, anc_bottom_left=abl,
        sky=sky, earth=earth,
        line_father=line_father, line_mother=line_mother,
        purpose_personal=lp, purpose_social=sp,
        purpose_spiritual=dp, purpose_planetary=pp,
        karmic_tail=kt, talents=tal,
        relationships=relationships, finance=finance,
        material_karma=material_karma, parental=parental,
        ancestral_father=Channel(atl, af1, af2),
        ancestral_father2=Channel(abr, af3, af4),
        ancestral_mother=Channel(atr, am1, am2),
        ancestral_mother2=Channel(abl, am3, am4),
        cross_point=cross, material_karma_point=mk_point,
    )


def calculate_varna(birth: date) -> dict:
    """Расчёт варн (каст) по дате рождения. Ведическая свёртка до 1..9.

    Правило: рождение 00:00-01:30 → берётся предыдущий день. Здесь время
    не учитываем — варну считаем от паспортной даты как есть, корректировку
    оставляем UI/пользователю.
    """
    d = reduce1(birth.day)
    m = reduce1(birth.month)
    y = reduce1(sum(int(c) for c in str(birth.year)))
    s = reduce1(d + m + y)
    result: dict[str, int] = {}
    for digit, pct in [(d, 40), (m, 10), (y, 10), (s, 40)]:
        v = VARNA.get(digit, "—")
        result[v] = result.get(v, 0) + pct
    return {
        "varnas": result,
        "expression": reduce1(birth.day + birth.month),
    }


def to_dict(m: DestinyMatrix) -> dict[str, Any]:
    """Сериализация в плоский dict для JSONB / API ответа."""
    return {
        "personality": {
            "day": m.day, "month": m.month, "year": m.year,
            "bottom": m.bottom, "center": m.center,
        },
        "ancestral_square": {
            "top_left": m.anc_top_left, "top_right": m.anc_top_right,
            "bottom_right": m.anc_bottom_right, "bottom_left": m.anc_bottom_left,
        },
        "lines": {
            "sky": m.sky, "earth": m.earth,
            "father": m.line_father, "mother": m.line_mother,
        },
        "purposes": {
            "personal": m.purpose_personal,
            "social": m.purpose_social,
            "spiritual": m.purpose_spiritual,
            "planetary": m.purpose_planetary,
        },
        "channels": {
            "karmic_tail": m.karmic_tail.as_list(),
            "talents": m.talents.as_list(),
            "relationships": m.relationships.as_list(),
            "finance": m.finance.as_list(),
            "material_karma": m.material_karma.as_list(),
            "parental": m.parental.as_list(),
            "ancestral_father_talents": m.ancestral_father.as_list(),
            "ancestral_father_karma": m.ancestral_father2.as_list(),
            "ancestral_mother_talents": m.ancestral_mother.as_list(),
            "ancestral_mother_karma": m.ancestral_mother2.as_list(),
        },
    }


# ── Public entry point — совместим с прежним API ────────────────────────────

def calculate_matrix(birth_date: date) -> dict[str, Any]:
    """Удобная обёртка: считает матрицу + варну и возвращает плоский dict
    для хранения в JSONB. Используется из api/routes/destiny_matrix.py."""
    return {
        **to_dict(calculate(birth_date)),
        "varna": calculate_varna(birth_date),
    }
