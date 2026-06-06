import asyncio

from meterdesk_api.db import check_database


async def seed_smoke_check() -> None:
    await check_database()
    print("MeterDesk seed smoke check complete: database reachable; no business data written.")


def main() -> None:
    asyncio.run(seed_smoke_check())


if __name__ == "__main__":
    main()
