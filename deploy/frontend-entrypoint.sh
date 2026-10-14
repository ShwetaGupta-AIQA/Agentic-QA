#!/bin/sh
set -eu
export QA_PROXY_TOKEN="$(tr -d '\r\n' < /run/secrets/api_token)"
envsubst '${QA_PROXY_TOKEN}' < /opt/qa-nginx.conf.template > /tmp/qa-nginx.conf
exec nginx -c /tmp/qa-nginx.conf -g 'daemon off;'
