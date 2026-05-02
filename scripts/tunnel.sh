#!/usr/bin/env bash
# Exposes local Flask to the internet via a Cloudflare quick tunnel (HTTPS, works on iPhone).
#
# Terminal 1: ./scripts/go_live.sh
# Terminal 2: PORT=5001 ./scripts/tunnel.sh   (PORT must match Terminal 1)
#
# Install cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-5001}"
CF="${ROOT}/tools/cloudflared"
if [[ ! -x "$CF" ]]; then
  echo "Missing $CF — download from:"
  echo "  https://github.com/cloudflare/cloudflared/releases"
  echo "Place the darwin binary at: tools/cloudflared"
  exit 1
fi
exec "$CF" tunnel --url "http://127.0.0.1:${PORT}"
