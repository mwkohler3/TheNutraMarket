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
        "description": "High-quality xanthan gum available in 80-mesh and 200-mesh grades. Ideal for thickening, stabilizing, and improving texture in powder blends and ready-to-drink formulations.",
        "category_label": "Functional Ingredients",
        "featured": True,
    },
    {
        "ingredient": "Citric Acid — 30–100 Mesh",
        "description": "Food-grade citric acid available in 30–100 mesh particle sizes. Widely used as an acidulant, flavor enhancer, and preservative in sports nutrition products.",
        "category_label": "Functional Ingredients",
        "featured": True,
    },
    {
        "ingredient": "DL-Malic Acid",
        "description": "DL-malic acid for use as a flavor enhancer and acidulant. Common in pre-workout and hydration formulations for a smooth, tart taste profile.",
        "category_label": "Functional Ingredients",
        "featured": True,
    },
    {
        "ingredient": "DHA Powder 20%",
        "description": "Microencapsulated DHA powder at 20% concentration. Suitable for capsules, powder blends, and functional food applications requiring omega-3 fortification.",
        "category_label": "Oils & Fatty Acids",
    },
    {
        "ingredient": "Creatine Monohydrate — 200 & 80 Mesh",
        "description": "Micronized creatine monohydrate available in 200-mesh and 80-mesh grades. One of the most researched and effective performance ingredients on the market.",
        "category_label": "Amino Acids & Performance",
        "featured": True,
    },
    {
        "ingredient": "D-Glucosamine Hydrochloride — 40 & 80 Mesh",
        "description": "D-glucosamine hydrochloride available in 40-mesh and 80-mesh grades. A key ingredient for joint health and mobility supplement formulations.",
        "category_label": "Joint & Recovery",
    },
    {
        "ingredient": "D-Glucosamine Sulfate KCl — 40 & 80 Mesh",
        "description": "D-glucosamine sulfate potassium chloride complex in 40 and 80 mesh. Clinically studied form commonly used in joint support products.",
        "category_label": "Joint & Recovery",
    },
    {
        "ingredient": "MSM — 20–40 Mesh & 40–80 Mesh",
        "description": "Methylsulfonylmethane (MSM) available in 20–40 mesh and 40–80 mesh grades. Supports joint health, recovery, and inflammation management.",
        "category_label": "Joint & Recovery",
    },
    {
        "ingredient": "Collagen Peptide — Bovine & Fish",
        "description": "Hydrolyzed collagen peptides available from both bovine and marine (fish) sources. Supports joint, skin, and connective tissue health. Excellent solubility.",
        "category_label": "Proteins",
    },
    {
        "ingredient": "Caffeine Anhydrous",
        "description": "High-purity caffeine anhydrous powder. A staple ingredient in pre-workout, energy, and fat-burning formulations across the sports nutrition industry.",
        "category_label": "Stimulants & Energy",
    },
    {
        "ingredient": "Taurine — With & Without Anti-Caking",
        "description": "Taurine available with and without anti-caking agent. Widely used in energy drinks, pre-workouts, and recovery formulas for its performance and hydration benefits.",
        "category_label": "Amino Acids & Performance",
    },
    {
        "ingredient": "Pea Protein — 80% & 85%",
        "description": "Plant-based pea protein isolate available at 80% and 85% protein concentrations. Allergen-friendly, vegan, and ideal for clean-label sports nutrition products.",
        "category_label": "Proteins",
    },
    {
        "ingredient": "MCT Powder 70%",
        "description": "Spray-dried MCT powder at 70% oil load. Easy to blend into powder formulations for energy, ketogenic products, and cognitive performance supplements.",
        "category_label": "Oils & Fatty Acids",
    },
    {
        "ingredient": "MCT Oil",
        "description": "Pure medium-chain triglyceride oil sourced from coconut. Available in bulk for liquid supplements, softgels, and ready-to-drink applications.",
        "category_label": "Oils & Fatty Acids",
    },
    {
        "ingredient": "Polydextrose",
        "description": "Soluble fiber ingredient used as a bulking agent, sugar replacer, and prebiotic in sports nutrition bars, powders, and functional foods.",
        "category_label": "Functional Ingredients",
    },
    {
        "ingredient": "L-Carnitine Base",
        "description": "Pure L-carnitine base powder. Supports fat metabolism and energy production. Used in fat-burning, endurance, and weight management formulations.",
        "category_label": "Amino Acids & Performance",
    },
    {
        "ingredient": "L-Aspartic Acid",
        "description": "L-aspartic acid for use in amino acid blends and testosterone support formulations. Plays a role in energy metabolism and neurotransmitter production.",
        "category_label": "Amino Acids & Performance",
    },
    {
        "ingredient": "L-Lysine Hydrochloride — 60 Mesh",
        "description": "L-lysine HCl at 60 mesh. An essential amino acid important for protein synthesis, immune function, and collagen formation.",
        "category_label": "Amino Acids & Performance",
    },
    {
        "ingredient": "Erythritol — 20–60 Mesh",
        "description": "Natural zero-calorie sweetener available in 20–60 mesh. Non-glycemic, tooth-friendly, and commonly used in sugar-free sports nutrition products.",
        "category_label": "Sweeteners",
    },
    {
        "ingredient": "Sucralose — 100 Mesh",
        "description": "High-intensity artificial sweetener at 100 mesh. Approximately 600x sweeter than sugar. Used in small quantities across powder and liquid formulations.",
        "category_label": "Sweeteners",
    },
    {
        "ingredient": "Xylitol — 10–30 Mesh",
        "description": "Sugar alcohol sweetener in 10–30 mesh granulation. Offers a cooling mouthfeel and is commonly used in chewable and flavored supplement formats.",
        "category_label": "Sweeteners",
    },
    {
        "ingredient": "Ascorbic Acid (Vitamin C)",
        "description": "Pure ascorbic acid powder. Essential antioxidant vitamin used in immune support, recovery, and general health supplement formulations.",
        "category_label": "Vitamins",
    },
    {
        "ingredient": "Biotin",
        "description": "Biotin (Vitamin B7) for hair, skin, nails, and metabolic health formulations. Available in various concentrations for flexible dosing.",
        "category_label": "Vitamins",
    },
    {
        "ingredient": "Inositol",
        "description": "Myo-inositol powder. Supports mood, cognitive function, and hormonal balance. Increasingly popular in wellness and sports nutrition products.",
        "category_label": "Vitamins",
    },
    {
        "ingredient": "Nicotinamide (Vitamin B3)",
        "description": "Nicotinamide (niacinamide) powder. A non-flushing form of vitamin B3 that supports energy metabolism and cellular health.",
        "category_label": "Vitamins",
    },
    {
        "ingredient": "Vitamin B1 Mononitrate",
        "description": "Thiamine mononitrate (Vitamin B1) powder. Supports energy metabolism and nervous system function. Stable form ideal for supplement manufacturing.",
        "category_label": "Vitamins",
    },
    {
        "ingredient": "Vitamin B1 HCl",
        "description": "Thiamine hydrochloride (Vitamin B1 HCl). Highly bioavailable form of thiamine used in multivitamins, B-complex blends, and performance supplements.",
        "category_label": "Vitamins",
    },
    {
        "ingredient": "Vitamin B6 (Pyridoxine HCl)",
        "description": "Pyridoxine hydrochloride (Vitamin B6). Supports protein metabolism, neurotransmitter synthesis, and immune function. Essential in B-complex and sports formulas.",
        "category_label": "Vitamins",
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
                "description": product["description"],
                "category_label": product["category_label"],
                "unit": "kg",
                "price_per_kg": 0,
                "price_on_request": True,
                "quantity_kg": 100000.0,
                "coa_document": "",
                "expires_on": "",
                "notes": product["description"],
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
