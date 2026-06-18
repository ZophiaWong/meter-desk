from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker

from meterdesk_api.db import create_engine
from meterdesk_api.repositories import SqlAlchemyMeterDeskRepository

DEFAULT_LIVE_DEMO_TICKET_ID = "TCK-1042"


async def reset_live_demo_state(ticket_id: str = DEFAULT_LIVE_DEMO_TICKET_ID) -> None:
    engine = create_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            repository = SqlAlchemyMeterDeskRepository(session)
            await repository.reset_demo_live_state(ticket_id)
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(reset_live_demo_state())
    print(f"MeterDesk live demo state reset for {DEFAULT_LIVE_DEMO_TICKET_ID}.")


if __name__ == "__main__":
    main()
