#!/usr/bin/env bash
set -Eeuo pipefail

read -r -a compose_command <<< "${COMPOSE:-docker compose}"
if ((${#compose_command[@]} == 0)); then
  printf 'COMPOSE must name a Compose command.\n' >&2
  exit 2
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/.." && pwd -P)
compose_file="$repo_root/compose.yaml"
if [[ ! -f "$compose_file" ]]; then
  printf 'MeterDesk Compose file not found: %s\n' "$compose_file" >&2
  exit 2
fi
readonly script_dir repo_root compose_file

unset COMPOSE_FILE
unset COMPOSE_PROJECT_NAME
unset COMPOSE_PROFILES
unset COMPOSE_ENV_FILES
unset COMPOSE_PATH_SEPARATOR
unset CONTAINER_BIND_ADDRESS
export COMPOSE_DISABLE_ENV_FILE=true

run_id=${GITHUB_RUN_ID:-local}
attempt=${GITHUB_RUN_ATTEMPT:-1}
project="meterdesk-smoke-${run_id,,}-${attempt,,}-$$"

if [[ ! "$project" =~ ^meterdesk-smoke-[a-z0-9]+-[a-z0-9]+-[0-9]+$ ]]; then
  printf 'Refusing invalid smoke project name: %s\n' "$project" >&2
  exit 2
fi

readonly project

compose() {
  "${compose_command[@]}" \
    --file "$compose_file" \
    --env-file /dev/null \
    --project-name "$project" \
    "$@"
}

cleanup() {
  local primary_status=$?
  local project_cleanup_status=0
  local image_cleanup_status=0
  local artifact_cleanup_status=0
  trap - EXIT
  set +e

  if ((primary_status != 0)); then
    printf 'Smoke failed (exit %s); Compose state follows.\n' "$primary_status" >&2
    compose ps >&2
    compose logs --tail 200 >&2
  fi

  if [[ "$project" != meterdesk-smoke-* ]]; then
    printf 'Refusing cleanup for non-smoke project: %s\n' "$project" >&2
    project_cleanup_status=2
  else
    compose down --volumes --remove-orphans
    project_cleanup_status=$?
    if ((project_cleanup_status == 0)); then
      printf 'Smoke cleanup complete for %s.\n' "$project"
    else
      printf 'Smoke cleanup failed for %s (exit %s).\n' \
        "$project" "$project_cleanup_status" >&2
    fi
  fi

  if [[ -n "${API_IMAGE:-}" || -n "${WEB_IMAGE:-}" ]]; then
    if [[ "${API_IMAGE:-}" != "meterdesk-api:${project}" || \
      "${WEB_IMAGE:-}" != "meterdesk-web:${project}" ]]; then
      printf 'Refusing cleanup for unexpected smoke image tags: API=%s Web=%s.\n' \
        "${API_IMAGE:-}" "${WEB_IMAGE:-}" >&2
      image_cleanup_status=2
    else
      docker image rm "$API_IMAGE" "$WEB_IMAGE"
      image_cleanup_status=$?
      if ((image_cleanup_status == 0)); then
        printf 'Smoke image tags removed.\n'
      else
        printf 'Smoke image cleanup failed (exit %s).\n' "$image_cleanup_status" >&2
      fi
    fi
  fi

  if [[ -n "${work_dir:-}" ]]; then
    if [[ ! "$work_dir" =~ ^/tmp/meterdesk-smoke-artifacts\.[[:alnum:]]{6}$ ]]; then
      printf 'Refusing cleanup for invalid smoke artifact directory: %s\n' "$work_dir" >&2
      artifact_cleanup_status=2
    else
      rm -r -- "$work_dir"
      artifact_cleanup_status=$?
      if ((artifact_cleanup_status == 0)); then
        printf 'Smoke artifacts removed.\n'
      else
        printf 'Smoke artifact cleanup failed (exit %s).\n' \
          "$artifact_cleanup_status" >&2
      fi
    fi
  fi

  if ((primary_status != 0)); then
    exit "$primary_status"
  fi
  if ((project_cleanup_status != 0)); then
    exit "$project_cleanup_status"
  fi
  if ((image_cleanup_status != 0)); then
    exit "$image_cleanup_status"
  fi
  exit "$artifact_cleanup_status"
}
trap cleanup EXIT

export POSTGRES_PORT=0
export API_PORT=0
export WEB_PORT=0
export POSTGRES_USER=meterdesk
export POSTGRES_PASSWORD=meterdesk
export POSTGRES_DB=meterdesk
export CONTAINER_DATABASE_URL=postgresql+psycopg://meterdesk:meterdesk@postgres:5432/meterdesk
export API_IMAGE="meterdesk-api:${project}"
export WEB_IMAGE="meterdesk-web:${project}"
export OPENAI_API_KEY=
export OPENAI_MODEL=
export OPENAI_BASE_URL=
export ENVIRONMENT=development
export DEMO_AUTH_SIGNING_KEY=meterdesk-container-smoke-only-hs256-signing-key-never-use-in-production
export DEMO_AUTH_TOKEN_TTL_SECONDS=28800

(
  unset OPENAI_BASE_URL
  export OPENAI_API_KEY=meterdesk-smoke-contract-key
  export OPENAI_MODEL=meterdesk-smoke-contract-model
  compose config --format json | python3 -c '
import json
import sys

environment = json.load(sys.stdin)["services"]["api"]["environment"]
assert environment["OPENAI_API_KEY"] == "meterdesk-smoke-contract-key"
assert environment["OPENAI_MODEL"] == "meterdesk-smoke-contract-model"
assert environment["OPENAI_BASE_URL"] == "https://api.openai.com/v1"
assert environment["ENVIRONMENT"] == "development"
assert environment["DATABASE_POOL_SIZE"] == "5"
assert environment["DATABASE_MAX_OVERFLOW"] == "5"
assert environment["DATABASE_POOL_TIMEOUT_SECONDS"] == "5"
assert environment["DATABASE_CONNECT_TIMEOUT_SECONDS"] == "3"
assert len(environment["DEMO_AUTH_SIGNING_KEY"]) >= 32
assert environment["DEMO_AUTH_TOKEN_TTL_SECONDS"] == "28800"
'
)
printf 'Runtime config contract: database, provider, and demo auth defaults are present.\n'

wait_timeout=${CONTAINER_WAIT_TIMEOUT:-180}
curl_attempts=${SMOKE_CURL_ATTEMPTS:-30}
curl_delay=${SMOKE_CURL_DELAY:-2}

if [[ ! "$wait_timeout" =~ ^[1-9][0-9]*$ ]]; then
  printf 'CONTAINER_WAIT_TIMEOUT must be a positive integer.\n' >&2
  exit 2
fi
if [[ ! "$curl_attempts" =~ ^[1-9][0-9]*$ ]] || [[ ! "$curl_delay" =~ ^[0-9]+$ ]]; then
  printf 'Smoke curl retry settings must be non-negative integers with at least one attempt.\n' >&2
  exit 2
fi

request_with_retries() {
  local url=$1
  local destination=$2
  local attempt_number

  for ((attempt_number = 1; attempt_number <= curl_attempts; attempt_number++)); do
    if curl --fail --silent --show-error --connect-timeout 2 --max-time 5 \
      --output "$destination" "$url"; then
      return 0
    fi
    if ((attempt_number < curl_attempts)); then
      sleep "$curl_delay"
    fi
  done

  printf 'Timed out waiting for %s after %s attempts.\n' "$url" "$curl_attempts" >&2
  return 1
}

assert_contains() {
  local file=$1
  local expected=$2
  local description=$3

  if ! grep --fixed-strings --quiet "$expected" "$file"; then
    printf 'Assertion failed: %s did not contain %s.\n' "$description" "$expected" >&2
    return 1
  fi
}

login_identity() {
  local subject=$1
  local response_file=$2
  local token_file=$3

  curl --fail --silent --show-error --connect-timeout 2 --max-time 10 \
    --header 'Content-Type: application/json' \
    --data "{\"subject\":\"${subject}\"}" \
    --output "$response_file" \
    "$api_url/auth/demo-login"
  python3 -c '
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
assert payload["principal"]["subject"] == sys.argv[2]
assert payload["expires_in"] == 28800
print(payload["access_token"], end="")
' "$response_file" "$subject" >"$token_file"
}

work_dir=$(mktemp -d /tmp/meterdesk-smoke-artifacts.XXXXXX)
readonly work_dir

compose build api web
compose up -d --wait --wait-timeout "$wait_timeout"

postgres_binding=$(compose port postgres 5432)
api_binding=$(compose port api 8000)
web_binding=$(compose port web 3000)
postgres_port=${postgres_binding##*:}
api_port=${api_binding##*:}
web_port=${web_binding##*:}

for binding in "$postgres_binding" "$api_binding" "$web_binding"; do
  if [[ ! "$binding" =~ ^127\.0\.0\.1:[0-9]+$ ]]; then
    printf 'Expected loopback-only smoke binding, received %s.\n' "$binding" >&2
    exit 1
  fi
done
printf 'Published ports: Postgres, API, and Web are bound to loopback.\n'

if [[ ! "$postgres_port" =~ ^[0-9]+$ ]] || [[ ! "$api_port" =~ ^[0-9]+$ ]] || [[ ! "$web_port" =~ ^[0-9]+$ ]]; then
  printf 'Could not resolve numeric ephemeral host ports.\n' >&2
  exit 1
fi
if [[ "$postgres_port" == 5432 || "$api_port" == 8000 || "$web_port" == 3000 ]]; then
  printf 'Smoke unexpectedly received a default host port.\n' >&2
  exit 1
fi

api_url="http://127.0.0.1:${api_port}"
web_url="http://127.0.0.1:${web_port}"

request_with_retries "$api_url/health" "$work_dir/health.json"
assert_contains "$work_dir/health.json" '"status":"ok"' '/health response'
printf 'API health: status=ok.\n'

request_with_retries "$api_url/health/db" "$work_dir/health-db.json"
assert_contains "$work_dir/health-db.json" '"database":"reachable"' '/health/db response'
printf 'Database health: database=reachable.\n'

anonymous_status=$(curl --silent --show-error --connect-timeout 2 --max-time 10 \
  --dump-header "$work_dir/anonymous.headers" \
  --output "$work_dir/anonymous.json" \
  --write-out '%{http_code}' \
  "$api_url/tickets")
if [[ "$anonymous_status" != 401 ]]; then
  printf 'Expected anonymous tickets status 401, received %s.\n' "$anonymous_status" >&2
  exit 1
fi
python3 -c '
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
assert payload["code"] == "auth.authentication_required"
assert payload["request_id"].startswith("req_")
' "$work_dir/anonymous.json"
if ! grep --ignore-case --fixed-strings --quiet \
  'x-request-id:' "$work_dir/anonymous.headers"; then
  printf 'Anonymous response did not include X-Request-ID.\n' >&2
  exit 1
fi
printf 'Anonymous business API: HTTP 401 with structured request ID.\n'

request_with_retries "$api_url/auth/demo-identities" "$work_dir/identities.json"
assert_contains "$work_dir/identities.json" 'demo-support-operator' 'demo identities response'
assert_contains "$work_dir/identities.json" 'demo-approver' 'demo identities response'
assert_contains "$work_dir/identities.json" 'demo-admin' 'demo identities response'
printf 'Demo identity registry: operator, approver, and admin are public.\n'

login_identity demo-support-operator "$work_dir/operator-login.json" "$work_dir/operator.token"
operator_token=$(<"$work_dir/operator.token")
curl --fail --silent --show-error --connect-timeout 2 --max-time 10 \
  --header "Authorization: Bearer ${operator_token}" \
  --output "$work_dir/tickets.json" \
  "$api_url/tickets"
assert_contains "$work_dir/tickets.json" 'TCK-1042' '/tickets response'
assert_contains "$work_dir/tickets.json" 'TCK-1137' '/tickets response'
printf 'Operator read: seeded tickets TCK-1042 and TCK-1137.\n'

operator_approval_status=$(curl --silent --show-error --connect-timeout 2 --max-time 10 \
  --header "Authorization: Bearer ${operator_token}" \
  --header 'Content-Type: application/json' \
  --data '{}' \
  --output "$work_dir/operator-approval.json" \
  --write-out '%{http_code}' \
  --request POST \
  "$api_url/approvals/APR-2042/approve")
if [[ "$operator_approval_status" != 403 ]]; then
  printf 'Expected operator approval status 403, received %s.\n' \
    "$operator_approval_status" >&2
  exit 1
fi
assert_contains "$work_dir/operator-approval.json" 'auth.forbidden' 'operator approval response'
printf 'Operator approval: HTTP 403.\n'

compose exec -T api sh -c \
  'test -z "${OPENAI_API_KEY:-}" && test -z "${OPENAI_MODEL:-}" && test -z "${OPENAI_BASE_URL:-}"'
printf 'Provider environment: key, model, and base URL are empty.\n'

provider_status=$(curl --silent --show-error --connect-timeout 2 --max-time 10 \
  --output "$work_dir/provider.json" --write-out '%{http_code}' \
  --header "Authorization: Bearer ${operator_token}" \
  --request POST "$api_url/tickets/TCK-1042/agent-runs")
if [[ "$provider_status" != 503 ]]; then
  printf 'Expected missing-provider status 503, received %s.\n' "$provider_status" >&2
  exit 1
fi
assert_contains "$work_dir/provider.json" 'OpenAI-compatible provider is not configured.' \
  'missing-provider response'
printf 'No-provider agent run: HTTP 503 with the expected message.\n'

login_identity demo-approver "$work_dir/approver-login.json" "$work_dir/approver.token"
approver_token=$(<"$work_dir/approver.token")
curl --fail --silent --show-error --connect-timeout 2 --max-time 10 \
  --dump-header "$work_dir/approver-decision.headers" \
  --header "Authorization: Bearer ${approver_token}" \
  --header 'Content-Type: application/json' \
  --data '{"decision_note":"Container smoke approval."}' \
  --output "$work_dir/approver-decision.json" \
  --request POST \
  "$api_url/approvals/APR-2042/approve"
python3 -c '
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
approval = payload["approval"]
actor = approval["decision_actor"]
assert approval["status"] == "approved"
assert actor == {
    "subject": "demo-approver",
    "display_name": "Demo Approver",
    "role": "approver",
    "source": "demo_session",
}
assert approval["decision_request_id"].startswith("req_")
print(approval["decision_request_id"], end="")
' "$work_dir/approver-decision.json" >"$work_dir/decision-request-id"
decision_request_id=$(<"$work_dir/decision-request-id")
if ! grep --ignore-case --fixed-strings --quiet \
  "x-request-id: ${decision_request_id}" "$work_dir/approver-decision.headers"; then
  printf 'Approval response header did not match the persisted decision request ID.\n' >&2
  exit 1
fi

curl --fail --silent --show-error --connect-timeout 2 --max-time 10 \
  --header "Authorization: Bearer ${approver_token}" \
  --output "$work_dir/persisted-approval.json" \
  "$api_url/approvals?status=approved&ticket_id=TCK-1042"
assert_contains "$work_dir/persisted-approval.json" 'demo-approver' 'persisted approval actor'
assert_contains "$work_dir/persisted-approval.json" "$decision_request_id" \
  'persisted approval request ID'
printf 'Approver decision: trusted actor and matching request ID persisted.\n'

web_home_status=$(curl --silent --show-error --connect-timeout 2 --max-time 10 \
  --dump-header "$work_dir/web-home.headers" \
  --output "$work_dir/web-home.html" \
  --write-out '%{http_code}' \
  "$web_url/")
if [[ "$web_home_status" != 307 && "$web_home_status" != 308 ]]; then
  printf 'Expected anonymous Web redirect, received HTTP %s.\n' "$web_home_status" >&2
  exit 1
fi
assert_contains "$work_dir/web-home.headers" '/login?returnTo=%2F' 'Web login redirect'
request_with_retries "$web_url/login" "$work_dir/web-login.html"
assert_contains "$work_dir/web-login.html" 'Choose a demo identity' 'Web login page'
assert_contains "$work_dir/web-login.html" 'Demo Support Operator' 'Web login page'
assert_contains "$work_dir/web-login.html" 'Demo Approver' 'Web login page'
assert_contains "$work_dir/web-login.html" 'Demo Admin' 'Web login page'
printf 'Web authentication: anonymous redirect and three-identity login page verified.\n'

api_user=$(docker image inspect --format '{{.Config.User}}' "$API_IMAGE")
web_user=$(docker image inspect --format '{{.Config.User}}' "$WEB_IMAGE")
if [[ "$api_user" != '10001:10001' ]] || [[ "$web_user" != '10001:10001' ]]; then
  printf 'Expected image users 10001:10001; API=%s Web=%s.\n' "$api_user" "$web_user" >&2
  exit 1
fi
printf 'Image users: API=%s Web=%s.\n' "$api_user" "$web_user"
printf 'Smoke identity: project=%s postgres_port=%s api_port=%s web_port=%s.\n' \
  "$project" "$postgres_port" "$api_port" "$web_port"
