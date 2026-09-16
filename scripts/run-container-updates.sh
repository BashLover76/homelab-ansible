#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
log_dir="$repo_dir/logs"
lock_file="$log_dir/container-updates.lock"

mkdir -p "$log_dir"

exec 9>"$lock_file"
flock -n 9 || exit 0

cd "$repo_dir"

ansible-playbook playbook/update-alertmanager.yml
