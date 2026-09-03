#!/usr/bin/env bash
# Descarga los backups de la VM Oracle a esta máquina (Mac).
# Uso:
#   deploy/descargar-backups.sh                # con rutas por defecto
#   deploy/descargar-backups.sh <IP> <clave.pem>
set -euo pipefail

HOST_ORACLE="${1:-168.75.71.113}"
SSH_KEY="${2:-${HOME}/.ssh/bayloncredit-oracle.key}"
LOCAL_DIR="${LOCAL_DIR:-${HOME}/BaylonCredit-backups}"
REMOTE_DIR="${REMOTE_DIR:-backups}"

mkdir -p "${LOCAL_DIR}"
echo "Descargando backups de ${HOST_ORACLE}:${REMOTE_DIR} a ${LOCAL_DIR}"
scp -q -i "${SSH_KEY}" "ubuntu@${HOST_ORACLE}:${REMOTE_DIR}/bayloncredit-*.sql.gz" "${LOCAL_DIR}/"

echo "OK"
ls -1t "${LOCAL_DIR}"/bayloncredit-*.sql.gz | head -3