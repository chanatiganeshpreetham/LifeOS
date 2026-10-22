#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  echo "Usage: ./deploy.sh BRANCH VERSION" >&2
  echo "Example: ./deploy.sh main v1.2.0" >&2
  exit 2
}

[[ $# -eq 2 ]] || usage
branch="$1"
version="$2"

git check-ref-format --branch "$branch" >/dev/null || {
  echo "Invalid Git branch: $branch" >&2
  exit 2
}
[[ "$version" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ && ${#version} -le 120 ]] || {
  echo "Invalid version tag: use up to 120 letters, digits, dots, underscores, or hyphens." >&2
  exit 2
}

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

compose_file="${DEPLOY_COMPOSE_FILE:-docker-compose.prod.yml}"
env_file="${DEPLOY_ENV_FILE:-.env.production}"
database_name="${DEPLOY_DATABASE_NAME:-lifeos}"
health_url="${DEPLOY_HEALTHCHECK_URL:-http://127.0.0.1:8080/api/v1/health}"

[[ -f "$compose_file" ]] || { echo "Compose file not found: $compose_file" >&2; exit 1; }
[[ -f "$env_file" ]] || { echo "Environment file not found: $env_file" >&2; exit 1; }
command -v docker >/dev/null || { echo "docker is not installed" >&2; exit 1; }
docker compose version >/dev/null || { echo "Docker Compose v2 is required" >&2; exit 1; }
command -v git >/dev/null || { echo "git is not installed" >&2; exit 1; }
command -v curl >/dev/null || { echo "curl is not installed" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required for health response validation" >&2; exit 1; }

if ! git diff --quiet -- . ':(exclude)deploy.sh' || ! git diff --cached --quiet || [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
  echo "Working tree has uncommitted or untracked source files. Commit/stash/inspect them before deploying." >&2
  git status --short >&2
  exit 1
fi
script_numstat="$(git diff --numstat -- deploy.sh)"
if [[ -n "$script_numstat" && "$script_numstat" != $'0\t0\tdeploy.sh' ]]; then
  echo "deploy.sh has content changes. Commit/stash them before deploying." >&2
  exit 1
fi

app_name="${DEPLOY_APP_NAME:-$(basename "$repo_root" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9_-]+/-/g; s/^[^a-z0-9]+//')}"
[[ "$app_name" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || {
  echo "Invalid Compose app name: $app_name (set DEPLOY_APP_NAME to a valid lowercase name)." >&2
  exit 1
}
export DEPLOY_IMAGE_PREFIX="${DEPLOY_IMAGE_PREFIX:-$app_name}"
export DEPLOY_VERSION="$version"

compose=(docker compose --parallel 1 --project-name "$app_name" --env-file "$env_file" -f "$compose_file")

echo "Fetching branch $branch..."
git fetch origin --prune
git show-ref --verify --quiet "refs/remotes/origin/$branch" || {
  echo "Remote branch origin/$branch was not found." >&2
  exit 1
}
if git show-ref --verify --quiet "refs/heads/$branch"; then
  git switch "$branch"
else
  git switch --track -c "$branch" "origin/$branch"
fi
git pull --ff-only origin "$branch"

commit="$(git rev-parse --short HEAD)"
echo "Preparing $app_name version $version from $branch ($commit)."
"${compose[@]}" config -q

for service in api frontend; do
  image="${DEPLOY_IMAGE_PREFIX}-${service}:${version}"
  if docker image inspect "$image" >/dev/null 2>&1; then
    echo "Image tag already exists: $image. Choose a new version name." >&2
    exit 1
  fi
done

echo "Building version-tagged Docker images..."
"${compose[@]}" build

if [[ "$database_name" != "none" ]]; then
  echo "Checking whether this release has pending database migrations..."
  migration_state="$("${compose[@]}" run --rm --no-deps api python -c 'from alembic.config import Config; from alembic.script import ScriptDirectory; from alembic.runtime.migration import MigrationContext; from app.db.session import engine; heads=sorted(ScriptDirectory.from_config(Config("alembic.ini")).get_heads()); conn=engine.connect(); current=sorted(MigrationContext.configure(conn).get_current_heads()); conn.close(); print("pending" if current != heads else "current")')"
  case "$migration_state" in
    pending)
      echo "Pending migration detected. Taking a PostgreSQL backup before applying it..."
      "$repo_root/backup-db.sh" "$database_name"
      "${compose[@]}" run --rm --no-deps api alembic upgrade head
      ;;
    current)
      echo "Database is already at the migration heads; skipping backup and migration."
      ;;
    *)
      echo "Could not determine migration state (reported: $migration_state). Stopping before deployment." >&2
      exit 1
      ;;
  esac
fi

echo "Starting version $version..."
"${compose[@]}" up -d --no-build --force-recreate

echo "Waiting for healthy API response at $health_url (up to 3 minutes)..."
healthy=false
for attempt in $(seq 1 36); do
  if response="$(curl --max-time 5 -fsS "$health_url" 2>/dev/null)" && \
    printf '%s' "$response" | python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin).get("status") == "ok" else 1)' 2>/dev/null; then
    healthy=true
    break
  fi
  sleep 5
done

if [[ "$healthy" != true ]]; then
  echo "Health check did not return status=ok. Deployment remains running for inspection; no automatic rollback was attempted." >&2
  "${compose[@]}" ps >&2 || true
  "${compose[@]}" logs --tail=100 api >&2 || true
  exit 1
fi

echo "Deployment healthy: $app_name version $version ($commit)."
"${compose[@]}" ps
