# P0-02 Authentication and Approval RBAC

## Status

- Priority: P0.
- Design status: approved for implementation.
- Implementation status: in progress on the candidate branch.
- Depends on: P0-01 CI and Runtime Baseline.
- Blocks: later hardening work that requires a trustworthy human actor or permission boundary.
- Intended deployment boundary: local development and seeded demo only.

## Problem

MeterDesk currently exposes business APIs anonymously and accepts a caller-supplied approval actor.
That makes the approval audit record untrustworthy: a client can claim any approver name, and the
server cannot distinguish reading a ticket from starting an agent, deciding an approval, or running
an eval.

P0-02 establishes one intentionally thin demo identity chain. FastAPI is the identity and
authorization authority. It issues and verifies short-lived signed tokens, derives roles from a
server-owned registry, enforces permissions on every business route, and persists the authenticated
actor for approval decisions. Next.js only holds the token in a protected cookie and forwards it to
FastAPI.

This is not an account system and is not suitable for a public or production deployment.

## Goals

1. Require a server-verifiable identity for every business API request.
2. Enforce read, agent-run, approval-decision, and eval-run permissions on the server.
3. Remove client authority over approval actor identity.
4. Preserve a structured, immutable approval decision audit record.
5. Provide a one-click local/demo login flow without passwords or external identity providers.
6. Correlate responses, structured errors, and approval decisions with a server request ID.

## Trust Boundary

```text
Browser
  |  login/switch/logout through Next.js Server Actions
  v
Next.js server
  |  HttpOnly cookie -> Authorization: Bearer <JWT>
  v
FastAPI
  |  verify signature and claims
  |  resolve subject -> role from static registry
  |  enforce route permission
  v
Repository / Postgres
  |  persist authenticated approval actor and request ID
  v
Mock financial mutation only after an approved decision
```

The browser never chooses an approval actor in an approval request. A token contains a subject but
not a role; FastAPI resolves the current role and display name from its static registry on every
request. Next.js is a cookie and presentation boundary, not the authorization authority.

## Demo Principals

The principal registry is static application configuration:

| Subject | Display name | Role |
|---|---|---|
| `demo-support-operator` | Demo Support Operator | `support_operator` |
| `demo-approver` | Demo Approver | `approver` |
| `demo-admin` | Demo Admin | `admin` |

All three identities are intentionally selectable without credentials. The login screen and API
must label this behavior as demo-only. Adding a principal or changing a role requires a server code
change; no role-management UI or user table is introduced.

## Public Authentication Interfaces

### `GET /auth/demo-identities`

Public. Returns the fixed demo identities with subject, display name, and role so the login page
does not duplicate the registry.

### `POST /auth/demo-login`

Public. Accepts exactly:

```json
{"subject": "demo-support-operator"}
```

Unknown subjects or extra fields are rejected. A successful response returns a bearer token,
expiry metadata, and the resolved principal. FastAPI signs the token; Next.js stores it in the
session cookie.

### `GET /auth/me`

Authenticated. Returns the principal resolved from the verified token subject. It does not trust a
role or display name from the token.

## Token Contract

FastAPI signs tokens with PyJWT, HS256, and an explicit `HS256` verification allowlist. The token
lifetime is eight hours and has no refresh or server-side session record.

Required claims:

| Claim | Required value or rule |
|---|---|
| `iss` | `meterdesk-demo-auth` |
| `aud` | `meterdesk-api` |
| `sub` | one registered demo subject |
| `iat` | issue time |
| `exp` | issue time plus configured eight-hour TTL |
| `jti` | unique token identifier |

Missing claims, expiration, invalid signatures, wrong issuer/audience, disallowed algorithms, and
unknown subjects all produce `401 Unauthorized`. Authentication failures use the Bearer challenge.

The role and display name do not enter the token. Changing the registry therefore changes the
effective authorization of subsequently verified requests without accepting stale role claims.

## Route Policy

The following routes remain public:

- `/health` and `/health/*`;
- `/docs`, `/redoc`, `/openapi.json`, and their framework-required assets;
- `GET /auth/demo-identities`;
- `POST /auth/demo-login`.

Every other API route requires a valid bearer token. Permissions are:

| Capability | `support_operator` | `approver` | `admin` |
|---|---:|---:|---:|
| Read business resources | allowed | allowed | allowed |
| Start an Agent run | allowed | denied | allowed |
| Approve or reject | denied | allowed | allowed |
| Run one or all Eval cases | denied | denied | allowed |

Missing or invalid authentication returns `401`. A valid principal without the required permission
returns `403`. The frontend may disable controls proactively, but FastAPI is always the final
enforcement point.

## Request Correlation and Errors

A FastAPI middleware generates `req_<uuid>` for every request. Every response, including errors,
returns it in `X-Request-ID`. MeterDesk's structured API error body also includes the same value.
Framework-native validation and not-found bodies may keep their existing shape; the response header
still supplies correlation.

An approval decision persists the request ID of the first successful terminal decision. A retry
returns that original ID rather than replacing it with the retry request's ID.

## Approval Decision Contract

Approve and reject requests accept exactly one optional field:

```json
{"decision_note": "Evidence confirms the duplicate capture."}
```

The request model forbids extra fields. The former `decided_by` field is removed without a
compatibility switch; sending it returns `422`. FastAPI constructs the actor from the authenticated
principal and passes it through the approval service to the repository.

`ApprovalSummary` exposes:

