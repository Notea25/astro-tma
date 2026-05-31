import asyncio

from sqlalchemy import case, func, select

from db.database import AsyncSessionLocal
from db.models import ArcanaMeaning


async def main() -> None:
    async with AsyncSessionLocal() as s:
        filled_expr = func.sum(case((ArcanaMeaning.meaning != "", 1), else_=0))
        total_expr = func.count()
        r = await s.execute(
            select(ArcanaMeaning.arcana_num, filled_expr, total_expr)
            .group_by(ArcanaMeaning.arcana_num)
            .order_by(ArcanaMeaning.arcana_num)
        )
        for row in r.all():
            print(f"arcana {row[0]:2d}: {row[1]}/{row[2]}")
        tot = await s.execute(select(filled_expr, total_expr))
        f, t = tot.one()
        print(f"TOTAL: {f}/{t}")


asyncio.run(main())
