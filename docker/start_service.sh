#!/usr/bin/env bash
set -ex

# start celery worker

celery -A dingoops.celery_api.workers worker --loglevel=info


# kolla_set_configs
echo "/usr/local/bin/gunicorn -c /etc/dingoops/gunicorn.py main:app" >/run_command

mapfile -t CMD < <(tail /run_command | xargs -n 1)
# kolla_extend_start
pip install -e .
if [[ "${!KOLLA_BOOTSTRAP[*]}" ]]; then

    alembic -c ./db/alembic/alembic.ini upgrade head
    exit 0
fi
echo "Running command: ${CMD[*]}"
exec "${CMD[@]}"
