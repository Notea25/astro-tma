"""LLM news writer — turns a detected event into a short article."""

from typing import Any

from core.logging import get_logger
from core.settings import settings

log = get_logger(__name__)


async def generate_body(event: dict[str, Any]) -> str:
    """Write a short 2-3 paragraph explanation. Falls back to simple template."""
    source = event.get("source_data", {})
    title = event.get("title_ru", "Астрологическое событие")

    if not settings.ANTHROPIC_API_KEY:
        return _fallback_body(title, source)

    prompt = (
        f"Ты — астролог. Напиши короткую новость для астро-ленты мобильного приложения.\n\n"
        f"Заголовок: {title}\n"
        f"Данные события: {source}\n\n"
        f"Формат: 2-3 коротких абзаца (150-220 слов всего), на русском. "
        f"Первый абзац — что происходит. Второй — как это влияет на людей (эмоции, дела, отношения). "
        f"Третий (опционально) — совет или на что обратить внимание. "
        f"Без воды, без эзотерического жаргона, практично и тепло. "
        f"Не используй маркдаун или списки — только обычные абзацы."
    )
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        return text or _fallback_body(title, source)
    except Exception as e:
        log.warning("news.llm_failed", title=title, error=str(e))
        return _fallback_body(title, source)


def _fallback_body(title: str, source: dict[str, Any]) -> str:
    planet = source.get("planet", "").capitalize()
    to_sign = source.get("to_sign_ru")
    if to_sign:
        return (
            f"{title}.\n\n"
            f"Смена знака меняет тональность темы планеты {planet}. "
            f"В ближайшие недели вы почувствуете новые акценты в делах и настроении. "
            f"Хороший момент, чтобы пересмотреть свои цели и расставить приоритеты заново."
        )
    if "retrograde" in source:
        direction = "ретроградно" if source.get("retrograde") else "прямо"
        return (
            f"{title}.\n\n"
            f"Когда планета движется {direction}, её тема переходит в другое качество. "
            f"Это время переосмысления и корректировки. Не торопитесь с решениями — "
            f"дайте себе время прочувствовать перемену."
        )
    return f"{title}.\n\nСлежите за своим состоянием и принимайте важные решения осознанно."
