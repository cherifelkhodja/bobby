#!/bin/sh
set -e

# Replace PORT variable in nginx config (Railway sets this)
export PORT=${PORT:-80}
envsubst '${PORT}' < /etc/nginx/conf.d/default.conf > /etc/nginx/conf.d/default.conf.tmp
mv /etc/nginx/conf.d/default.conf.tmp /etc/nginx/conf.d/default.conf

exec "$@"
