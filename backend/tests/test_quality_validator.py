"""
Тесты валидатора на реальных кейсах из AstroTMA PDF.

Каждый кейс — кусок реального текста из PDF с известной проблемой.
Тесты проверяют что валидатор детектит эту проблему правильно.
"""

import pytest

from services.quality_validator import Severity, TextValidator, ValidationContext


@pytest.fixture
def v():
    return TextValidator(use_spellchecker=False)


# ────────────────────────────────────────────────────────────────────
# КЕЙСЫ ИЗ РЕАЛЬНОГО PDF
# ────────────────────────────────────────────────────────────────────


class TestRealCases:
    """Реальные тексты из AstroTMA PDF (стр.7, 12, 18 — известные проблемы)."""

    def test_uranus_template_too_short(self, v):
        """Стр.7 — Уран в Водолее, шаблонная заглушка 30 слов."""
        text = (
            "Уран в Водолее (поколение 1996–2003) — в своей стихии: "
            "революция через технологии и сетевые связи. Цифровое поколение. "
            "Положение в 6-м доме уточняет, в какой сфере это проявляется активнее всего."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Уран в Водолее")
        issues = v.validate(text, ctx)
        codes = {i.code for i in issues}
        # Должен поймать: слишком короткий + шаблонная фраза + поколенческий штамп
        assert "TOO_SHORT_CRITICAL" in codes
        assert "TEMPLATE_PHRASE" in codes
        assert "GENERATIONAL_IN_INDIVIDUAL" in codes
        assert any(i.severity == Severity.CRITICAL for i in issues)

    def test_jupiter_saturn_aspect_template(self, v):
        """Стр.12 — Юпитер ⚹ Сатурн, чистая болванка."""
        text = (
            "Юпитер и Сатурн дают возможность, которую важно осознанно использовать. "
            "Это аспект возможности: потенциал раскрывается через осознанное использование. "
            "Чем точнее орб, тем заметнее эта тема в характере, отношениях и "
            "повторяющихся выборах."
        )
        ctx = ValidationContext(section_kind="aspect", subject="Юпитер ⚹ Сатурн")
        issues = v.validate(text, ctx)
        codes = {i.code for i in issues}
        assert "TEMPLATE_PHRASE" in codes
        # Должно сработать минимум 2 шаблонных паттерна
        template_count = sum(1 for i in issues if i.code == "TEMPLATE_PHRASE")
        assert template_count >= 2

    def test_synthesis_truncated(self, v):
        """Стр.18 — синтез обрывается на полуслове «карь»."""
        text = (
            "Это напряжение часто проявляется в отношениях: вы привязываетесь, "
            "но потом чувствуете себя в ловушке. Или вы строите карь"
        )
        ctx = ValidationContext(section_kind="synthesis", subject="Финальный синтез")
        issues = v.validate(text, ctx)
        codes = {i.code for i in issues}
        assert "TRUNCATED" in codes
        critical = [i for i in issues if i.severity == Severity.CRITICAL]
        assert len(critical) >= 1

    def test_magical_wars_english(self, v):
        """Стр.8 — англицизм «магические Wars»."""
        text = (
            "Использование своих способностей и своей силы в корыстных целях. "
            "Тёмная магия. Магические Wars. Зацикленность на семье и близких, "
            "страх их смерти. Родовые конфликты. Осуждение и неприятие родителей. "
            "Неумение прощать. Неуважение к старшим. Суды с родственниками. "
            "Учитесь принимать свою духовную природу и использовать дары во благо. "
            "Работайте с прощением через медитации и практики самопознания."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Какая-то планета")
        issues = v.validate(text, ctx)
        codes = {i.code for i in issues}
        assert "LATIN_IN_RUSSIAN" in codes
        latin_issue = next(i for i in issues if i.code == "LATIN_IN_RUSSIAN")
        assert "Wars" in latin_issue.snippet

    def test_gender_mismatch_singular_plural(self, v):
        """Стр.9 — «вы реально осталась одни» (рассогласование рода+числа)."""
        text = (
            "Стрелец здесь уходит от монотонности, поэтому вас привлекают люди "
            "с идеями, путешествия, совместные проекты, которые ломают рутину. "
            "Риск: поверхностный оптимизм маскирует глубокую неуверенность в том, "
            "заслуживаете ли вы счастья. Честно посмотрите, после скольких "
            "«новых начинаний» вы реально осталась одни. Это важный сигнал. "
            "Подумайте над этим серьёзно — паттерн повторяется не случайно."
        )
        ctx = ValidationContext(section_kind="house", subject="5 дом", gender="male")
        issues = v.validate(text, ctx)
        codes = {i.code for i in issues}
        assert "GENDER_NUMBER_MISMATCH" in codes

    def test_generational_in_individual(self, v):
        """Стр.7 — «поколение 1996-2003» в индивидуальной планетарной интерпретации."""
        text = (
            "Уран в Водолее — энергия преображения и неожиданных перемен. "
            "Поколение 1996–2003 несёт в себе бунт против устаревших систем. "
            "Это даёт вам инновационное мышление и способность видеть будущее "
            "там, где другие видят только настоящее. Однако стоит помнить о "
            "практичности и не отрываться от земных реалий полностью. "
            "Балансируйте революционные идеи с конкретными шагами в реальной жизни."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Уран в Водолее")
        issues = v.validate(text, ctx)
        codes = {i.code for i in issues}
        assert "GENERATIONAL_IN_INDIVIDUAL" in codes

    def test_generational_allowed_in_outer_aspect(self, v):
        """Уран-Плутон — поколенческий аспект, штамп допустим."""
        text = (
            "Секстиль Урана и Плутона — поколенческий аспект: стремление "
            "к трансформации через нестандартные решения. На личном уровне — "
            "способность перестраиваться без разрушения. Эта связь усиливает "
            "вашу способность к глубоким изменениям в жизни, особенно когда "
            "вы решаете отказаться от устаревших паттернов. Поколение 1996–2003 "
            "несёт эту энергию коллективно, но у вас она проявляется индивидуально."
        )
        ctx = ValidationContext(section_kind="aspect", subject="Уран ⚹ Плутон")
        issues = v.validate(text, ctx)
        codes = {i.code for i in issues}
        # Поколенческий штамп НЕ должен быть проблемой здесь
        assert "GENERATIONAL_IN_INDIVIDUAL" not in codes


# ────────────────────────────────────────────────────────────────────
# ПОЗИТИВНЫЕ КЕЙСЫ — хороший текст не должен ловить ложные срабатывания
# ────────────────────────────────────────────────────────────────────


class TestGoodTexts:
    """Хорошие тексты из того же PDF — валидатор не должен на них ругаться."""

    def test_solnce_v_telce_clean(self, v):
        """Стр.6 — Солнце в Тельце, нормальный развёрнутый текст."""
        text = (
            "Солнце в Тельце делает вас человеком, для которого существование "
            "начинается с осязаемого, реального мира. Это не абстрактный идеалист, "
            "а строитель, архитектор своей жизни. Вы движетесь медленно, но "
            "неуклонно; торопить вас глупо. В 10-м доме это качество выливается "
            "в карьеру: вы ищете позиции, где можно накопить ресурсы, завоевать "
            "авторитет, оставить материальный след. На переговорах вы убеждаете "
            "не словами, а фактами и цифрами. Ваша сила — в умении преобразовать "
            "идею в объект, проект в прибыль, мечту в имущество. Уязвимость: вы "
            "можете застрять в консервативности, отказываясь от нового только "
            "потому, что оно не проверено временем."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Солнце в Тельце")
        issues = v.validate(text, ctx)
        critical = [i for i in issues if i.severity == Severity.CRITICAL]
        assert not critical, f"Не должно быть critical: {critical}"

    def test_solnce_uran_quadrature_clean(self, v):
        """Стр.13 — Солнце □ Уран, лучший текст в отчёте."""
        text = (
            "Это самый плотный аспект в вашей карте, и он фундаментален. "
            "Уран в Водолее на 6-м доме рвёт в революцию, требует переделки "
            "всех систем, включая личные привычки и работу. Солнце в Тельце "
            "на 10-м доме хочет иметь вес в обществе, заработать деньги, "
            "занять видимую позицию. Конфликт очень конкретен: вы подчиняетесь "
            "правилам на работе, но внутри саботируете их; строите репутацию, "
            "но хотите её взорвать. Признайте свою волатильность и ищите "
            "работу, которая требует постоянного переизобретения: стартапы, "
            "творчество, консультирование."
        )
        ctx = ValidationContext(section_kind="aspect", subject="Солнце □ Уран")
        issues = v.validate(text, ctx)
        critical = [i for i in issues if i.severity == Severity.CRITICAL]
        assert not critical, f"Не должно быть critical: {critical}"


# ────────────────────────────────────────────────────────────────────
# СПЕЦИАЛЬНЫЕ КЕЙСЫ
# ────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_text(self, v):
        ctx = ValidationContext(section_kind="planet_in_sign", subject="N/A")
        issues = v.validate("", ctx)
        assert len(issues) == 1
        assert issues[0].code == "EMPTY"
        assert issues[0].severity == Severity.CRITICAL

    def test_whitespace_only(self, v):
        ctx = ValidationContext(section_kind="planet_in_sign", subject="N/A")
        issues = v.validate("   \n\t  ", ctx)
        assert any(i.code == "EMPTY" for i in issues)

    def test_word_duplication(self, v):
        text = (
            "Это очень очень важный аспект в вашей карте. Он работает работает "
            "через десятый дом и связан с карьерой. Если вы понимаете эту "
            "связь, то можете использовать её на благо себя и окружающих. "
            "Главное — не забывать про практичность и реальные шаги. "
            "Развивайте себя через ежедневные действия и наблюдения за результатами."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="N/A")
        issues = v.validate(text, ctx)
        codes = {i.code for i in issues}
        assert "WORD_DUPLICATION" in codes

    def test_mc_ic_allowed(self, v):
        """Аббревиатуры MC / IC не должны помечаться как англицизмы."""
        text = (
            "Десятый дом, где находится MC (середина неба), отвечает за "
            "вашу карьеру и публичный образ. Противоположная точка — IC, "
            "глубинное основание личности. Эти две оси формируют главную "
            "вертикаль вашей карты. Через MC вы реализуетесь в мире, через "
            "IC — обретаете внутреннюю опору и связь с корнями."
        )
        ctx = ValidationContext(section_kind="house", subject="10 дом")
        issues = v.validate(text, ctx)
        latin_issues = [i for i in issues if i.code == "LATIN_IN_RUSSIAN"]
        assert not latin_issues, f"MC/IC должны быть разрешены: {latin_issues}"

    def test_truncation_with_period(self, v):
        """Текст заканчивающийся точкой не должен помечаться как обрезанный."""
        text = (
            "Это полный текст, который заканчивается нормальной точкой. "
            "Он достаточно длинный чтобы пройти проверку минимальной длины, "
            "и не содержит шаблонных фраз или англицизмов. В нём есть конкретные "
            "примеры и советы, которые могут быть полезны клиенту. Финальная "
            "мысль завершает текст логично и красиво."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Тест")
        issues = v.validate(text, ctx)
        truncated = [i for i in issues if i.code == "TRUNCATED"]
        assert not truncated
