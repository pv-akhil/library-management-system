#!/bin/sh
set -e

echo "==> Running Django database migrations..."
python manage.py migrate --noinput

echo "==> Collecting static assets..."
python manage.py collectstatic --noinput

# Optionally seed default demo data if RUN_SEED=True
if [ "$RUN_SEED" = "True" ] || [ "$RUN_SEED" = "true" ]; then
    echo "==> Seeding initial demo library catalog & accounts..."
    python manage.py seed_data || true
fi

echo "==> Starting Gunicorn WSGI server on port ${PORT:-8000}..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${GUNICORN_WORKERS:-3} \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
