#!/bin/bash
set -e  # Exit if command fails

echo "Starting Django container..."

# Simply print database information
echo "=== Database environment variables ==="
echo "DB_HOST: $DB_HOST"
echo "DB_NAME: $DB_NAME"
echo "DB_USER: $DB_USER"
echo "DB_PORT: $DB_PORT"
echo "DB_PASSWORD: $DB_PASSWORD"
echo "=========================="

# Test MySQL port connectivity
echo "Testing MySQL connectivity to $DB_HOST:$DB_PORT ..."
if curl --connect-timeout 5 "telnet://$DB_HOST:$DB_PORT" >/dev/null 2>&1; then
  echo "MySQL connection successful!"
else
  echo "Unable to connect to MySQL at $DB_HOST:$DB_PORT"
fi

# Execute database migrations
echo "Running database migrations..."
python3 manage.py migrate --noinput

# Initialize data
echo "Initializing data..."
#python3 api/common/scripts/init_data.py

# Start application service (using gunicorn as example)
echo "Starting Gunicorn server..."
exec uwsgi --ini uwsgi.ini
