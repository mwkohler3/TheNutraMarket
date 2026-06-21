#!/usr/bin/env python3
"""Seed Shop now listings for National Chemical (sportsnutrition.com ingredient marketplace catalog)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LISTINGS_FILE = ROOT / "data" / "marketplace_listings.json"
SUBS_FILE = ROOT / "data" / "marketplace_supplier_subscriptions.json"

SUPPLIER_COMPANY = "National Chemical"
SUPPLIER_EMAIL = "max@sportsnutrition.com"
SUPPLIER_CODE = "SX-NATCHEM"
ACCESS_CODE = "NM-NATCHEM"

PRODUCTS = [
    {
        "ingredient": "Xanthan Gum — 80 & 200 Mesh",
        "notes": "High-quality xanthan gum in 80-mesh and 200-mesh grades. Thickening and stabilizing for powder blends and RTD. GMP verified · National Chemical.",
        "featured": True,
    },
    {
        "ingredient": "Citric Acid — 30–100 Mesh",
        "notes": "Food-grade citric acid, 30–100 mesh. Acidulant, flavor enhancer, and preservative. GMP verified · National Chemical.",
        "featured": True,
    },
    {
        "ingredient": "DL-Malic Acid",
        "notes": "DL-malic acid for flavor enhancement and acidulation. Common in pre-workout and hydration formulas. GMP verified · National Chemical.",
        "featured": True,
    },
    {
        "ingredient": "DHA Powder 20%",
        "notes": "Microencapsulated DHA powder at 20% concentration. Capsules, powders, and functional foods. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Creatine Monohydrate — 200 & 80 Mesh",
        "notes": "Micronized creatine monohydrate in 200-mesh and 80-mesh grades. GMP verified · National Chemical.",
        "featured": True,
    },
    {
        "ingredient": "D-Glucosamine Hydrochloride — 40 & 80 Mesh",
        "notes": "D-glucosamine HCl in 40-mesh and 80-mesh grades. Joint health formulations. GMP verified · National Chemical.",
    },
    {
        "ingredient": "D-Glucosamine Sulfate KCl — 40 & 80 Mesh",
        "notes": "D-glucosamine sulfate potassium chloride in 40 and 80 mesh. GMP verified · National Chemical.",
    },
    {
        "ingredient": "MSM — 20–40 Mesh & 40–80 Mesh",
        "notes": "Methylsulfonylmethane (MSM) in 20–40 mesh and 40–80 mesh grades. Joint and recovery support. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Collagen Peptide — Bovine & Fish",
        "notes": "Hydrolyzed collagen peptides from bovine and marine sources. Excellent solubility. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Caffeine Anhydrous",
        "notes": "High-purity caffeine anhydrous for pre-workout, energy, and thermogenic formulas. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Taurine — With & Without Anti-Caking",
        "notes": "Taurine with and without anti-caking agent. Energy, pre-workout, and recovery applications. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Pea Protein — 80% & 85%",
        "notes": "Plant-based pea protein isolate at 80% and 85% protein. Vegan, allergen-friendly. GMP verified · National Chemical.",
    },
    {
        "ingredient": "MCT Powder 70%",
        "notes": "Spray-dried MCT powder at 70% oil load. Ketogenic and cognitive performance products. GMP verified · National Chemical.",
    },
    {
        "ingredient": "MCT Oil",
        "notes": "Pure medium-chain triglyceride oil from coconut. Bulk for liquids, softgels, and RTD. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Polydextrose",
        "notes": "Soluble fiber bulking agent and prebiotic for bars, powders, and functional foods. GMP verified · National Chemical.",
    },
    {
        "ingredient": "L-Carnitine Base",
        "notes": "Pure L-carnitine base powder. Fat metabolism and energy production. GMP verified · National Chemical.",
    },
    {
        "ingredient": "L-Aspartic Acid",
        "notes": "L-aspartic acid for amino blends and performance formulations. GMP verified · National Chemical.",
    },
    {
        "ingredient": "L-Lysine Hydrochloride — 60 Mesh",
        "notes": "L-lysine HCl at 60 mesh. Essential amino acid for protein synthesis. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Erythritol — 20–60 Mesh",
        "notes": "Natural zero-calorie sweetener, 20–60 mesh. Non-glycemic. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Sucralose — 100 Mesh",
        "notes": "High-intensity sweetener at 100 mesh. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Xylitol — 10–30 Mesh",
        "notes": "Sugar alcohol sweetener, 10–30 mesh granulation. Chewable and flavored formats. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Ascorbic Acid (Vitamin C)",
        "notes": "Pure ascorbic acid powder. Antioxidant vitamin for immune and recovery formulas. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Biotin",
        "notes": "Biotin (Vitamin B7) for hair, skin, nails, and metabolic health. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Inositol",
        "notes": "Myo-inositol powder. Mood, cognitive, and hormonal balance applications. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Nicotinamide (Vitamin B3)",
        "notes": "Nicotinamide (niacinamide) powder. Non-flushing vitamin B3. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Vitamin B1 Mononitrate",
        "notes": "Thiamine mononitrate (Vitamin B1). Stable form for manufacturing. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Vitamin B1 HCl",
        "notes": "Thiamine hydrochloride (Vitamin B1 HCl). Highly bioavailable thiamine. GMP verified · National Chemical.",
    },
    {
        "ingredient": "Vitamin B6 (Pyridoxine HCl)",
        "notes": "Pyridoxine hydrochloride (Vitamin B6). B-complex and sports formulas. GMP verified · National Chemical.",
    },
]


def upsert_supplier(subs: list[dict]) -> list[dict]:
    for sub in subs:
        if _norm_company(sub.get("company_name", "")) == _norm_company(SUPPLIER_COMPANY):
            sub.update(
                {
                    "contact_email": SUPPLIER_EMAIL,
                    "public_supplier_code": SUPPLIER_CODE,
                    "status": "active",
                }
            )
            return subs
    subs.append(
        {
            "id": str(uuid.uuid4()),
            "company_name": SUPPLIER_COMPANY,
            "contact_name": "Sales",
            "contact_email": SUPPLIER_EMAIL,
            "monthly_amount_usd": 0.0,
            "billing_provider": "manual",
            "public_supplier_code": SUPPLIER_CODE,
            "access_code": ACCESS_CODE,
            "status": "active",
            "started_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    return subs


def _norm_company(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def build_listings(base_date: datetime) -> list[dict]:
    rows: list[dict] = []
    for i, product in enumerate(PRODUCTS):
        slug = product["ingredient"].lower().replace(" ", "-").replace("/", "-")[:40]
        rows.append(
            {
                "id": f"nc-{slug}-{i + 1:02d}",
                "category": "Ingredient",
                "supplier_company": SUPPLIER_COMPANY,
                "supplier_contact_email": SUPPLIER_EMAIL,
                "supplier_public_code": SUPPLIER_CODE,
                "ingredient": product["ingredient"],
                "unit": "kg",
                "price_per_kg": 0,
                "price_on_request": True,
                "quantity_kg": 100000.0,
                "coa_document": "GMP-COA-available-on-request",
                "expires_on": "",
                "notes": product["notes"],
                "created_at": (base_date - timedelta(minutes=i)).isoformat(timespec="seconds"),
                "sale_mode": "buy_now",
                "featured": bool(product.get("featured")),
                "platform_sourced": True,
            }
        )
    return rows


def main() -> None:
    base_date = datetime.now().replace(microsecond=0)
    existing = json.loads(LISTINGS_FILE.read_text(encoding="utf-8"))
    auction_listings = [x for x in existing if str(x.get("sale_mode") or "").lower() == "auction"]
    nc_listings = build_listings(base_date)
    merged = nc_listings + auction_listings
    LISTINGS_FILE.write_text(json.dumps(merged, indent=2), encoding="utf-8")

    subs = json.loads(SUBS_FILE.read_text(encoding="utf-8"))
    subs = upsert_supplier(subs)
    SUBS_FILE.write_text(json.dumps(subs, indent=2), encoding="utf-8")

    print(f"Wrote {len(nc_listings)} National Chemical shop listings + kept {len(auction_listings)} auction lots.")


if __name__ == "__main__":
    main()
