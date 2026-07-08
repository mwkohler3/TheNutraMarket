#!/usr/bin/env python3
"""Seed Live Auction lots (National Chemical overstock/clearance) with live end dates.

Keeps all Shop now (buy_now) listings and replaces auction lots with a fresh set
of open lots that end in the near future, so the Live Auction tab is never empty.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LISTINGS_FILE = ROOT / "data" / "marketplace_listings.json"

SUPPLIER_COMPANY = "National Chemical"
SUPPLIER_EMAIL = "max@sportsnutrition.com"
SUPPLIER_CODE = "SX-NATCHEM"

# (ingredient, category_label, list_price_per_kg, quantity_kg, coa, note, ends_in_hours)
LOTS = [
    (
        "Creatine Monohydrate — 200 Mesh",
        "Amino Acids & Performance",
        4.20,
        18000.0,
        "coa-creatine-200mesh.pdf",
        "Overstock clearance · domestic stock",
        72,
    ),
    (
        "Collagen Peptides — Bovine",
        "Proteins",
        6.75,
        9500.0,
        "coa-collagen-bovine.pdf",
        "Near-expiry liquidation · move fast",
        108,
    ),
    (
        "Beta-Alanine — Fine Powder",
        "Amino Acids & Performance",
        5.10,
        4400.0,
        "coa-beta-alanine.pdf",
        "Overstock · urgent lot",
        156,
    ),
    (
        "Caffeine Anhydrous",
        "Stimulants & Energy",
        7.40,
        6200.0,
        "coa-caffeine-anhydrous.pdf",
        "Surplus inventory · best bid wins",
        204,
    ),
    (
        "Citric Acid — 30–100 Mesh",
        "Functional Ingredients",
        1.95,
        26000.0,
        "coa-citric-acid.pdf",
        "Bulk overstock · competitive bidding",
        252,
    ),
    (
        "Erythritol — 20–60 Mesh",
        "Sweeteners",
        3.20,
        15000.0,
        "coa-erythritol.pdf",
        "Clearance lot · sweetener overstock",
        300,
    ),
]


def build_auction_lots(base: datetime) -> list[dict]:
    rows: list[dict] = []
    for i, (ingredient, category_label, list_price, qty, coa, note, ends_in_hours) in enumerate(LOTS):
        starting = round(list_price * 0.82, 2)
        rows.append(
            {
                "id": f"nc-auction-{i + 1:02d}",
                "category": "Ingredient",
                "supplier_company": SUPPLIER_COMPANY,
                "supplier_contact_email": SUPPLIER_EMAIL,
                "supplier_public_code": SUPPLIER_CODE,
                "ingredient": ingredient,
                "category_label": category_label,
                "unit": "kg",
                "price_per_kg": list_price,
                "quantity_kg": qty,
                "coa_document": coa,
                "expires_on": "",
                "notes": note,
                "created_at": (base - timedelta(minutes=i)).isoformat(timespec="seconds"),
                "sale_mode": "auction",
                "starting_bid_per_kg": starting,
                "bid_increment": 0.05,
                "auction_ends_at": (base + timedelta(hours=ends_in_hours)).isoformat(timespec="seconds"),
                "platform_sourced": True,
            }
        )
    return rows


def main() -> None:
    base = datetime.now().replace(microsecond=0)
    existing = json.loads(LISTINGS_FILE.read_text(encoding="utf-8"))
    buy_now = [x for x in existing if str(x.get("sale_mode") or "").lower() != "auction"]
    auction_lots = build_auction_lots(base)
    merged = buy_now + auction_lots
    LISTINGS_FILE.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"Kept {len(buy_now)} shop listings + wrote {len(auction_lots)} live auction lots.")


if __name__ == "__main__":
    main()
