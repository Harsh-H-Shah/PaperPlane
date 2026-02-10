#!/bin/bash
# Ensure bind-mounted directories are writable
mkdir -p /app/data /app/logs 2>/dev/null || true
touch /app/logs/activity.log 2>/dev/null || true
exec "$@"
