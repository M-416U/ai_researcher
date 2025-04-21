#!/bin/bash

echo "Initializing database..."
python3 -c "from app import create_app, init_db; app = create_app(); init_db(app)"

echo "Launching Gunicorn..."
exec gunicorn run:app --bind 0.0.0.0:${PORT:-5000}
