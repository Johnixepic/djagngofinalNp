#!/usr/bin/env bash
set -euo pipefail

# Detect the host's current LAN IPv4, configure the firewall if needed, and
# recreate only the Django service with that address in DJANGO_LAN_IP.
# Run from the repository root: bash scripts/enable-lan.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v ip >/dev/null 2>&1; then
    echo "Error: the 'ip' command is required (install iproute2)." >&2
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "Error: Docker is required but was not found in PATH." >&2
    exit 1
fi

if [[ ! -f .env ]]; then
    echo "Error: .env is missing. Copy .env.example to .env and configure the database and secrets first." >&2
    exit 1
fi

ROUTE="$(ip -4 route get 1.1.1.1 2>/dev/null | head -n 1 || true)"
IFACE="$(awk '{for (i=1; i<=NF; i++) if ($i == "dev") {print $(i+1); exit}}' <<< "$ROUTE")"
if [[ -z "$IFACE" ]]; then
    echo "Error: could not determine the active IPv4 network interface." >&2
    exit 1
fi

CIDR="$(ip -o -4 addr show dev "$IFACE" scope global | awk 'NR == 1 {print $4}')"
if [[ -z "$CIDR" ]]; then
    echo "Error: no global IPv4 address found on $IFACE." >&2
    exit 1
fi

read -r HOST_IP NETWORK < <(python3 - "$CIDR" <<'PY'
import ipaddress, sys
interface = ipaddress.ip_interface(sys.argv[1])
if interface.version != 4:
    raise SystemExit("Expected an IPv4 interface.")
print(interface.ip, interface.network)
PY
)

if [[ "$HOST_IP" == "127.0.0.1" ]]; then
    echo "Error: detected loopback instead of a LAN IPv4 address." >&2
    exit 1
fi

echo "Detected interface: $IFACE"
echo "Detected LAN IPv4: $HOST_IP"
echo "LAN subnet: $NETWORK"

if command -v ufw >/dev/null 2>&1 && sudo ufw status | grep -q "Status: active"; then
    if sudo ufw status | grep -Eq "8081/tcp[[:space:]]+ALLOW IN[[:space:]]+$NETWORK([[:space:]]|$)"; then
        echo "UFW already allows TCP/8081 from $NETWORK."
    else
        echo "Allowing TCP/8081 from local subnet $NETWORK through UFW..."
        sudo ufw allow from "$NETWORK" to any port 8081 proto tcp
    fi
else
    echo "UFW is not active; no firewall rule was changed."
fi

# Compose interpolates this exported value into the web service environment.
# It is intentionally not written to .env, so stale IPs do not accumulate.
export DJANGO_LAN_IP="$HOST_IP"

echo
echo "Starting/recreating the Django service with the detected LAN IP..."
docker compose up -d --force-recreate web

echo
echo "LAN access is ready: http://$HOST_IP:8081"
echo "Keep your phone and laptop on the same trusted Wi-Fi network."
echo "This app has no user login. Do not forward port 8081 to the internet."
