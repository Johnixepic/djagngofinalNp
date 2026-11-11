#!/usr/bin/env bash
set -euo pipefail

# Enable access to the development app from devices on the same trusted LAN.
# Run from the repository root: ./scripts/enable-lan.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v ip >/dev/null 2>&1; then
    echo "Error: the 'ip' command is required (install iproute2)." >&2
    exit 1
fi

ROUTE="$(ip -4 route get 1.1.1.1 2>/dev/null | head -n 1)"
IFACE="$(awk '{for (i=1; i<=NF; i++) if ($i == "dev") {print $(i+1); exit}}' <<< "$ROUTE")"
if [[ -z "$IFACE" ]]; then
    echo "Error: could not determine the active network interface." >&2
    exit 1
fi

CIDR="$(ip -o -4 addr show dev "$IFACE" scope global | awk 'NR == 1 {print $4}')"
if [[ -z "$CIDR" ]]; then
    echo "Error: no IPv4 address found on $IFACE." >&2
    exit 1
fi

read -r HOST_IP NETWORK < <(python3 - "$CIDR" <<'PY'
import ipaddress, sys
interface = ipaddress.ip_interface(sys.argv[1])
print(interface.ip, interface.network)
PY
)

if [[ ! -f .env ]]; then
    echo "Error: .env is missing. Copy .env.example to .env and configure the database and secrets first." >&2
    exit 1
fi

python3 - "$HOST_IP" <<'PY'
from pathlib import Path
import sys

env_path = Path(".env")
host_ip = sys.argv[1]
lines = env_path.read_text().splitlines()
key = "DJANGO_ALLOWED_HOSTS"
for index, line in enumerate(lines):
    if line.strip().startswith(key + "="):
        current = line.split("=", 1)[1].strip()
        hosts = [item.strip() for item in current.split(",") if item.strip()]
        if host_ip not in hosts:
            hosts.append(host_ip)
        lines[index] = key + "=" + ",".join(hosts)
        break
else:
    lines.append(key + "=localhost,127.0.0.1," + host_ip)
env_path.write_text("\n".join(lines) + "\n")
PY

echo "Allowed Django host: $HOST_IP"
echo "LAN URL: http://$HOST_IP:8081"

if command -v ufw >/dev/null 2>&1 && sudo ufw status | grep -q "Status: active"; then
    echo "Allowing TCP/8081 from local subnet $NETWORK through UFW..."
    sudo ufw allow from "$NETWORK" to any port 8081 proto tcp
else
    echo "UFW is not active; no firewall rule was changed."
fi

echo
echo "Restart the app so Django reads the updated .env:"
echo "  docker compose up -d --force-recreate web"
echo
echo "Keep your phone and laptop on the same trusted Wi-Fi network."
echo "This app has no user login. Do not forward port 8081 to the internet."