- optional `decision_actor` containing `subject`, `display_name`, `role`, and `source`;
- optional `decision_request_id`;
- the existing decision status, timestamp, note, and governed action data.

Allowed actor sources are:

- `demo_session`: a decision made through an authenticated demo token;
- `seed_fixture`: repository-owned synthetic history;
- `legacy_unverified`: an older external row whose actor cannot be verified.

Pending approvals have no decision actor, request ID, timestamp, or note. A new terminal decision
must have a complete `demo_session` actor and request ID.

### Immutable terminal decisions

The first terminal decision owns the audit record:

- approve after approve returns the original approval and creates no second mock mutation;
- reject after reject returns the original rejection;
- reject after approve, or approve after reject, returns `409 Conflict`;
- no retry changes actor, note, decision timestamp, or decision request ID.

The existing mock mutation idempotency remains in force. P1-04 remains responsible for stronger
concurrent decision evidence.

## Persistence and Migration

The Alembic migration renames the old actor display column and adds:

- actor subject;
- actor role;
- actor source;
- decision request ID;
- check constraints for pending, verified demo/fixture, and legacy combinations.

The old `decided_by` value becomes `decision_actor_display_name`. Repository-owned historical Eval
fixture `APR-EVAL-CR-003-HIST` is upgraded to subject `demo-approver`, role `approver`, source
`seed_fixture`, and deterministic request ID `req_seed_eval_cr_003_hist`.

Other pre-existing terminal rows retain their display text, use `legacy_unverified`, and receive no
invented subject, role, or request ID. Downgrade restores the display column name to `decided_by`;
the additional structured fields are necessarily discarded.

All repository-owned in-memory and Postgres fixtures must use the new contract. The historical Eval
fixture continues to prevent a duplicate synthetic financial adjustment.

## Next.js Session and UX

Next.js implements a server-only session data-access layer and Server Actions for login, identity
switch, and logout. It stores the FastAPI token in `meterdesk_demo_session` with:

- `HttpOnly`;
- `SameSite=Lax`;
- `Path=/`;
- an eight-hour expiry matching the token;
- `Secure` when the originating request is HTTPS.

No token is written to local storage. No custom CSRF token is added; SameSite cookies and Next.js
Server Action Origin/Host enforcement are the intended demo boundary.

The login action accepts only a safe relative `returnTo`. Absolute URLs, protocol-relative values,
and malformed paths fall back to the workbench root. Because the cookie is browser-scoped, all tabs
share the selected identity.

Server-side API helpers attach the bearer token on every protected request. A `401` clears the
cookie and returns the user to login. A `403` keeps the session and presents a permission message.

The AppShell shows the current identity and provides switch/logout actions. Agent, approval, and
Eval controls stay visible when unauthorized but are disabled with the required-role explanation.
Terminal approval cards show the actor summary; stable subject and request ID appear in Proof &
audit details.

## Configuration and Fail-Closed Behavior

`.env.example` and Compose expose an overrideable, long demo-only signing key and the eight-hour
TTL. The checked-in value is suitable only for a loopback demo and must be labelled accordingly.

Demo authentication is always enabled for the current application. If the runtime environment is
configured as production, startup fails closed instead of exposing demo identity selection. There
is no authentication-off flag.

## Testing and Evidence

Backend tests cover registry resolution, token claims, expiry, forged tokens, issuer/audience,
unknown subjects, production fail-closed startup, public-route boundaries, `401`/`403`, the complete
role matrix, request IDs, rejected actor spoofing, and immutable decision retries.

Postgres tests cover migration and seed compatibility, actor/request persistence, terminal decision
immutability, and single mock mutation behavior. Frontend tests cover login/switch/logout, cookie
flags, safe return paths, bearer forwarding, `401` recovery, `403` presentation, role-aware controls,
and actor display.

The container smoke test verifies anonymous rejection, operator read plus approval denial, approver
success with durable actor audit, the Web login surface, and the existing no-provider `503` behavior.

Required verification commands are:

```text
make lint
make test
make test-db
make build-web
python scripts/check_markdown_links.py
make container-smoke
```

Evidence must record the exact commands, exit statuses, relevant test counts, deviations, and any
environmental limitations.

## Non-Goals

P0-02 does not add passwords, a user table, server-side sessions, refresh tokens, revocation,
external identity providers, enterprise IAM, MFA, SCIM, multi-tenancy, or a permission-management
UI. It does not persist actors for Agent or Eval execution; that cross-action correlation remains
P0-05. It does not change the draft-only reply boundary or permit real financial mutations.

## Acceptance Criteria

- Public and protected routes match the documented boundary.
- Tokens satisfy the fixed claim and algorithm contract and expire after eight hours.
- All four capability groups enforce the complete role matrix in FastAPI.
- Approval clients cannot supply or overwrite actor identity.
- First terminal decisions retain their actor, note, timestamp, and request ID on retries.
- Seeded and migrated approval rows satisfy the structured actor/source constraints.
- Next.js never exposes the token to browser JavaScript and safely forwards authenticated requests.
- Login, identity switching, logout, unauthorized recovery, and disabled role controls work in the
  seeded demo.
- Production configuration refuses to start with demo authentication.
- Host, database, Web build, Markdown, and container verification pass with recorded evidence.

## References

- [FastAPI OAuth2 and JWT tutorial](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Next.js authentication guide](https://nextjs.org/docs/app/guides/authentication)
- [P0-01 CI and Runtime Baseline](p0-01-ci-runtime-baseline.md)
- [Hardening Roadmap](roadmap.md)
