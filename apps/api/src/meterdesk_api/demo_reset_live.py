from __future__ import annotations

import asyncio
import os
import sys

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
    ticket_id = (
        sys.argv[1] if len(sys.argv) > 1 else os.getenv("TICKET_ID", DEFAULT_LIVE_DEMO_TICKET_ID)
    )
    asyncio.run(reset_live_demo_state(ticket_id))
    print(f"MeterDesk live demo state reset for {ticket_id}.")


if __name__ == "__main__":
    main()
