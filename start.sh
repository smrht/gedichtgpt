#!/bin/bash

# Activeer virtual environment als die bestaat
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Controleer of Redis draait
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis..."
    redis-server &
    sleep 2
fi

# Stel environment variables in
export FLASK_APP=app.py
export FLASK_ENV=production
export PYTHONUNBUFFERED=1

# Start Gunicorn met optimale instellingen
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --threads 2 \
    --worker-class gevent \
    --worker-connections 1000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output \
    app:app
