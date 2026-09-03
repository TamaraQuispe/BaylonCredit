#!/usr/bin/env bash
# Backup diario de la base de datos PostgreSQL del contenedor Docker.
#   - Vuelca la base con pg_dump comprimido en gzip.
#   - Rotación: conserva los últimos RETENTION_DAYS backups.
#   - Lee las credenciales del .env.prod del proyecto automáticamente.
#
# Uso:
#   ./deploy/backup-postgres.sh          # desde el repo
#   backup-postgres.sh  ~/BaylonCredit   # desde cualquier sitio, indicando el repo
set -euo pipefail

REPO_DIR="${1:-$(pwd)}"
ENV_FILE="${REPO_DIR}/.env.prod"
BACKUP_DIR="${BACKUP_DIR:-${HOME}/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
DB_CONTAINER="${DB_CONTAINER:-bayloncredit-database-1}"

if [ ! -f "${ENV_FILE}" ]; then
  echo "ERROR: no se encuentra ${ENV_FILE}" >&2
  exit 1
fi

# Extrae usuario / base / host del DATABASE_URL (postgresql+asyncpg://user:pass@host:port/db)
DB_URL="$(grep -E '^DATABASE_URL=' "${ENV_FILE}" | head -1 | cut -d= -f2- | tr -d '\"')"
DB_USER="$(printf '%s' "${DB_URL}" | sed -E 's#^.*\/\/([^:]+):.*#\1#')"
DB_NAME="$(printf '%s' "${DB_URL}" | sed -E 's#.*/([^/?]*)(\?.*)?$#\1#')"
DB_HOST="$(printf '%s' "${DB_URL}" | sed -E 's#^.*@([^:]+):.*#\1#')"
DB_PASS="$(printf '%s' "${DB_URL}" | sed -E 's#^.*\/\/[^:]+:([^@]*)@.*#\1#')"
DB_PORT="$(printf '%s' "${DB_URL}" | sed -E 's#^.*@[^:]+:([0-9]+).*#\1#' )"
DB_PORT="${DB_PORT:-5432}"

mkdir -p "${BACKUP_DIR}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_FILE="${BACKUP_DIR}/bayloncredit-${STAMP}.sql.gz"
TMP_FILE="${OUT_FILE}.tmp"

echo "Dump de ${DB_NAME}@${DB_HOST} -> ${OUT_FILE}"
if docker exec -e PGPASSWORD="${DB_PASS}" "${DB_CONTAINER}" pg_dump -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -d "${DB_NAME}" --no-owner | gzip > "${TMP_FILE}"; then
  mv "${TMP_FILE}" "${OUT_FILE}"
  echo "OK: backup creado"
else
  rm -f "${TMP_FILE}"
  echo "ERROR: fallo el pg_dump" >&2
  exit 1
fi

# Rotación: borra los backups más antiguos que RETENTION_DAYS días
find "${BACKUP_DIR}" -maxdepth 1 -type f -name 'bayloncredit-*.sql.gz' -mtime +"${RETENTION_DAYS}" -delete

echo "Backups conservados (ultimos):"
ls -1t "${BACKUP_DIR}"/bayloncredit-*.sql.gz 2>/dev/null | head -3