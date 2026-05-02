#!/usr/bin/env bash
# Run Flask ready to share: tunnel-friendly port, debug off, correct URLs behind HTTPS tunnels.
#
# Usage:
#   Terminal 1:  ./scripts/go_live.sh
#   Terminal 2:  PORT=5001 ./scripts/tunnel.sh
#
# cloudflared prints a https://….trycloudflare.com URL — send that link (open on iPhone, not localhost).
# Optional: SESSION_COOKIE_SECURE=1 ./scripts/go_live.sh  (cookies only over HTTPS; localhost http won’t keep session)
# macOS: PORT defaults to 5001 (AirPlay often uses 5000).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" == "Darwin" ]]; then
  export PORT="${PORT:-5001}"
else
  export PORT="${PORT:-5000}"
fi
export FLASK_HOST="${FLASK_HOST:-127.0.0.1}"
export FLASK_DEBUG="${FLASK_DEBUG:-0}"

echo ""
echo "Flask → http://${FLASK_HOST}:${PORT}  (debug=${FLASK_DEBUG})"
echo ""
echo "In a second terminal:"
echo "  cd \"${ROOT}\" && PORT=${PORT} ./scripts/tunnel.sh"
echo ""
echo "Share the https://….trycloudflare.com URL. Stripe/checkout needs that same public URL (see ProxyFix in app.py)."
echo ""

exec python3 app.py
