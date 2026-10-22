#!/usr/bin/env bash
set -Eeuo pipefail

database_name="${1:-${DEPLOY_DATABASE_NAME:-lifeos}}"
[[ "$database_name" =~ ^[A-Za-z0-9_-]+$ ]] || {
  echo "Invalid PostgreSQL database name: $database_name" >&2
  exit 2
}

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
backup_dir="${DEPLOY_BACKUP_DIR:-$repo_root/.deploy-backups}"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
umask 077

command -v pg_dump >/dev/null || { echo "pg_dump is required" >&2; exit 1; }
command -v flock >/dev/null || { echo "flock is required (install util-linux)" >&2; exit 1; }
command -v ionice >/dev/null || { echo "ionice is required (install util-linux)" >&2; exit 1; }

exec 9>"$backup_dir/.${database_name}.lock"
flock 9

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$backup_dir/${database_name}-${stamp}.dump"
temporary_file="${backup_file}.tmp"
trap 'rm -f -- "$temporary_file"' EXIT

echo "Creating low-priority compressed backup of $database_name..."
if [[ "$EUID" -eq 0 ]]; then
  nice -n 19 ionice -c3 runuser -u postgres -- pg_dump -Fc "$database_name" > "$temporary_file"
else
  sudo -u postgres nice -n 19 ionice -c3 pg_dump -Fc "$database_name" > "$temporary_file"
fi
[[ -s "$temporary_file" ]] || { echo "pg_dump produced an empty backup file" >&2; exit 1; }
chmod 600 "$temporary_file"
mv -- "$temporary_file" "$backup_file"
trap - EXIT

mapfile -t old_backups < <(find "$backup_dir" -maxdepth 1 -type f -name "${database_name}-*.dump" -printf '%T@ %p\n' | sort -nr | awk 'NR > 3 {sub(/^[^ ]+ /, ""); print}')
for old_backup in "${old_backups[@]}"; do
  rm -f -- "$old_backup"
done

echo "Backup saved: $backup_file"
echo "Retained $(find "$backup_dir" -maxdepth 1 -type f -name "${database_name}-*.dump" | wc -l) most recent $database_name backups."
