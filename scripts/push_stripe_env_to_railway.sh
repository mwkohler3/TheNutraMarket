#!/usr/bin/env bash
# Push Stripe-related variables from .env to Railway (requires railway CLI + linked project).
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "Missing .env — copy .env.example to .env and add your Stripe keys."
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

missing=()
[[ -z "${STRIPE_SECRET_KEY:-}" ]] && missing+=("STRIPE_SECRET_KEY")
[[ -z "${STRIPE_WEBHOOK_SECRET:-}" ]] && missing+=("STRIPE_WEBHOOK_SECRET")

if ((${#missing[@]})); then
  echo "Missing in .env: ${missing[*]}"
  echo "Run: python3 scripts/configure_stripe_webhook.py  (after setting STRIPE_SECRET_KEY)"
  exit 1
fi

echo "Pushing Stripe variables to Railway..."
railway variables set \
  STRIPE_SECRET_KEY="$STRIPE_SECRET_KEY" \
  STRIPE_PUBLISHABLE_KEY="${STRIPE_PUBLISHABLE_KEY:-}" \
  STRIPE_WEBHOOK_SECRET="$STRIPE_WEBHOOK_SECRET" \
  PLATFORM_COMMITMENT_FEE_USD="${PLATFORM_COMMITMENT_FEE_USD:-250}" \
  PUBLIC_APP_URL="${PUBLIC_APP_URL:-https://thenutramarket.up.railway.app}" \
  AGREEMENT_NOTIFY_EMAIL="${AGREEMENT_NOTIFY_EMAIL:-}" \
  SMTP_HOST="${SMTP_HOST:-}" \
  SMTP_PORT="${SMTP_PORT:-587}" \
  SMTP_USER="${SMTP_USER:-}" \
  SMTP_PASSWORD="${SMTP_PASSWORD:-}" \
  MAIL_FROM="${MAIL_FROM:-}" \
  SMTP_USE_TLS="${SMTP_USE_TLS:-true}"

echo "Done. Redeploy will happen automatically on Railway."
