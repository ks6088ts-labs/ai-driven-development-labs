#!/bin/sh
# Provisioning script: creates the "viewer" Grafana user on first startup.
# Runs as a short-lived sidecar (grafana-setup service in compose.observability.yml).
#
# Future extension point:
#   Replace Basic Auth with OIDC by setting GF_AUTH_GENERIC_OAUTH_* variables
#   in compose and removing this script. The "viewer" role mapping can then be
#   handled by the IdP group → Grafana role mapping.

set -eu

GRAFANA_URL="http://grafana:3000"
ADMIN_USER="admin"
ADMIN_PASS="${GF_SECURITY_ADMIN_PASSWORD:-changeme}"
VIEWER_PASS="${GF_VIEWER_PASSWORD:-viewerpass}"

echo "Waiting for Grafana to become ready..."
RETRIES=0
MAX_RETRIES=30
until curl -sf "${GRAFANA_URL}/api/health" | grep -q '"database":"ok"'; do
  RETRIES=$((RETRIES + 1))
  if [ "${RETRIES}" -ge "${MAX_RETRIES}" ]; then
    echo "Error: Grafana did not become ready after ${MAX_RETRIES} attempts." >&2
    exit 1
  fi
  sleep 3
done
echo "Grafana is ready."

# Create the viewer user (idempotent – ignores "user already exists" errors).
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "${GRAFANA_URL}/api/admin/users" \
  -H "Content-Type: application/json" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -d "{
    \"name\":     \"Viewer\",
    \"email\":    \"viewer@localhost\",
    \"login\":    \"viewer\",
    \"password\": \"${VIEWER_PASS}\",
    \"role\":     \"Viewer\"
  }")

if [ "${HTTP_STATUS}" = "200" ] || [ "${HTTP_STATUS}" = "412" ]; then
  # 412 = user already exists
  echo "Viewer user provisioned (HTTP ${HTTP_STATUS})."
else
  echo "Warning: unexpected HTTP status ${HTTP_STATUS} when creating viewer user." >&2
fi
