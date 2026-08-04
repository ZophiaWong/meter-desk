from types import SimpleNamespace

import pytest

import meterdesk_api.db as db
import meterdesk_api.main as main_module
from meterdesk_api.settings import Settings


class DisposableRuntime:
    def __init__(self) -> None:
        self.dispose_calls = 0

    async def dispose(self) -> None:
        self.dispose_calls += 1


def test_create_database_runtime_configures_the_bounded_pool(monkeypatch) -> None:
    captured: dict[str, object] = {}
    engine = object()
    session_factory = object()

    def create_engine(database_url: str, **kwargs):
        captured["database_url"] = database_url
        captured["engine_kwargs"] = kwargs
        return engine

    def create_session_factory(bound_engine, **kwargs):
        captured["session_engine"] = bound_engine
        captured["session_kwargs"] = kwargs
        return session_factory

    monkeypatch.setattr(db, "create_async_engine", create_engine)
    monkeypatch.setattr(db, "async_sessionmaker", create_session_factory)
    settings = Settings(
        database_url="postgresql+psycopg://test:test@db.test:5432/test",
        database_pool_size=7,
        database_max_overflow=4,
        database_pool_timeout_seconds=9,
        database_connect_timeout_seconds=11,
        _env_file=None,
    )

    runtime = db.create_database_runtime(settings)

    assert runtime.engine is engine
    assert runtime.session_factory is session_factory
    assert captured == {
        "database_url": "postgresql+psycopg://test:test@db.test:5432/test",
        "engine_kwargs": {
            "connect_args": {"connect_timeout": 11},
            "pool_pre_ping": True,
            "pool_size": 7,
            "max_overflow": 4,
            "pool_timeout": 9,
        },
        "session_engine": engine,
        "session_kwargs": {"expire_on_commit": False},
    }


@pytest.mark.asyncio
async def test_database_runtime_context_disposes_after_an_error(monkeypatch) -> None:
    runtime = DisposableRuntime()
    monkeypatch.setattr(db, "create_database_runtime", lambda settings=None: runtime)

    with pytest.raises(RuntimeError, match="deliberate failure"):
        async with db.database_runtime_context():
            raise RuntimeError("deliberate failure")

    assert runtime.dispose_calls == 1


@pytest.mark.asyncio
async def test_app_lifespan_owns_one_runtime_and_disposes_it_once(monkeypatch) -> None:
    runtime = DisposableRuntime()
    build_calls = 0

    def create_runtime():
        nonlocal build_calls
        build_calls += 1
        return runtime

    monkeypatch.setattr(main_module, "create_database_runtime", create_runtime)
    test_app = main_module.create_app()

    assert build_calls == 0
    async with test_app.router.lifespan_context(test_app):
        assert build_calls == 1
        assert test_app.state.database_runtime is runtime
        assert runtime.dispose_calls == 0

    assert runtime.dispose_calls == 1
    assert not hasattr(test_app.state, "database_runtime")


@pytest.mark.asyncio
async def test_app_lifespan_disposes_runtime_when_serving_fails(monkeypatch) -> None:
    runtime = DisposableRuntime()
    monkeypatch.setattr(main_module, "create_database_runtime", lambda: runtime)
    test_app = main_module.create_app()

    with pytest.raises(RuntimeError, match="serving failure"):
        async with test_app.router.lifespan_context(test_app):
            raise RuntimeError("serving failure")

    assert runtime.dispose_calls == 1
    assert not hasattr(test_app.state, "database_runtime")


@pytest.mark.asyncio
async def test_get_database_runtime_rejects_missing_lifespan_state() -> None:
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    with pytest.raises(RuntimeError, match="FastAPI lifespan"):
        await db.get_database_runtime(request)


@pytest.mark.asyncio
async def test_get_session_yields_independent_sessions_from_the_runtime() -> None:
    sessions = []

    class FakeSession:
        def __init__(self) -> None:
            self.closed = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            self.closed = True

    class FakeSessionFactory:
        def __call__(self):
            session = FakeSession()
            sessions.append(session)
            return session

    runtime = SimpleNamespace(session_factory=FakeSessionFactory())
    first_dependency = db.get_session(runtime)
    second_dependency = db.get_session(runtime)

    first = await anext(first_dependency)
    second = await anext(second_dependency)

    assert first is not second
    await first_dependency.aclose()
    await second_dependency.aclose()
    assert [session.closed for session in sessions] == [True, True]


@pytest.mark.asyncio
async def test_check_database_executes_an_async_query_on_the_runtime_engine() -> None:
    statements: list[str] = []

    class FakeConnection:
        async def execute(self, statement) -> None:
            statements.append(str(statement))

    class ConnectionContext:
        async def __aenter__(self):
            return FakeConnection()

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

    class FakeEngine:
        def connect(self):
            return ConnectionContext()

    await db.check_database(SimpleNamespace(engine=FakeEngine()))

    assert statements == ["SELECT 1"]
