# Seeded Container Demo Runbook

Use this runbook to start MeterDesk as a reproducible local container demo. It is separate from the
[host-development workflow](../../README.md#local-setup): keep using `make install`, `make db-up`,
and `make dev` when changing code on the host.

## Prerequisites

- Docker Engine or Docker Desktop with the Compose plugin available as `docker compose`.
- Bash 4 or newer and Python 3, used by the isolated smoke harness.
- Free local ports `3000`, `8000`, and `5432`, or chosen replacements.
- The repository checkout; no OpenAI-compatible provider key is needed for the seeded replay.

## Quick start

From the repository root:

```bash
make container-build
make container-up
make container-smoke
make container-down
```

`container-build` builds the locked API and Web runtime images. `container-up` starts Postgres,
migrates, seeds, and then starts the API and Web services. `container-smoke` is an isolated,
no-key verification run: it creates its own Compose project, uses ephemeral host ports, verifies
the seeded services, and removes only that smoke project's services, volume, image tags, and
temporary artifacts when it exits.

The smoke path also verifies anonymous API rejection, operator read access, operator approval
denial, an approver decision with persisted actor/request audit data, the Web login page, and the
authenticated no-provider `503` path.

`container-down` stops the normal project and removes its containers and orphaned services. It does
not remove the normal project database volume.

The default URLs are:

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- Postgres: `localhost:5432`

Open the Web URL and choose a fixed demo identity. Use **Demo Support Operator** to start an Agent
run, **Demo Approver** to decide approvals, or **Demo Admin** to run Eval Lab. All roles may read the
business resources.

Compose publishes all three ports on `127.0.0.1` by default. They are not reachable from another
host unless an operator explicitly changes the bind address as described below.

## Seeded replay and explicit live runs

The container demo is usable without a provider key. Its tickets, audit history, and visible
outcomes are seeded replay data; they do not represent a live agent execution. In the no-key
state, attempting a new agent run returns the existing missing-provider response.

To make a live agent run from the seeded pending-approval state, keep the normal container project
running and use this sequence:

1. In the untracked local `.env`, configure `OPENAI_API_KEY` and `OPENAI_MODEL`. When
   `OPENAI_BASE_URL` is unset, Compose preserves the application default
   `https://api.openai.com/v1`; set the optional value only for another compatible endpoint. Do not
   print the values or pass them on a command line.
2. Reset the Duplicate Charge live runtime rows through the API image:

   ```bash
   docker compose run --rm --no-deps api \
     python -m meterdesk_api.demo_reset_live TCK-1042
   ```

3. Recreate the API and Web containers so they receive the newly configured provider environment,
   without rerunning their migration and seed dependencies:

   ```bash
   docker compose up -d --no-deps --force-recreate \
     --wait --wait-timeout 180 api web
   ```

4. Open the Workbench as Demo Support Operator or Demo Admin and initiate the live run for
   `TCK-1042`.

Use `TCK-1137` instead of `TCK-1042` in the reset command for the Credit/Refund Dispute path. Run
`make container-seed` whenever you want to discard live demo runtime rows and restore the seeded
baseline. This is an explicit operator flow: seeding never calls a provider, and no provider
configuration is baked into either image. Do not paste, print, commit, or include provider values
in logs, screenshots, or support artifacts.

Financial actions remain mock-only, including after a live run. Customer-facing replies remain
draft-only and are never sent by MeterDesk.

## Local demo authentication boundary

Compose passes `ENVIRONMENT=development`, an eight-hour token TTL, and a long demo-only signing-key
default to every API-image service. For a normal shared demo, override `DEMO_AUTH_SIGNING_KEY` in
the untracked `.env` with a private value of at least 32 characters. Do not put a real secret in
`.env.example`, Compose, screenshots, logs, or shell history.

FastAPI signs and verifies the JWT. Next.js stores it only in an `HttpOnly`, `SameSite=Lax`,
path-wide cookie and adds `Secure` when the incoming Web request is HTTPS. All browser tabs share
the selected identity. There is no refresh token, password, user table, revocation service, or
server-side session record; expiration, logout, or switching identity requires another one-click
demo login.

This boundary must not be exposed as production authentication. Setting `ENVIRONMENT=production`
or `prod` makes the API fail closed during startup. Use loopback bindings unless a trusted demo
network and host controls have been explicitly chosen.

## Health, logs, and reseeding

Check liveness and database reachability from the host:

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/health/db
```

`/health` confirms that FastAPI is alive. `/health/db` runs async `SELECT 1` through the shared
application-lifetime engine. Compose uses that database-backed route for API readiness with an
eight-second HTTP probe timeout and ten-second healthcheck timeout, so Web startup also depends on
database reachability.

Use these diagnostics without rendering Compose configuration or environment values:

```bash
docker compose ps
docker compose logs --tail 200 postgres migrate seed api web
```

Avoid commands that render resolved Compose configuration when local environment files may contain
secrets. The smoke harness prints service state and the last 200 log lines only when its own
verification fails; it does not render environment files or their values. Review application logs
before sharing them because they can contain local demo data.

To rerun migrations and reset only the demo-owned seed rows, use:

```bash
make container-seed
```

`container-seed` starts the normal project Postgres service if needed, runs migrations, and rebuilds
the demo-owned tickets, billing evidence, approvals, traces, mock mutations, and eval fixtures.
It leaves unrelated local rows alone. Reseeding is not a live-provider execution and does not send
customer replies or make real financial changes.

## Database and environment boundary

For a normal container run, the API ignores the host `DATABASE_URL`. It derives its connection from
the coupled `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` settings and connects internally
to `postgres:5432`. Those simple `POSTGRES_*` overrides are shared by the Postgres service and API;
`POSTGRES_PORT` changes only the host-facing database port.

Each API process owns one async engine and uses these bounded pool defaults:

- `DATABASE_POOL_SIZE=5`
- `DATABASE_MAX_OVERFLOW=5`
- `DATABASE_POOL_TIMEOUT_SECONDS=5`
- `DATABASE_CONNECT_TIMEOUT_SECONDS=3`

Override them only through the untracked local environment when a constrained demo host requires a
different per-process connection budget. Pool pre-ping remains enabled. Migrations use Alembic's
separate `NullPool`, while seed and live-reset commands dispose their own short-lived runtime.

For custom credentials that include URL-special characters, set the same raw `POSTGRES_*` values for
the Postgres service and use `CONTAINER_DATABASE_URL` as the explicit URL-encoded API override.
Keep both forms in an untracked local environment file and do not echo either form in a terminal,
log, issue, or commit. Database credentials in this demo are local-only and must not be reused for
any external or production database.

Only `make container-smoke` has strict dotenv isolation. Make skips its normal `.env` include for
that target, and the smoke script pins the repository `compose.yaml`, uses `/dev/null` as the Compose
environment file, disables automatic dotenv loading, neutralizes inherited Compose selectors, and
overrides ports, database settings, image tags, and provider variables. It does not read or print
`.env` values. Normal container targets intentionally continue to consume the local environment.

## Port overrides and Compose state

Override host ports for a normal project when the defaults are occupied:

```bash
POSTGRES_PORT=55432 API_PORT=18000 WEB_PORT=13000 make container-up
```

Use the matching overridden API port for health checks. Containers address each other through the
internal Compose names (`postgres:5432` and `http://api:8000`), so host port overrides do not change
container-to-container traffic.

All published ports remain loopback-only under those overrides. To opt in to access from another
host, set the one shared bind-address variable explicitly:

```bash
CONTAINER_BIND_ADDRESS=0.0.0.0 make container-up
```

This exposes Postgres, the API, and the Web server on every host interface. Use it only on a trusted
network with host firewall controls. MeterDesk has local demo RBAC, but it does not provide
production account security, credential lifecycle management, MFA, revocation, rate limiting, or
enterprise IAM. Prefer the loopback default when remote access is unnecessary.

Compose names containers and volumes by project. The normal project uses its persistent named
database volume across `make container-down` and future `make container-up` invocations. If you set
`COMPOSE_PROJECT_NAME`, that name selects a separate project and therefore a separate project-scoped
volume. The smoke harness always uses a unique `meterdesk-smoke-...` project, never the normal one.

### Destructive volume removal

**This workflow permanently destroys the verified Compose project database volume and its data.**
First list the active project names and volume names:

```bash
docker compose ls
docker volume ls --format '{{.Name}}'
```

Choose the exact project name that owns the data you intend to discard. The repository directory
normally produces `meter-desk`, but use that name only when `docker compose ls` confirms it and the
volume list shows the matching `meter-desk_meterdesk-postgres-data` volume. Verify the selected
project services before deleting anything:

```bash
docker compose --project-name meter-desk ps
```

If the confirmed project has another name, replace the literal `meter-desk` with that exact name in
both commands. Only after the project and its services are verified, remove that project and volume:

```bash
docker compose --project-name meter-desk down --volumes --remove-orphans
```

This destructive command is never part of normal `make container-down`. Use `make container-seed`
when a demo-data reset is sufficient.

## Troubleshooting

**Build fails.** Confirm Docker is running and the Compose plugin is available, then retry
`make container-build`. The images install from committed lockfiles; do not regenerate lockfiles to
work around a build failure.

**`container-up` does not become healthy.** Inspect `docker compose ps` and the bounded logs above.
If Postgres is healthy but `/health/db` is still unavailable from WSL2, follow the
[WSL2 Docker Desktop Postgres troubleshooting guide](../troubleshooting/wsl-docker-postgres-health-db.md).

**A default port is occupied.** Stop the process that owns the port or use the port overrides above.
Do not remove volumes merely to solve a host-port conflict.

**A live run reports that the provider is unavailable.** That is expected for the seeded no-key
path. Configure the provider privately for an explicit live run, then confirm that the normal
container project was restarted with that configuration. Never use the smoke command to test live
provider credentials.
