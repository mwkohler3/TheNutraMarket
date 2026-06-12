#!/usr/bin/env python3
"""Seed 50 demo marketplace listings + supplier subscriptions."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LISTINGS_FILE = ROOT / "data" / "marketplace_listings.json"
SUBS_FILE = ROOT / "data" / "marketplace_supplier_subscriptions.json"

SUPPLIERS = [
    ("Nordic Actives BV", "supply@nordicactives.example", "SX-NORD01"),
    ("Atlas BioIngredients", "inventory@atlasbio.example", "SX-ATLAS1"),
    ("Pacific Amino Co.", "sales@pacificamino.example", "SX-PACAM1"),
    ("FlavorChem Partners", "orders@flavorchem.example", "SX-FLCHEM"),
    ("NutraPack Solutions", "inventory@nutrapack.example", "SX-NPACK1"),
    ("CreatineSource Ltd", "trade@creatinesource.example", "SX-CRTSRC"),
    ("Herbal Extracts Global", "export@herbalextract.example", "SX-HERBEX"),
    ("SweetWorks Naturals", "bulk@sweetworks.example", "SX-SWTWRK"),
    ("ContainerWorks Inc", "wholesale@containerworks.example", "SX-CONWRK"),
    ("ProBlend Manufacturing", "supply@problend.example", "SX-PBLEND"),
    ("Vitamin Matrix Labs", "orders@vitmatrix.example", "SX-VITMTX"),
    ("Collagen Proteins Int'l", "trade@collagenpro.example", "SX-COLPRO"),
    ("CapsuleTech USA", "sales@capsuletech.example", "SX-CAPTEC"),
    ("Botanical Ingredients LLC", "bulk@botanicaling.example", "SX-BOTING"),
    ("LabelRight Printing", "orders@labelright.example", "SX-LBLRGT"),
    ("WheyDirect Exports", "export@wheydirect.example", "SX-WHEYDX"),
    ("Stevia Pure Co.", "sales@steviapure.example", "SX-STVPRE"),
    ("PouchPack Industries", "inventory@pouchpack.example", "SX-POUCHP"),
    ("Beta-Alanine Systems", "supply@betaalanine.example", "SX-BTAALN"),
    ("Citrus Flavor House", "orders@citrusflavor.example", "SX-CITFLV"),
]

PRODUCTS = [
    ("Ingredient", "Creatine Monohydrate 200 Mesh", "kg", 4.2, 18000, "coa-creatine-200mesh.pdf", "48-hour domestic stock"),
    ("Ingredient", "Whey Protein Isolate 90%", "kg", 8.9, 6200, "coa-wpi90-lot441.pdf", "EU origin, instantized"),
    ("Ingredient", "Collagen Peptides Bovine", "kg", 6.75, 9500, "coa-collagen-bovine.pdf", "Near-expiry liquidation"),
    ("Ingredient", "Beta-Alanine Fine Powder", "kg", 5.1, 4400, "coa-beta-alanine.pdf", "Best bid wins"),
    ("Ingredient", "L-Citrulline Malate 2:1", "kg", 7.4, 3100, "coa-citrulline-malate.pdf", "Urgent domestic inventory"),
    ("Ingredient", "BCAA 2:1:1 Instant", "kg", 9.2, 2800, "coa-bcaa-instant.pdf", "MOQ breaks at 500kg"),
    ("Ingredient", "HMB Calcium", "kg", 11.5, 1200, "coa-hmb-ca.pdf", "GMP certified site"),
    ("Ingredient", "Taurine USP", "kg", 3.8, 7600, "coa-taurine-usp.pdf", "Price drops at quantity thresholds"),
    ("Ingredient", "Glutamine Micronized", "kg", 4.95, 5200, "coa-glutamine-micro.pdf", "Overstock clearance"),
    ("Ingredient", "Caffeine Anhydrous", "kg", 12.3, 900, "coa-caffeine-anhydrous.pdf", "Export docs available"),
    ("Ingredient", "Magnesium Glycinate", "kg", 14.2, 2100, "coa-mag-glycinate.pdf", "Pharma grade"),
    ("Ingredient", "Zinc Bisglycinate", "kg", 18.6, 850, "coa-zinc-bisglycinate.pdf", "Low MOQ available"),
    ("Ingredient", "Vitamin D3 Cholecalciferol", "kg", 42.0, 120, "coa-vitd3-cholecalciferol.pdf", "Cold chain optional"),
    ("Ingredient", "Vitamin C Ascorbic Acid", "kg", 3.2, 11000, "coa-vitamin-c.pdf", "48-hour liquidation"),
    ("Ingredient", "Electrolyte Blend Premix", "kg", 6.1, 3400, "coa-electrolyte-premix.pdf", "Custom blend surplus"),
    ("Ingredient", "Ashwagandha KSM-66 Extract", "kg", 22.5, 680, "coa-ashwagandha-ksm66.pdf", "Organic certified"),
    ("Ingredient", "Rhodiola Rosea Extract 3%", "kg", 19.8, 420, "coa-rhodiola-3pct.pdf", "Standardized extract"),
    ("Ingredient", "Turmeric Curcumin 95%", "kg", 16.4, 1500, "coa-curcumin-95.pdf", "Non-GMO verified"),
    ("Ingredient", "Green Tea Extract EGCG", "kg", 21.0, 560, "coa-green-tea-egcg.pdf", "Instant inventory"),
    ("Ingredient", "Beet Root Powder", "kg", 5.6, 2900, "coa-beet-root.pdf", "Color-stable lot"),
    ("Ingredient", "Sodium Bicarbonate", "kg", 1.85, 14000, "coa-sodium-bicarbonate.pdf", "Food grade bulk"),
    ("Ingredient", "MCT Oil Powder 70%", "kg", 10.8, 1800, "coa-mct-powder-70.pdf", "Keto formulation surplus"),
    ("Ingredient", "EAA Full Spectrum", "kg", 13.4, 2200, "coa-eaa-blend.pdf", "Vegan suitable"),
    ("Ingredient", "Hydrolyzed Whey Peptides", "kg", 11.2, 1600, "coa-hydro-whey.pdf", "Fast absorption grade"),
    ("Flavoring", "Natural Vanilla Bourbon Type", "kg", 24.5, 380, "coa-vanilla-bourbon.pdf", "TTB compliant"),
    ("Flavoring", "Natural Chocolate Fudge Type", "kg", 19.2, 520, "coa-chocolate-fudge.pdf", "Heat stable"),
    ("Flavoring", "Natural Strawberry Type", "kg", 17.8, 610, "coa-strawberry-nat.pdf", "Clean label"),
    ("Flavoring", "Natural Mango Type", "kg", 18.4, 440, "coa-mango-nat.pdf", "Tropical profile"),
    ("Flavoring", "Stevia Reb M 95%", "kg", 88.0, 95, "coa-stevia-rebm95.pdf", "High potency sweetener"),
    ("Flavoring", "Monk Fruit Extract 25%", "kg", 72.0, 110, "coa-monk-fruit-25.pdf", "Natural sweetener"),
    ("Flavoring", "Sucralose Micronized", "kg", 28.5, 240, "coa-sucralose-micro.pdf", "Pharma grade"),
    ("Flavoring", "Natural Blue Raspberry Type", "kg", 16.9, 330, "coa-blue-raspberry.pdf", "Pre-workout favorite"),
    ("Flavoring", "Natural Lemon Lime Type", "kg", 15.5, 470, "coa-lemon-lime.pdf", "Hydration SKUs"),
    ("Flavoring", "Natural Cookies & Cream Type", "kg", 20.1, 290, "coa-cookies-cream.pdf", "Protein powder pairing"),
    ("Flavoring", "Natural Peanut Butter Type", "kg", 21.3, 260, "coa-peanut-butter.pdf", "Allergen controlled"),
    ("Flavoring", "Natural Watermelon Type", "kg", 16.2, 390, "coa-watermelon-nat.pdf", "Summer seasonal overstock"),
    ("Flavoring", "Acesulfame Potassium", "kg", 9.8, 680, "coa-ace-k.pdf", "Synergistic sweetener blend"),
    ("Flavoring", "Natural Mint Type", "kg", 18.7, 210, "coa-mint-nat.pdf", "Cooling agent compatible"),
    ("Packaging", "HDPE White 175cc Bottle + 38mm Cap", "unit", 0.19, 85000, "spec-hdpe-175cc.pdf", "Includes child-resistant cap"),
    ("Packaging", "PET Clear 2L Canister + Scoop", "unit", 1.42, 12000, "spec-pet-2l-canister.pdf", "Protein powder format"),
    ("Packaging", "Stand-Up Pouch Matte 2kg", "unit", 0.34, 42000, "spec-pouch-2kg-matte.pdf", "MOQ 5,000 units"),
    ("Packaging", "Stand-Up Pouch Gloss 500g", "unit", 0.12, 96000, "spec-pouch-500g-gloss.pdf", "48-hour ship domestic"),
    ("Packaging", "HDPE Black 750cc Bottle", "unit", 0.28, 28000, "spec-hdpe-750cc-black.pdf", "UV protective"),
    ("Packaging", "Aluminum Scoop 30cc", "unit", 0.06, 150000, "spec-scoop-30cc.pdf", "Embossing available"),
    ("Packaging", "Shrink Sleeve Label Roll 500m", "unit", 0.08, 22000, "spec-shrink-sleeve.pdf", "Full-color digital print"),
    ("Packaging", "Corrugated Shipper 12-Count", "unit", 1.15, 8500, "spec-shipper-12ct.pdf", "E-commerce ready"),
    ("Packaging", "Glass Amber 120cc Bottle", "unit", 0.52, 14000, "spec-glass-120cc.pdf", "Premium capsule line"),
    ("Packaging", "Child-Resistant Cap 38mm", "unit", 0.04, 210000, "spec-cr-cap-38mm.pdf", "CRC certified"),
    ("Packaging", "Foil Sachet 30g Single Serve", "unit", 0.07, 320000, "spec-foil-sachet-30g.pdf", "Stick pack surplus"),
    ("Packaging", "Desiccant Packet 1g Silica", "unit", 0.02, 500000, "spec-desiccant-1g.pdf", "Food safe"),
]


def main() -> None:
    base_date = datetime(2026, 6, 1, 10, 0, 0)
    subs = []
    for i, (company, email, code) in enumerate(SUPPLIERS):
        subs.append(
            {
                "id": str(uuid.uuid4()),
                "company_name": company,
                "contact_name": "",
                "contact_email": email,
                "monthly_amount_usd": 0.0,
                "billing_provider": "manual",
                "public_supplier_code": code,
                "access_code": f"NM-{code.replace('SX-', '')[:8]}",
                "status": "active",
                "started_at": (base_date - timedelta(days=30 + i)).isoformat(timespec="seconds"),
            }
        )

    listings = []
    for i, (category, name, unit, price, qty, coa, notes) in enumerate(PRODUCTS):
        supplier = SUPPLIERS[i % len(SUPPLIERS)]
        company, email, code = supplier
        listings.append(
            {
                "id": f"demo-listing-{i + 1:03d}",
                "category": category,
                "supplier_company": company,
                "supplier_contact_email": email,
                "ingredient": name,
                "unit": unit,
                "price_per_kg": price,
                "quantity_kg": float(qty),
                "coa_document": coa,
                "expires_on": (base_date + timedelta(days=60 + (i * 3) % 180)).strftime("%Y-%m-%d"),
                "notes": notes,
                "created_at": (base_date + timedelta(hours=i)).isoformat(timespec="seconds"),
                "supplier_public_code": code,
            }
        )

    LISTINGS_FILE.write_text(json.dumps(listings, indent=2), encoding="utf-8")
    SUBS_FILE.write_text(json.dumps(subs, indent=2), encoding="utf-8")
    print(f"Wrote {len(listings)} listings and {len(subs)} supplier subscriptions.")


if __name__ == "__main__":
    main()
