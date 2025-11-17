#!/usr/bin/env bash
set -e
WSL_IP=$(ip -4 addr show eth0 | sed -n 's/.*inet \([0-9.]*\)\/.*/\1/p')
cat > docker-compose.override.yml <<EOF
services:
  bot:
    extra_hosts:
      - "wslhost:$WSL_IP"
EOF
echo "Wrote docker-compose.override.yml with wslhost -> $WSL_IP"
