#!/usr/bin/env bash
# Validate before creating files, building images or starting containers.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
die() { echo "$*" >&2; exit 1; }
[[ ${DOMAIN:-} =~ ^([A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$ ]] || die 'Set DOMAIN to a public hostname (without https:// or a port).'
[[ ${ACME_EMAIL:-} =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]] || die 'Set ACME_EMAIL to a valid email address.'
[[ ${STAGING:-0} == 0 || ${STAGING:-0} == 1 ]] || die 'STAGING must be 0 or 1.'
[[ -s web/index.html ]] || die 'Missing storefront: web/index.html.'
case "${DATABASE_URL:-sqlite:///data/cargo-auto.db}" in
 sqlite:///data/*) catalogue="${DATABASE_URL:-sqlite:///data/cargo-auto.db}"; catalogue="${catalogue#sqlite:///}"; [[ -s $catalogue ]] || die "Missing catalogue: $catalogue. Run make sqlite." ;;
 postgresql://*|postgres://*) : ;;
 *) die 'DATABASE_URL must use sqlite:///data/<file> or PostgreSQL.' ;;
esac
if [[ ${DATABASE_URL:-} =~ @postgres(:5432)?/ ]]; then
  [[ -n ${POSTGRES_PASSWORD:-} && ${POSTGRES_PASSWORD} != change-me ]] || die 'Set POSTGRES_PASSWORD before starting the production postgres profile.'
fi
[[ -n ${DOCKER:-} ]] || die 'Docker CLI not found.'
"$DOCKER" compose version >/dev/null || die 'Docker Compose plugin is missing.'
"$DOCKER" info >/dev/null 2>&1 || die 'Docker daemon is not running.'
command -v curl >/dev/null || die 'curl is required for public HTTPS checks.'
