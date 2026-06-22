#!/usr/bin/env python3
"""Create or verify Stripe webhook endpoint for TheNutraMarket checkout."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def public_app_url() -> str:
    raw = (
        os.environ.get("PUBLIC_APP_URL", "").strip()
        or os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
        or "https://thenutramarket.up.railway.app"
    )
    if not raw.startswith("http"):
        raw = f"https://{raw}"
    return raw.rstrip("/")


def main() -> int:
    load_dotenv()
    try:
        import stripe
    except ImportError:
        print("Install stripe: pip install stripe")
        return 1

    secret = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not secret:
        print("Set STRIPE_SECRET_KEY in .env first (see .env.example).")
        return 1

    webhook_url = f"{public_app_url()}/marketplace/stripe-webhook"
    stripe.api_key = secret

    print(f"Target webhook URL: {webhook_url}")
    existing = stripe.WebhookEndpoint.list(limit=100)
    for endpoint in existing.data:
        if endpoint.url == webhook_url:
            print(f"Webhook already registered: {endpoint.id}")
            print("If you lost the signing secret, delete this endpoint in Stripe Dashboard and re-run this script.")
            return 0

    endpoint = stripe.WebhookEndpoint.create(
        url=webhook_url,
        enabled_events=["checkout.session.completed"],
        description="TheNutraMarket buyer checkout",
    )
    print(f"Created webhook: {endpoint.id}")
    print()
    print("Add to .env and Railway:")
    print(f"STRIPE_WEBHOOK_SECRET={endpoint.secret}")
    print()
    print("Then run: ./scripts/push_stripe_env_to_railway.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
