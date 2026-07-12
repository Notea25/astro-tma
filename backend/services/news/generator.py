"""LLM news writer — turns a detected event into a short article."""

from typing import Any

from core.logging import get_logger
from core.settings import settings
from services.llm_utils import first_text_block

log = get_logger(__name__)


async def generate_body(event: dict[str, Any]) -> str:
    """Write a short 2-3 paragraph explanation. Falls back to simple template."""
    source = event.get("source_data", {})
    title = event.get("title_ru", "Астрологическое событие")

    if not settings.LLM_API_KEY:
        return _fallback_body(title, source)

    prompt = (
        f"Ты пишешь короткую новость для астро-ленты популярного приложения. "
        f"Читатели — обычные люди, не астрологи.\n\n"
        f"Заголовок: {title}\n"
        f"Данные события: {source}\n\n"
        f"Формат: 2-3 коротких абзаца (150-220 слов всего). "
        f"Первый — что происходит человеческим языком. "
        f"Второй — как это будет ощущаться в обычной жизни: настроение, дела, отношения, разговоры. "
        f"Третий (опционально) — один конкретный совет: что попробовать или чего избегать.\n\n"
        f"КАК ПИСАТЬ:\n"
        f"- Живой язык, как будто рассказываешь подруге за кофе.\n"
        f"- Конкретные образы из жизни.\n"
        f"- Без эзотерического жаргона: ни «энергии», ни «вселенная», ни «архетипы».\n"
        f"- Без banальностей вроде «звёзды благоволят».\n"
        f"- Без markdown, без списков, без заголовков — только обычные абзацы.\n"
        f"- Обращайся на «вы», без официоза."
    )
    try:
        from services.llm_client import create_llm_client
        from services.llm_pool import llm_semaphore

        client = create_llm_client()
        async with llm_semaphore:
            message = await client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
        text = first_text_block(message.content).strip()
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
