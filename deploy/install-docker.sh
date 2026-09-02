#!/usr/bin/env bash
# Instala Docker Engine + Compose v2 en Ubuntu (compatible 22.04 / 24.04).
# Idempotente: puede ejecutarse varias veces sin problemas.
set -euo pipefail

sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg

# Añade el repositorio oficial de Docker si no existe aún.
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg |
    sudo gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" |
    sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
fi

sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"

echo "Docker listo. Vuelve a entrar por SSH (logout) para aplicar el grupo docker."
docker --version
docker compose version