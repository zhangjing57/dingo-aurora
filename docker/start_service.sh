#!/usr/bin/env bash
set -ex

# kolla_set_configs
echo "/usr/local/bin/gunicorn -c /etc/dingoops/gunicorn.py main:app" >/run_command

mapfile -t CMD < <(tail /run_command | xargs -n 1)

echo "Running command: ${CMD[*]}"
exec "${CMD[@]}"
