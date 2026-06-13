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


# ────────────────────────────────────────────────────────────────────
# РЕГРЕССИИ — фиксы расслоения качества и ложных срабатываний латиницы
# ────────────────────────────────────────────────────────────────────


_VENUS_65 = (
    "Венера в Тельце даёт телесную, осязаемую любовь: для натива важны "
    "прикосновения, вкус, запах, фактура вещей. В отношениях он ищет "
    "стабильность и верность, тяжело переносит резкие перемены настроения "
    "партнёра. Деньги и красота связаны напрямую — натив тратит на то, "
    "что можно потрогать и чем владеть долго. Риск: собственничество и "
    "лень в чувствах, когда комфорт важнее развития. Учитесь отпускать "
    "контроль над близкими и ценить нематериальные знаки внимания тоже."
)  # 65 слов


class TestThinThreshold:
    """thin-порог секционный (target_words * 0.8) и согласован с генератором."""

    def test_thin_only_with_target(self, v):
        """Без target_words thin-проверка выключена — валидатор самодостаточен."""
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Венера")
        codes = {i.code for i in v.validate(_VENUS_65, ctx)}
        assert "TOO_SHORT_THIN" not in codes
        assert "TOO_SHORT_CRITICAL" not in codes

    def test_thin_warned_below_floor(self, v):
        """65 слов при цели 90 → ниже порога 72 → WARNING, не CRITICAL/TRUNCATED."""
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Венера", target_words=90)
        issues = v.validate(_VENUS_65, ctx)
        codes = {i.code for i in issues}
        assert "TOO_SHORT_THIN" in codes
        assert "TOO_SHORT_CRITICAL" not in codes
        assert "TRUNCATED" not in codes
        thin = next(i for i in issues if i.code == "TOO_SHORT_THIN")
        assert thin.severity == Severity.WARNING

    def test_not_thin_above_floor(self, v):
        """65 слов при цели 75 → выше порога 60 → штатный текст, не thin."""
        ctx = ValidationContext(section_kind="house", subject="5 дом", target_words=75)
        codes = {i.code for i in v.validate(_VENUS_65, ctx)}
        assert "TOO_SHORT_THIN" not in codes

    def test_at_target_not_thin(self, v):
        """Текст в районе цели не помечается thin (нет лишних repair)."""
        body = "Натив осваивает сферу через конкретные осязаемые шаги ежедневно. "
        text = "Солнце в Тельце. " + body * 14 + "Это итог."
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Солнце", target_words=90)
        codes = {i.code for i in v.validate(text, ctx)}
        assert "TOO_SHORT_THIN" not in codes
        assert "TOO_SHORT_CRITICAL" not in codes


