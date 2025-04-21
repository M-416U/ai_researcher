#!/bin/bash

echo "Running DB setup..."
python -c "from app import create_app, init_db; app = create_app(); init_db(app)"

echo "Starting Gunicorn..."
exec gunicorn run:app