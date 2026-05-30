"""
Тест-сьют валидации калькулятора Матрицы Судьбы.

Эталон: пример из книги «Матрица судьбы от А до Я» (23.01.1987) — все §1-§4.
Плюс независимые публичные источники и математические инварианты.
"""
import sys
from datetime import date
from pathlib import Path

import pytest

# Make `services.*` importable when running pytest directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.destiny_matrix.calculator import (
    ARCANA_NAMES,
    calculate,
    calculate_varna,
    reduce,
    to_dict,
)


class TestReduce:
    def test_range(self):
        assert reduce(25) == 7
        assert reduce(26) == 8
        assert reduce(23) == 5
        assert reduce(30) == 3
        assert reduce(22) == 22
        assert reduce(7) == 7


class TestBookExample:
    """Эталонный пример книги: 23.01.1987. Все позиции из методики."""

    @pytest.fixture
    def m(self):
        return calculate(date(1987, 1, 23))

    def test_personality(self, m):
        assert (m.day, m.month, m.year, m.bottom, m.center) == (5, 1, 7, 13, 8)

    def test_ancestral_square(self, m):
        assert (m.anc_top_left, m.anc_top_right,
                m.anc_bottom_right, m.anc_bottom_left) == (6, 8, 20, 18)

    def test_lines_and_purposes(self, m):
        assert m.sky == 14 and m.earth == 12
        assert m.line_father == 8 and m.line_mother == 8
        assert m.purpose_personal == 8 and m.purpose_social == 16
        assert m.purpose_spiritual == 6 and m.purpose_planetary == 22

    def test_karmic_tail(self, m):
        assert m.karmic_tail.as_list() == [13, 21, 7]

    def test_talents(self, m):
        assert m.talents.as_list() == [1, 9, 10]

    def test_relationships_and_finance(self, m):
        assert m.relationships.as_list() == [21, 3, 9]
        assert m.finance.as_list() == [15, 6, 9]

    def test_material_karma(self, m):
        assert m.material_karma.as_list() == [7, 22, 15]

    def test_parental(self, m):
        assert m.parental.as_list() == [5, 13, 18]

    def test_ancestral_channels(self, m):
        assert m.ancestral_father.as_list() == [6, 14, 20]
        assert m.ancestral_father2.as_list() == [20, 10, 3]
        assert m.ancestral_mother.as_list() == [8, 16, 6]
        assert m.ancestral_mother2.as_list() == [18, 8, 8]


class TestVarna:
    def test_book_example_03_02_1993(self):
        r = calculate_varna(date(1993, 2, 3))
        assert r["varnas"]["Брахман"] == 40
        assert r["varnas"]["Кшатрий"] == 40
        assert r["expression"] == 5


class TestPublicSources:
    """Независимые источники — базовый квадрат."""

    def test_halva_10_04_1988(self):
        m = calculate(date(1988, 4, 10))
        assert (m.day, m.month, m.year) == (10, 4, 8)
        assert m.anc_top_left == 14  # 10+4

    def test_dzen_09_01_2001(self):
        m = calculate(date(2001, 1, 9))
        assert (m.day, m.month, m.year, m.bottom, m.center) == (9, 1, 3, 13, 8)
        assert m.karmic_tail.as_list() == [13, 21, 7]
        assert m.talents.as_list() == [1, 9, 10]

    def test_infohit_22_11_1983(self):
        m = calculate(date(1983, 11, 22))
        assert (m.day, m.month, m.year, m.bottom, m.center) == (22, 11, 21, 9, 9)
        assert (m.anc_top_left, m.anc_top_right,
                m.anc_bottom_right, m.anc_bottom_left) == (6, 5, 3, 4)


class TestInvariants:
    DATES = [
        date(1900, 1, 1), date(1999, 12, 31), date(1988, 2, 29),
        date(2000, 11, 22), date(2024, 8, 19), date(1956, 4, 7),
    ]

    @pytest.mark.parametrize("bd", DATES)
    def test_all_in_range(self, bd):
        for block in to_dict(calculate(bd)).values():
            for v in block.values():
                vals = v if isinstance(v, list) else [v]
                assert all(1 <= x <= 22 for x in vals)

    @pytest.mark.parametrize("bd", DATES)
    def test_idempotent(self, bd):
        assert to_dict(calculate(bd)) == to_dict(calculate(bd))


class TestArcanaNames:
    def test_marseille(self):
        assert ARCANA_NAMES[8] == "Справедливость"
        assert ARCANA_NAMES[11] == "Сила"
        assert ARCANA_NAMES[22] == "Уровневая свобода"

    def test_complete(self):
        assert set(ARCANA_NAMES) == set(range(1, 23))
