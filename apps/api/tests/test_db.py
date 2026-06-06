import meterdesk_api.db as db


async def test_check_database_runs_database_probe(monkeypatch) -> None:
    captured: dict[str, bool] = {}

    def probe() -> None:
        captured["probe"] = True

    monkeypatch.setattr(db, "_run_database_probe", probe)

    await db.check_database()

    assert captured == {"probe": True}
