"""Compatibility endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from api.schemas.compatibility import CompatibilityRequest, CompatibilityResponse
from core.cache import cache_get, cache_set, key_compatibility
from core.settings import settings
from db.database import get_db
from services.astro.compatibility import calculate_compatibility

router = APIRouter(prefix="/compatibility", tags=["compatibility"])


@router.post("/", response_model=CompatibilityResponse)
async def get_compatibility(
    body: CompatibilityRequest,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sign-level compatibility — free for all users.
    Results are cached since they never change for a given sign pair.
    """
    cache_key = key_compatibility(body.sign_a, body.sign_b)
    cached = await cache_get(cache_key)
    if cached:
        return CompatibilityResponse(**cached)

    result = calculate_compatibility(body.sign_a, body.sign_b)

    response = CompatibilityResponse(
        sign_a=result.sign_a,
        sign_b=result.sign_b,
        overall=result.overall,
        love=result.love,
        communication=result.communication,
        trust=result.trust,
        passion=result.passion,
        tier=result.tier,
        description_ru=result.description_ru,
        strengths_ru=result.strengths_ru,
        challenges_ru=result.challenges_ru,
        is_deep_analysis=False,
    )
    await cache_set(cache_key, response.model_dump(), settings.CACHE_TTL_COMPATIBILITY)
    return response