class TestQualityFixes:
    """Латиница в заголовках/аббревиатурах, но не в inline-bold."""

    def test_latin_in_heading_ignored(self, v):
        """Латиница в заголовке-СТРОКЕ **...** не считается англицизмом."""
        text = (
            "**Sun in Taurus**\n"
            "Солнце в Тельце делает натива человеком, для "
            "которого мир начинается с осязаемого. Он движется медленно, но "
            "неуклонно, ценит результат, который можно потрогать и измерить. "
            "В карьере ищет позицию, дающую ресурсы и вес, убеждает фактами, "
            "а не словами, и оставляет за собой материальный, прочный след."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Солнце")
        issues = v.validate(text, ctx)
        latin = [i for i in issues if i.code == "LATIN_IN_RUSSIAN"]
        assert not latin, f"Латиница в заголовке-строке не должна ловиться: {latin}"

    def test_latin_in_inline_bold_caught(self, v):
        """Inline-bold **Wars** посреди абзаца — НЕ заголовок, латиница ловится."""
        text = (
            "Использование силы в корыстных целях. Тёмная магия. Магические "
            "**Wars** и родовые конфликты с близкими людьми. Натив учится "
            "прощать, принимать свою природу и направлять дары во благо, а не "
            "во вред окружающим его людям и собственной семье в долгой перспективе."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Плутон")
        issues = v.validate(text, ctx)
        latin = [i for i in issues if i.code == "LATIN_IN_RUSSIAN"]
        assert latin, "Латиница в inline-bold должна ловиться (finding №3)"
        assert "Wars" in latin[0].snippet

    def test_iq_eq_allowed(self, v):
        """Аббревиатуры IQ / EQ — разрешённые, не англицизмы."""
        text = (
            "Высокий IQ соединяется у натива с развитым EQ: он одинаково силён "
            "в анализе и в чувствах. Это даёт ему редкую способность понимать "
            "и логику ситуации, и эмоции людей вокруг, не теряя при этом ни "
            "холодной головы, ни живого, тёплого человеческого участия в делах."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Меркурий")
        issues = v.validate(text, ctx)
        latin = [i for i in issues if i.code == "LATIN_IN_RUSSIAN"]
        assert not latin, f"IQ/EQ должны быть разрешены: {latin}"


# ────────────────────────────────────────────────────────────────────
# LAYER 1 — секционные пороги под реальные цели генератора (90/120/140)
# ────────────────────────────────────────────────────────────────────


class TestSectionTargets:
    """Цели planets=90 / houses=120 / aspects=140 → floors 72 / 96 / 112."""

    def test_house_75_words_at_target_120_is_thin(self, v):
        """Дом ~75 слов при цели 120 (floor 96) → TOO_SHORT_THIN, не CRITICAL."""
        text = (
            "Пятый дом в Стрельце отвечает за творчество, детей и романтику. "
            "Натив влюбляется в идеи и людей, которые расширяют его горизонт, "
            "тянется к спорту, дальним путешествиям, азартной игре и сцене. "
            "В детях он ценит свободу и поощряет их живое любопытство, а не "
            "слепое послушание любой ценой. В романах ему важен драйв и общий "
            "поиск смысла, скучную предсказуемость он не выносит и быстро остывает. "
            "Риск — разбрасываться: начинать ярко и эффектно, но бросать дело, "
            "когда уходит первый кураж и притупляется живой азарт самой игры."
        )
        ctx = ValidationContext(section_kind="house", subject="5 дом", target_words=120)
        codes = {i.code for i in v.validate(text, ctx)}
        assert "TOO_SHORT_THIN" in codes

    def test_aspect_90_words_at_target_140_is_thin(self, v):
        """Аспект на ~90 слов при цели 140 (floor 112) → TOO_SHORT_THIN."""
        text = (
            "Венера в трине к Марсу соединяет нежность и напор: натив умеет "
            "и желать, и заботиться, не теряя одно ради другого. В отношениях "
            "он берёт инициативу мягко, без давления, и партнёр чувствует "
            "одновременно страсть и безопасность. В работе это даёт обаяние "
            "переговорщика — он добивается своего, не наживая врагов. Сильная "
            "сторона: притягательность и лёгкость в сближении. Зона роста — "
            "не путать лёгкость с поверхностностью, доводить близость до глубины, "
            "а проекты до конца, не бросая на половине ради нового увлечения."
        )
        ctx = ValidationContext(section_kind="aspect", subject="Венера △ Марс", target_words=140)
        codes = {i.code for i in v.validate(text, ctx)}
        assert "TOO_SHORT_THIN" in codes

    def test_compact_planet_at_target_not_thin(self, v):
        """Планета ~85 слов при цели 90 (floor 72) — штатный текст, не thin."""
        text = (
            "Меркурий в Близнецах делает ум натива быстрым, любопытным и "
            "переключаемым: он схватывает суть на лету, легко говорит и пишет, "
            "обожает обмен фактами и новыми контактами с разными людьми. "
            "В работе силён там, где нужно быстро переварить много информации "
            "и связать разрозненное в стройную и понятную другим картину. "
            "Уязвимость — распыление: десять вкладок в голове сразу, ни одна "
            "из них не закрыта до конца. Совет — выбирать одну тему в день "
            "и доводить её до конкретного результата, а не коллекционировать "
            "начатое и так и недосказанное вслух без ясного финала."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Меркурий", target_words=90)
        codes = {i.code for i in v.validate(text, ctx)}
        assert "TOO_SHORT_THIN" not in codes
        assert "TOO_SHORT_CRITICAL" not in codes


# ────────────────────────────────────────────────────────────────────
# LAYER 2 — усиленные шаблонные паттерны
# ────────────────────────────────────────────────────────────────────


class TestTemplatePatterns:
    """Новые штампы ловятся, легитимные обороты высших планет — нет."""

    @pytest.mark.parametrize(
        "phrase",
        [
            "важно осознанно использовать этот ресурс",
            "потенциал раскрывается через работу и быт",
            "это даёт возможность для роста",
            "положение в доме уточняет сферу проявления",
            "чем точнее орб тем заметнее тема",
        ],
    )
    def test_template_phrase_detected(self, v, phrase):
        text = phrase + ". " + " ".join(["содержательный"] * 60) + "."
        ctx = ValidationContext(section_kind="aspect", subject="тест")
        codes = {i.code for i in v.validate(text, ctx)}
        assert "TEMPLATE_PHRASE" in codes, f"не пойман штамп: {phrase!r}"

    def test_legit_outer_aspect_phrases_not_template(self, v):
        """«на личном уровне» и «поколенческий аспект» — НЕ штампы."""
        text = (
            "Секстиль Урана и Плутона — поколенческий аспект: стремление "
            "к трансформации через нестандартные решения. На личном уровне — "
            "способность перестраиваться без разрушения. Эта связь усиливает "
            "вашу способность к глубоким изменениям, когда вы отказываетесь "
            "от устаревших паттернов и выбираете осознанный путь обновления."
        )
        ctx = ValidationContext(section_kind="aspect", subject="Уран ⚹ Плутон")
        codes = {i.code for i in v.validate(text, ctx)}
        assert "TEMPLATE_PHRASE" not in codes


# ────────────────────────────────────────────────────────────────────
# LAYER 3 — финальный synthesis: обрыв и критическая короткость
# ────────────────────────────────────────────────────────────────────


class TestSynthesis:
    """validate(reading, section_kind='synthesis') ловит обрыв/короткость."""

    def test_synthesis_truncated_detected(self, v):
        text = (
            "Главное противоречие вашей карты — между жаждой стабильности и "
            "тягой к переменам. Вы строите прочное, но внутри саботируете "
            "собственные правила. Или вы строите карь"
        )
        ctx = ValidationContext(section_kind="synthesis", subject="Финал")
        codes = {i.code for i in v.validate(text, ctx)}
        assert "TRUNCATED" in codes

    def test_synthesis_complete_clean(self, v):
        text = (
            "Главный дар вашей карты — умение превращать идеи в осязаемый "
            "результат. Главная задача — научиться отпускать контроль там, "
            "где он мешает близости. В ближайший год обратите внимание на "
            "баланс между карьерой и домом: именно там сейчас точка роста."
        )
        ctx = ValidationContext(section_kind="synthesis", subject="Финал")
        codes = {i.code for i in v.validate(text, ctx)}
        assert "TRUNCATED" not in codes


class TestNatalAnRegressions:
    """Регрессии из ревью карты AN (natal_AN.pdf)."""

    def test_case_after_prep_nominative(self, v):
        """P1-1: «направлено на карьера» — именительный после «на»."""
        text = (
            "Венера в Тельце раскрывает мягкую чувственность и тягу к красоте. "
            "В 10-м доме это качество направлено на карьера, статус, "
            "предназначение и видимое место в мире, и это формирует ваш стиль "
            "взаимодействия с окружающими людьми каждый день без исключения."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Венера")
        codes = {i.code for i in v.validate(text, ctx)}
        assert "CASE_AFTER_PREP" in codes

    def test_case_after_prep_clean_form(self, v):
        """Переписанная связка «работает в сфере: …» не триггерит правило."""
        text = (
            "Венера в Тельце раскрывает мягкую чувственность и тягу к красоте. "
            "В 10-м доме это качество работает в сфере: карьера, статус, "
            "предназначение и видимое место в мире, и это формирует ваш стиль "
            "взаимодействия с окружающими людьми каждый день без исключения."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Венера")
        codes = {i.code for i in v.validate(text, ctx)}
        assert "CASE_AFTER_PREP" not in codes

    def test_case_after_prep_allows_normal_phrase(self, v):
        """Нормальное «на режим сна» не должно уходить в repair."""
        text = (
            "Уран в шестом доме направляет внимание на режим сна и здоровье "
            "без перегибов: вам важно замечать, когда тело просит нового ритма, "
            "и перестраивать расписание до того, как накопится раздражение."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Уран")
        codes = {i.code for i in v.validate(text, ctx)}
        assert "CASE_AFTER_PREP" not in codes

    def test_false_asc_attribution_in_aspect(self, v):
        """P2-2: «Солнце на Асценденте Льва» в тексте аспекта."""
        text = (
            "Солнце в квадрате к Луне создаёт внутреннее напряжение между волей "
            "и чувствами. Солнце в Тельце на Асценденте Льва усиливает желание "
            "быть замеченным, и это требует постоянной внутренней работы над "
            "балансом между амбицией и эмоциональной потребностью в покое."
        )
        ctx = ValidationContext(section_kind="aspect", subject="Солнце квадрат Луна")
        codes = {i.code for i in v.validate(text, ctx)}
        assert "FALSE_ASC_ATTRIBUTION" in codes

    def test_false_asc_attribution_only_in_aspect(self, v):
        """Та же фраза в разборе планеты — не аспект — не триггерит правило."""
        text = (
            "Солнце в Тельце на Асценденте Льва усиливает желание быть "
            "замеченным и придаёт характеру тёплую, царственную ноту, которая "
            "проявляется в манере держаться и в стремлении вести за собой "
            "людей в любых жизненных обстоятельствах без лишней суеты."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Солнце")
        codes = {i.code for i in v.validate(text, ctx)}
        assert "FALSE_ASC_ATTRIBUTION" not in codes

    def test_broken_gender_phrase_detected(self, v):
        """P2-5: «результат уже видна цель» — м.р. сущ. + ж.р. краткая форма."""
        text = (
            "Марс в Деве делает вас педантичным в действии: вы доводите дело до "
            "конца, когда результат уже видна цель, и не бросаете начатое на "
            "полпути, даже если это требует кропотливой и долгой работы над "
            "каждой мелкой деталью без права на ошибку."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Марс")
        codes = {i.code for i in v.validate(text, ctx)}
        assert "GENDER_NUMBER_MISMATCH" in codes

    def test_correct_gender_phrase_clean(self, v):
        """Корректная фраза «когда цель уже видна» (цель — ж.р.) не триггерит."""
        text = (
            "Марс в Деве делает вас педантичным в действии: вы доводите дело до "
            "конца, когда цель уже видна и понятна, и не бросаете начатое на "
            "полпути, даже если это требует кропотливой и долгой работы над "
            "каждой мелкой деталью без права на ошибку."
        )
        ctx = ValidationContext(section_kind="planet_in_sign", subject="Марс")
        codes = {i.code for i in v.validate(text, ctx)}
        assert "GENDER_NUMBER_MISMATCH" not in codes
