#!/usr/bin/env bash
# duck.sh — Actualizador DuckDNS para credifycredit.duckdns.org.
# Reemplaza al antiguo duck.sh con el token incrustado: el token NUNCA vive en este
# archivo. Se lee de la variable de entorno DUCKDNS_TOKEN, que la VM obtiene desde
# /etc/environment o desde la línea del propio cron (así no se versiona).
#
# Instalación en la VM (una sola vez):
#   1. mkdir -p /root/duckdns && cp deploy/duck.sh /root/duckdns/duck.sh
#   2. chmod +x /root/duckdns/duck.sh
#   3. Prueba manual con el token real (sin publicarlo):
#        DUCKDNS_TOKEN=TU_TOKEN /root/duckdns/duck.sh        → debe imprimir "OK"
#   4. Programar en crontab (sudo crontab -e):
#        */5 * * * * DUCKDNS_TOKEN=TU_TOKEN /root/duckdns/duck.sh >/dev/null 2>&1
#
# Nota: sustituir DUCKDNS_TOKEN=TU_TOKEN por tu token real solo donde se indique;
# NUNCA editar este archivo para pegarlo (quedaría versionado).

set -u

DOMINIO="credifycredit"          # subdominio DuckDNS (sin .duckdns.org)
TOKEN="${DUCKDNS_TOKEN:-}"       # token real, inyectado desde el entorno
LOG="/var/log/duckdns.log"

if [ -z "${TOKEN}" ]; then
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: DUCKDNS_TOKEN vacio o no definido" >> "${LOG}"
  exit 1
fi

URL="https://www.duckdns.org/update?domains=${DOMINIO}&token=${TOKEN}"
RESP=$(curl -ks --max-time 20 "${URL}")

if [ "${RESP}" = "OK" ]; then
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Actualizado ${DOMINIO}.duckdns.org -> OK" >> "${LOG}"
else
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR actualizando ${DOMINIO}: ${RESP}" >> "${LOG}"
  exit 1
fi
