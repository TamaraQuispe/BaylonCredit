#!/usr/bin/env bash
set -euo pipefail

ROOT="$(dirname "$(dirname "$(realpath "$0")")")"
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-$(openssl rand -hex 32)}"
docker compose --project-directory "$ROOT" -f "$ROOT/docker-compose.demo.yml" up --build -d
printf '\nDemo local: http://localhost:8081\nUsuario: docente@example.com\nClave: DemoAPF2-2026!\nDatos ficticios, sin conexion con produccion.\n'
