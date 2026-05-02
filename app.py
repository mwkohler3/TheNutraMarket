from __future__ import annotations

from collections import deque
from datetime import datetime
import os
from pathlib import Path
import json
import uuid

try:
    import stripe
except ImportError:  # pragma: no cover
    stripe = None  # type: ignore

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

try:
    from duckduckgo_search import DDGS
except ImportError:  # pragma: no cover
    DDGS = None

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-lead-pipeline-secret")
# Correct scheme/host when behind Cloudflare Tunnel, ngrok, etc. (for Stripe return URLs and sessions).
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
if os.environ.get("SESSION_COOKIE_SECURE", "").lower() in ("1", "true", "yes"):
    app.config["SESSION_COOKIE_SECURE"] = True

DATA_DIR = Path(__file__).parent / "data"
LEADS_FILE = DATA_DIR / "leads.json"
EXCLUSIVES_FILE = DATA_DIR / "exclusives.json"
MARKETPLACE_LISTINGS_FILE = DATA_DIR / "marketplace_listings.json"
MARKETPLACE_ALERTS_FILE = DATA_DIR / "marketplace_alerts.json"
MARKETPLACE_DEALS_FILE = DATA_DIR / "marketplace_deals.json"
MARKETPLACE_COMMITS_FILE = DATA_DIR / "marketplace_commits.json"
MARKETPLACE_SUPPLIER_SUBSCRIPTIONS_FILE = DATA_DIR / "marketplace_supplier_subscriptions.json"
MARKETPLACE_FORUM_THREADS_FILE = DATA_DIR / "marketplace_forum_threads.json"
MARKETPLACE_SUPPLIER_RATINGS_FILE = DATA_DIR / "marketplace_supplier_ratings.json"
MARKETPLACE_AGREEMENT_SUBMISSIONS_FILE = DATA_DIR / "marketplace_agreement_submissions.json"
MARKETPLACE_VIG_RATE = 0.05
SUPPLIER_SUBSCRIPTION_MONTHLY_USD = 100.0
MARKETPLACE_AGREEMENT_VERSION = "v1-brokered-marketplace-terms"
SESSION_PENDING_COMMIT_KEY = "marketplace_pending_commit"

# Words that must not drive listing/forum keyword search (they match almost everything).
_MARKETPLACE_ASSISTANT_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "are",
        "but",
        "not",
        "you",
        "all",
        "can",
        "her",
        "was",
        "one",
        "our",
        "out",
        "get",
        "has",
        "him",
        "his",
        "how",
        "its",
        "may",
        "new",
        "now",
        "old",
        "see",
        "two",
        "who",
        "did",
        "use",
        "way",
        "too",
        "any",
        "try",
        "let",
        "put",
        "end",
        "why",
        "ask",
        "had",
        "tell",
        "very",
        "when",
        "come",
        "could",
        "would",
        "there",
        "their",
        "what",
        "which",
        "about",
        "after",
        "before",
        "from",
        "with",
        "have",
        "this",
        "that",
        "these",
        "those",
        "your",
        "into",
        "only",
        "some",
        "than",
        "them",
        "then",
        "also",
        "each",
        "just",
        "like",
        "make",
        "most",
        "such",
        "well",
        "been",
        "call",
        "does",
        "doing",
        "help",
        "here",
        "need",
        "want",
        "know",
        "work",
        "find",
        "give",
        "look",
        "more",
        "back",
        "over",
        "should",
        "still",
        "being",
        "both",
        "during",
        "etc",
        "buy",
        "sell",
        "using",
        "she",
        "say",
        "much",
        "does",
        "really",
        "please",
        "thanks",
        "thank",
        "hello",
        "hi",
        "hey",
    }
)

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
STRIPE_SUPPLIER_PRICE_ID = os.environ.get("STRIPE_SUPPLIER_PRICE_ID", "").strip()
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_CHECKOUT_ENABLED = bool(stripe and STRIPE_SECRET_KEY and STRIPE_SUPPLIER_PRICE_ID)
WEDGE_PRODUCT = "Ingredient Marketplace"
WEDGE_PHASE_COPY = (
    "Global B2B marketplace across ingredients, packaging, and merchandise. "
    "Match vetted suppliers with qualified buyers based on spec, MOQ, region, and COA documentation."
)
DEFAULT_VALUE_PITCH = (
    "Match vetted suppliers to brands, manufacturers, and distributors across ingredients, packaging, and merchandise."
)

STAGES = ["New", "Qualified", "Contacted", "Negotiation", "Won", "Lost"]
SALES_REPS = ["Unassigned", "Maya", "Jordan", "Chris", "Taylor", "Sam"]
LANES = ["Demand (buyer)", "Supply (supplier)"]
REGIONS = ["Global", "Americas", "Europe", "UK/Ireland", "MENA", "APAC", "Africa", "Oceania"]
SEGMENTS = [
    "Supplement brand",
    "Sports nutrition brand",
    "CMO / private label mfg",
    "Functional food & beverage",
    "Distributor / importer",
    "Ingredient / raw supplier",
    "Packaging supplier",
    "Flavor house",
    "Other",
]
LEAD_SOURCE_TYPES = [
    "LinkedIn",
    "Trade show / event",
    "Exhibitor list",
    "Industry association",
    "Referral / warm intro",
    "Website / inbound",
    "Cold call",
    "Discovery tool (search)",
    "Other",
]
TOUCH_CHANNELS = ["Email", "LinkedIn DM", "LinkedIn connect note", "Phone", "Voicemail", "WhatsApp", "In-person", "Other"]
LOSS_REASONS = [
    "No fit / outside ICP",
    "Incumbent supplier locked",
    "No budget",
    "Bad timing",
    "No response / ghosted",
    "Chose competitor",
    "Compliance / legal block",
    "Other",
]
VOLUME_BANDS = ["Pilot / trial only", "SMB repeat buys", "Mid-market", "Enterprise / high SKU count"]
ICP_SCORES = ["", "1", "2", "3", "4", "5"]
DEFAULT_EXTENDED = {
    "lane": "",
    "region": "",
    "segment": "",
    "lead_source_type": "",
    "lead_source_detail": "",
    "contact_name": "",
    "contact_title": "",
    "contact_email": "",
    "contact_phone": "",
    "categories_sourcing": "",
    "moq_notes": "",
    "icp_score": "",
    "est_volume_band": "",
    "loss_reason": "",
    "touch_log": [],
}
CORE_INGREDIENTS = [
    "collagen",
    "creatine",
    "electrolyte",
    "protein",
    "preworkout",
    "greens",
    "nootropic",
    "vitamin",
    "mineral",
]

# Geo tokens per CRM region bucket — used only in whitelisted search templates (no user free text).
PIPELINE_REGIONS: dict[str, list[str]] = {
    "Global": ["international", "worldwide nutrition", "global supplement export"],
    "Americas": [
        "United States",
        "Canada",
        "Mexico",
        "Brazil",
        "Colombia",
        "Argentina",
        "Chile",
    ],
    "Europe": [
        "Germany",
        "France",
        "Netherlands",
        "Poland",
        "Italy",
        "Spain",
        "Sweden",
        "Czech Republic",
    ],
    "UK/Ireland": ["United Kingdom", "Ireland", "Scotland"],
    "MENA": ["UAE", "Saudi Arabia", "Turkey", "Israel", "Egypt"],
    "APAC": [
        "India",
        "China",
        "Japan",
        "South Korea",
        "Australia",
        "Singapore",
        "Thailand",
        "Vietnam",
        "Indonesia",
        "Malaysia",
    ],
    "Africa": ["South Africa", "Nigeria", "Kenya", "Morocco"],
    "Oceania": ["Australia", "New Zealand"],
}

CREATINE_PIPELINE_TEMPLATES = [
    "{geo} creatine monohydrate supplement brand",
    "{geo} creatine monohydrate manufacturer",
    "{geo} sports nutrition company creatine powder",
    "{geo} private label supplement contract manufacturer creatine",
    "{geo} dietary supplement creatine monohydrate wholesale",
]

PIPELINE_MAX_QUERIES_PER_RUN = 55
PIPELINE_MAX_NEW_LEADS_PER_RUN = 120
PIPELINE_PER_QUERY_CAP = 12
URL_SKIP_SUBSTRINGS = (
    "google.com/search",
    "youtube.com",
    "facebook.com/",
    "instagram.com",
    "twitter.com/",
    "x.com/",
    "wikipedia.org",
    "linkedin.com/jobs",
    "pinterest.com",
)


def ensure_data_store() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not LEADS_FILE.exists():
        LEADS_FILE.write_text("[]", encoding="utf-8")
    if not EXCLUSIVES_FILE.exists():
        EXCLUSIVES_FILE.write_text(
            json.dumps(
                [
                    {
                        "id": "exclusive-fitsweet-001",
                        "company_name": "FitSweet",
                        "exclusive_item": "Flavor system platform",
                        "status": "Active",
                        "territory": "Global (to be finalized)",
                        "notes": (
                            "Initial exclusive partner record seeded from provided sell sheet. "
                            "Replace with final negotiated scope and channels."
                        ),
                    }
                ],
                indent=2,
            ),
            encoding="utf-8",
        )
    if not MARKETPLACE_LISTINGS_FILE.exists():
        MARKETPLACE_LISTINGS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_ALERTS_FILE.exists():
        MARKETPLACE_ALERTS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_DEALS_FILE.exists():
        MARKETPLACE_DEALS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_COMMITS_FILE.exists():
        MARKETPLACE_COMMITS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_SUPPLIER_SUBSCRIPTIONS_FILE.exists():
        MARKETPLACE_SUPPLIER_SUBSCRIPTIONS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_FORUM_THREADS_FILE.exists():
        MARKETPLACE_FORUM_THREADS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_SUPPLIER_RATINGS_FILE.exists():
        MARKETPLACE_SUPPLIER_RATINGS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_AGREEMENT_SUBMISSIONS_FILE.exists():
        MARKETPLACE_AGREEMENT_SUBMISSIONS_FILE.write_text("[]", encoding="utf-8")


def _safe_load_json_list(path: Path) -> list[dict]:
    ensure_data_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def load_marketplace_listings() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_LISTINGS_FILE)


def save_marketplace_listings(listings: list[dict]) -> None:
    MARKETPLACE_LISTINGS_FILE.write_text(json.dumps(listings, indent=2), encoding="utf-8")


def load_marketplace_alerts() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_ALERTS_FILE)


def save_marketplace_alerts(alerts: list[dict]) -> None:
    MARKETPLACE_ALERTS_FILE.write_text(json.dumps(alerts, indent=2), encoding="utf-8")


def load_marketplace_deals() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_DEALS_FILE)


def save_marketplace_deals(deals: list[dict]) -> None:
    MARKETPLACE_DEALS_FILE.write_text(json.dumps(deals, indent=2), encoding="utf-8")


def load_marketplace_commits() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_COMMITS_FILE)


def save_marketplace_commits(commits: list[dict]) -> None:
    MARKETPLACE_COMMITS_FILE.write_text(json.dumps(commits, indent=2), encoding="utf-8")


def load_agreement_submissions() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_AGREEMENT_SUBMISSIONS_FILE)


def save_agreement_submissions(rows: list[dict]) -> None:
    ensure_data_store()
    MARKETPLACE_AGREEMENT_SUBMISSIONS_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def load_supplier_subscriptions() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_SUPPLIER_SUBSCRIPTIONS_FILE)


def save_supplier_subscriptions(rows: list[dict]) -> None:
    MARKETPLACE_SUPPLIER_SUBSCRIPTIONS_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _norm_company(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _norm_email(s: str) -> str:
    return (s or "").strip().lower()


def supplier_subscription_active(company: str, email: str) -> bool:
    """Active subscription if company name matches (normalized) OR email matches."""
    c = _norm_company(company)
    e = _norm_email(email)
    if not c and not e:
        return False
    for sub in load_supplier_subscriptions():
        st = (sub.get("status") or "active").lower()
        if st not in ("active", "trialing"):
            continue
        sc = _norm_company(sub.get("company_name", ""))
        se = _norm_email(sub.get("contact_email", ""))
        if e and se == e:
            return True
        if c and sc == c:
            return True
    return False


def load_forum_threads() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_FORUM_THREADS_FILE)


def save_forum_threads(threads: list[dict]) -> None:
    MARKETPLACE_FORUM_THREADS_FILE.write_text(json.dumps(threads, indent=2), encoding="utf-8")


def load_supplier_ratings() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_SUPPLIER_RATINGS_FILE)


def save_supplier_ratings(rows: list[dict]) -> None:
    MARKETPLACE_SUPPLIER_RATINGS_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def build_supplier_rating_aggregates() -> dict[str, dict]:
    by_code: dict[str, list[float]] = {}
    for r in load_supplier_ratings():
        code = (r.get("supplier_public_code") or "").strip()
        if not code:
            continue
        try:
            stars = float(r.get("stars", 0))
        except (TypeError, ValueError):
            continue
        if stars < 1 or stars > 5:
            continue
        by_code.setdefault(code, []).append(stars)
    out: dict[str, dict] = {}
    for code, vals in by_code.items():
        if not vals:
            continue
        out[code] = {"avg": round(sum(vals) / len(vals), 2), "count": len(vals)}
    return out


def format_supplier_rating_pill(agg: dict | None) -> str:
    if not agg or not agg.get("count"):
        return "No ratings yet"
    return f"★ {agg['avg']:.1f} ({agg['count']})"


def _all_supplier_public_codes() -> set[str]:
    codes: set[str] = set()
    for s in load_supplier_subscriptions():
        c = s.get("public_supplier_code")
        if c:
            codes.add(str(c))
    for lst in load_marketplace_listings():
        c = lst.get("supplier_public_code")
        if c:
            codes.add(str(c))
    return codes


def _generate_unique_supplier_public_code() -> str:
    existing = _all_supplier_public_codes()
    for _ in range(80):
        cand = "SX-" + uuid.uuid4().hex[:6].upper()
        if cand not in existing:
            return cand
    return "SX-" + uuid.uuid4().hex[:10].upper()


def _find_subscription_row(subs: list[dict], company: str, email: str) -> dict | None:
    ne, nc = _norm_email(email), _norm_company(company)
    if ne:
        for s in subs:
            if _norm_email(s.get("contact_email", "")) == ne:
                return s
    if nc:
        for s in subs:
            if _norm_company(s.get("company_name", "")) == nc:
                return s
    return None


def get_or_assign_supplier_public_code(company: str, email: str) -> str:
    subs = load_supplier_subscriptions()
    row = _find_subscription_row(subs, company, email)
    if row:
        existing = (row.get("public_supplier_code") or "").strip()
        if existing:
            return existing
        code = _generate_unique_supplier_public_code()
        row["public_supplier_code"] = code
        save_supplier_subscriptions(subs)
        return code
    return _generate_unique_supplier_public_code()


def ensure_all_listing_supplier_codes() -> None:
    listings = load_marketplace_listings()
    changed = False
    for lst in listings:
        if lst.get("supplier_public_code"):
            continue
        lst["supplier_public_code"] = get_or_assign_supplier_public_code(
            str(lst.get("supplier_company", "")),
            str(lst.get("supplier_contact_email", "")),
        )
        changed = True
    if changed:
        save_marketplace_listings(listings)


def upsert_local_subscription_from_stripe(
    *,
    company: str,
    email: str,
    contact_name: str,
    customer_id: str | None,
    subscription_id: str | None,
    stripe_status: str,
) -> None:
    subs = load_supplier_subscriptions()
    ne = _norm_email(email)
    row: dict | None = None
    for s in subs:
        if _norm_email(s.get("contact_email", "")) == ne:
            row = s
            break
    if row is None:
        row = {
            "id": str(uuid.uuid4()),
            "company_name": company,
            "contact_email": email,
            "contact_name": contact_name,
            "monthly_amount_usd": SUPPLIER_SUBSCRIPTION_MONTHLY_USD,
            "started_at": datetime.now().isoformat(timespec="seconds"),
        }
        subs.append(row)
    row["company_name"] = company or row.get("company_name", "")
    row["contact_email"] = email or row.get("contact_email", "")
    row["contact_name"] = contact_name or row.get("contact_name", "")
    row["monthly_amount_usd"] = SUPPLIER_SUBSCRIPTION_MONTHLY_USD
    row["billing_provider"] = "stripe"
    if customer_id:
        row["stripe_customer_id"] = customer_id
    if subscription_id:
        row["stripe_subscription_id"] = subscription_id
    row["stripe_status"] = stripe_status
    row["status"] = "active" if stripe_status in ("active", "trialing") else "inactive"
    if not row.get("public_supplier_code"):
        row["public_supplier_code"] = _generate_unique_supplier_public_code()
    save_supplier_subscriptions(subs)


def apply_stripe_subscription_object(sub_data: dict) -> None:
    """Sync a Stripe Subscription object into local JSON (used by webhooks)."""
    meta = sub_data.get("metadata") or {}
    sub_id = sub_data.get("id")
    status = str(sub_data.get("status") or "")
    customer_id = sub_data.get("customer")
    email_hint = _norm_email(str(meta.get("contact_email") or ""))
    company = str(meta.get("company_name") or "").strip()
    subs = load_supplier_subscriptions()
    row: dict | None = None
    if sub_id:
        for s in subs:
            if s.get("stripe_subscription_id") == sub_id:
                row = s
                break
    if row is None and email_hint:
        for s in subs:
            if _norm_email(s.get("contact_email", "")) == email_hint:
                row = s
                break
    if row is None and email_hint:
        upsert_local_subscription_from_stripe(
            company=company,
            email=email_hint,
            contact_name="",
            customer_id=str(customer_id) if customer_id else None,
            subscription_id=str(sub_id) if sub_id else None,
            stripe_status=status,
        )
        return
    if row is None:
        return
    if customer_id:
        row["stripe_customer_id"] = str(customer_id)
    if sub_id:
        row["stripe_subscription_id"] = str(sub_id)
    row["stripe_status"] = status
    row["billing_provider"] = "stripe"
    row["status"] = "active" if status in ("active", "trialing") else "inactive"
    if company:
        row["company_name"] = company
    if email_hint:
        row["contact_email"] = email_hint
    if not row.get("public_supplier_code"):
        row["public_supplier_code"] = _generate_unique_supplier_public_code()
    save_supplier_subscriptions(subs)


def _marketplace_assistant_meaningful_tokens(low: str) -> list[str]:
    raw = [t for t in low.replace(",", " ").split() if len(t) > 2]
    return [t for t in raw if t not in _MARKETPLACE_ASSISTANT_STOPWORDS]


def marketplace_assistant_reply(message: str) -> str:
    """Rule-based assistant + search listings, alerts, and forum (no external API)."""
    raw = (message or "").strip()
    if not raw:
        return "Ask me anything—for example: ingredient name, brokerage fee, supplier subscription, COA, or forum."

    low = raw.lower()
    pct = int(MARKETPLACE_VIG_RATE * 100)
    monthly = int(SUPPLIER_SUBSCRIPTION_MONTHLY_USD)

    fee_keys = (
        "fee",
        "brokerage",
        "commission",
        "vig",
        "percent",
        "%",
        "take",
        "cut",
        "platform fee",
        "marketplace fee",
    )
    if any(k in low for k in fee_keys):
        return (
            f"The brokerage fee is {pct}% of the gross value of each closed deal. "
            f"That is separate from the ${monthly}/month supplier subscription (required to post listings). "
            "Buyers can set ingredient alerts without a supplier subscription."
        )

    if any(
        k in low
        for k in (
            "subscribe",
            "subscription",
            "stripe",
            "card",
            "billing",
            "per month",
            "/month",
            "monthly plan",
            "monthly fee",
            "monthly cost",
            "monthly charge",
            "billed monthly",
            "monthly billing",
            "pay monthly",
        )
    ):
        if STRIPE_CHECKOUT_ENABLED:
            return (
                f"Supplier subscription is ${monthly}/month. "
                "Under Marketplace → Suppliers, use the subscription form—you will be redirected to secure checkout to add a card; "
                "Stripe bills monthly after that. Then create listings with the same company and email."
            )
        return (
            f"Supplier subscription is ${monthly}/month (current list price). "
            "Use the Supplier subscription form under Marketplace → Suppliers with your company and contact email, then create listings. "
            "(Set STRIPE_SECRET_KEY and STRIPE_SUPPLIER_PRICE_ID to enable live card billing.)"
        )

    if "rating" in low or "review" in low or "stars" in low:
        n = len(load_supplier_ratings())
        return (
            f"Buyers who have committed on a listing can rate the supplier using the anonymous supplier code (SX-…) shown on that row—"
            f"company names stay hidden until commitment. There are {n} rating record(s) on file."
        )

    if any(k in low for k in ("forum", "community", "procurement", "network")) and "listing" not in low:
        return (
            "Open Marketplace → Community to start or reply to threads with other purchasing agents. "
            "For private deals, use Buyers and the agreement flow after you match a listing."
        )

    if "coa" in low or "certificate" in low:
        return (
            "Every supplier listing requires a COA reference (file name or doc ID) so buyers can verify documentation before committing."
        )

    if any(k in low for k in ("how many listing", "listings", "inventory")):
        n = len(load_marketplace_listings())
        return f"There are {n} active listing(s) right now. Tell me an ingredient name and I will search them."

    listings = load_marketplace_listings()
    threads = load_forum_threads()
    rating_agg = build_supplier_rating_aggregates()

    tokens = _marketplace_assistant_meaningful_tokens(low)
    hits: list[str] = []
    for lst in listings:
        ing = str(lst.get("ingredient", ""))
        blob = f"{ing} {lst.get('notes', '')}".lower()
        if tokens and any(t in blob for t in tokens):
            code = str(lst.get("supplier_public_code") or "")
            pill = format_supplier_rating_pill(rating_agg.get(code))
            hits.append(
                f"• {ing} — ${float(lst.get('price_per_kg', 0)):.2f}/kg, "
                f"{float(lst.get('quantity_kg', 0)):.0f} kg (public ref {code}, {pill})"
            )
        if len(hits) >= 5:
            break

    if hits:
        return "Here are matching listings:\n" + "\n".join(hits[:5])

    fhits: list[str] = []
    for th in threads:
        title = str(th.get("title", ""))
        blob = f"{title} {th.get('body', '')}".lower()
        if tokens and any(t in blob for t in tokens):
            fhits.append(f"• Forum: {title}")
        if len(fhits) >= 3:
            break
    if fhits:
        return "Related community threads:\n" + "\n".join(fhits)

    pricing_hint = any(
        p in low
        for p in (
            "how much",
            "cost",
            "pricing",
            "price",
            "pay",
            "charge",
            "expensive",
            "cheap",
        )
    )
    if pricing_hint and not tokens:
        return (
            f"Typical marketplace charges: {pct}% brokerage on closed deal value; suppliers pay ${monthly}/month to list. "
            "Per-kg listing prices vary by product—name an ingredient to search the catalog."
        )

    return (
        f"I could not match that to a specific listing. Try a product name (e.g. collagen), or ask about {pct}% brokerage, "
        f"${monthly}/mo supplier subscription, COA, or the forum."
    )


def _parse_csv_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.replace(";", ",").split(",") if item.strip()]


def _num_or_none(raw: str) -> float | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_ingredient(raw: str) -> str:
    return " ".join((raw or "").strip().lower().split())


def _commit_key(listing_id: str, buyer_contact_email: str) -> str:
    return f"{listing_id.strip().lower()}::{buyer_contact_email.strip().lower()}"


def build_commit_lookup() -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for commit in load_marketplace_commits():
        if not commit.get("listing_id") or not commit.get("buyer_contact_email"):
            continue
        if not commit.get("agreement_accepted"):
            continue
        lookup[_commit_key(commit["listing_id"], commit["buyer_contact_email"])] = commit
    return lookup


def _listing_matches_alert(listing: dict, alert: dict) -> bool:
    listing_ingredient = _normalize_ingredient(listing.get("ingredient", ""))
    wanted = [_normalize_ingredient(i) for i in alert.get("ingredient_watchlist", [])]
    if wanted and listing_ingredient not in wanted:
        return False
    max_price = alert.get("max_price_per_kg")
    if isinstance(max_price, (int, float)) and listing.get("price_per_kg", 0.0) > max_price:
        return False
    min_qty = alert.get("min_quantity_kg")
    if isinstance(min_qty, (int, float)) and listing.get("quantity_kg", 0.0) < min_qty:
        return False
    return True


def build_marketplace_matches() -> list[dict]:
    listings = load_marketplace_listings()
    alerts = load_marketplace_alerts()
    commit_lookup = build_commit_lookup()
    rating_agg = build_supplier_rating_aggregates()
    matches: list[dict] = []
    for listing in listings:
        code = str(listing.get("supplier_public_code") or "")
        agg = rating_agg.get(code)
        for alert in alerts:
            if _listing_matches_alert(listing, alert):
                is_visible = bool(
                    commit_lookup.get(_commit_key(listing.get("id", ""), alert.get("buyer_contact_email", "")))
                )
                matches.append(
                    {
                        "listing_id": listing.get("id"),
                        "alert_id": alert.get("id"),
                        "ingredient": listing.get("ingredient"),
                        "supplier_company": listing.get("supplier_company"),
                        "supplier_company_masked": listing.get("supplier_company") if is_visible else "Hidden until purchase commitment",
                        "supplier_public_code": code,
                        "supplier_rating_display": format_supplier_rating_pill(agg),
                        "supplier_visible": is_visible,
                        "buyer_company": alert.get("buyer_company"),
                        "buyer_contact_email": alert.get("buyer_contact_email"),
                        "price_per_kg": listing.get("price_per_kg"),
                        "quantity_kg": listing.get("quantity_kg"),
                        "expires_on": listing.get("expires_on"),
                    }
                )
    return matches


def build_marketplace_summary() -> dict:
    listings = load_marketplace_listings()
    alerts = load_marketplace_alerts()
    deals = load_marketplace_deals()
    gross = sum(float(d.get("gross_deal_value", 0.0)) for d in deals)
    vig_collected = sum(float(d.get("vig_fee", 0.0)) for d in deals)
    subs = load_supplier_subscriptions()
    active_subs = sum(1 for s in subs if (s.get("status") or "active").lower() == "active")
    return {
        "listings": len(listings),
        "alerts": len(alerts),
        "matches": len(build_marketplace_matches()),
        "deals": len(deals),
        "commits": len(load_marketplace_commits()),
        "supplier_subscriptions": active_subs,
        "forum_threads": len(load_forum_threads()),
        "gross_volume": gross,
        "vig_collected": vig_collected,
        "vig_rate_pct": int(MARKETPLACE_VIG_RATE * 100),
    }


def listings_for_marketplace_view() -> list[dict]:
    """Public catalog rows: always mask legal supplier name (SX- ref only). Unmask per buyer on matches after they commit."""
    ensure_all_listing_supplier_codes()
    listings = sorted(load_marketplace_listings(), key=lambda x: x.get("created_at", ""), reverse=True)
    rating_agg = build_supplier_rating_aggregates()
    out: list[dict] = []
    for listing in listings:
        item = dict(listing)
        code = str(listing.get("supplier_public_code") or "")
        agg = rating_agg.get(code)
        item["supplier_public_code"] = code
        item["supplier_rating_display"] = format_supplier_rating_pill(agg)
        item["supplier_public_name"] = "Confidential supplier"
        out.append(item)
    return out


def normalize_lead(lead: dict) -> dict:
    """Ensure extended fields exist for templates (does not write to disk)."""
    out = dict(lead)
    tl = out.get("touch_log")
    if not isinstance(tl, list):
        out["touch_log"] = []
    for key, default in DEFAULT_EXTENDED.items():
        if key == "touch_log":
            continue
        out.setdefault(key, default)
    return out


def load_leads() -> list[dict]:
    ensure_data_store()
    try:
        raw = json.loads(LEADS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [normalize_lead(lead) for lead in raw]


def load_exclusives() -> list[dict]:
    ensure_data_store()
    try:
        data = json.loads(EXCLUSIVES_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def classify_lead_bucket(lead: dict) -> str:
    """
    Classify lead as buyer/supplier based on explicit lane first, then fallback hints.
    """
    lane = (lead.get("lane") or "").strip().lower()
    if lane == "demand (buyer)":
        return "buyer"
    if lane == "supply (supplier)":
        return "supplier"

    source = (lead.get("source") or "").lower()
    segment = (lead.get("segment") or "").lower()
    website = (lead.get("website") or "").lower()
    text = " ".join([source, segment, website])
    supplier_hints = ("ingredient", "supplyside", "vendor", "supplier", "raw", "flavor")
    return "supplier" if any(h in text for h in supplier_hints) else "buyer"


def split_leads_for_dashboard(leads: list[dict]) -> tuple[list[dict], list[dict]]:
    buyers: list[dict] = []
    suppliers: list[dict] = []
    for lead in leads:
        if classify_lead_bucket(lead) == "supplier":
            suppliers.append(lead)
        else:
            buyers.append(lead)
    return buyers, suppliers


def get_lead_by_id(lead_id: str) -> dict | None:
    for lead in load_leads():
        if lead.get("id") == lead_id:
            return lead
    return None


def parse_ingredient_focus(raw: str) -> list[str]:
    return [item.strip() for item in raw.replace(";", ",").split(",") if item.strip()]


def apply_extended_fields_from_form(lead: dict, form) -> None:
    """Mutate lead from a werkzeug ImmutableMultiDict (request.form)."""
    lead["lane"] = form.get("lane", "").strip()
    lead["region"] = form.get("region", "").strip()
    lead["segment"] = form.get("segment", "").strip()
    lead["lead_source_type"] = form.get("lead_source_type", "").strip()
    lead["lead_source_detail"] = form.get("lead_source_detail", "").strip()
    lead["contact_name"] = form.get("contact_name", "").strip()
    lead["contact_title"] = form.get("contact_title", "").strip()
    lead["contact_email"] = form.get("contact_email", "").strip()
    lead["contact_phone"] = form.get("contact_phone", "").strip()
    lead["categories_sourcing"] = form.get("categories_sourcing", "").strip()
    lead["moq_notes"] = form.get("moq_notes", "").strip()
    lead["icp_score"] = form.get("icp_score", "").strip()
    lead["est_volume_band"] = form.get("est_volume_band", "").strip()
    lead["loss_reason"] = form.get("loss_reason", "").strip()
    if form.get("ingredient_focus") is not None:
        lead["ingredient_focus"] = parse_ingredient_focus(form.get("ingredient_focus", ""))


def save_leads(leads: list[dict]) -> None:
    normalized = [normalize_lead(dict(lead)) for lead in leads]
    LEADS_FILE.write_text(json.dumps(normalized, indent=2), encoding="utf-8")


def merge_core_lead_fields(lead: dict, form) -> None:
    lead["company_name"] = form.get("company_name", "").strip()
    lead["website"] = form.get("website", "").strip()
    rep = form.get("sales_rep", "").strip()
    lead["sales_rep"] = rep if rep in SALES_REPS else lead.get("sales_rep", "Unassigned")
    st = form.get("stage", "").strip()
    lead["stage"] = st if st in STAGES else lead.get("stage", "New")
    pr = form.get("priority", "").strip()
    if pr in ("High", "Medium", "Low"):
        lead["priority"] = pr
    lead["next_action"] = form.get("next_action", "").strip()
    lead["last_call_outcome"] = form.get("last_call_outcome", "").strip()
    if form.get("notes") is not None:
        lead["notes"] = form.get("notes", "").strip()
    apply_extended_fields_from_form(lead, form)


def build_summary(leads: list[dict]) -> dict:
    stage_counts = {stage: 0 for stage in STAGES}
    for lead in leads:
        stage = lead.get("stage", "New")
        if stage in stage_counts:
            stage_counts[stage] += 1
    return {
        "total": len(leads),
        "new": stage_counts["New"],
        "qualified": stage_counts["Qualified"],
        "active": stage_counts["Contacted"] + stage_counts["Negotiation"],
        "won": stage_counts["Won"],
        "lost": stage_counts["Lost"],
        "stage_counts": stage_counts,
    }


def find_ingredient_matches(text: str) -> list[str]:
    text_lower = text.lower()
    return [ingredient for ingredient in CORE_INGREDIENTS if ingredient in text_lower]


def _ingredient_focus_creatine_wedge(combined: str) -> list[str]:
    focus = find_ingredient_matches(combined)
    lower = {x.lower() for x in focus}
    if "creatine" not in lower:
        focus = ["creatine", *focus]
    return focus


def _pipeline_hit_allowed(url: str) -> bool:
    low = url.lower()
    return not any(s in low for s in URL_SKIP_SUBSTRINGS)


def _lead_from_pipeline_hit(
    *,
    url: str,
    title: str,
    snippet: str,
    region_bucket: str,
    geo_token: str,
    search_query: str,
) -> dict:
    combined = f"{title} {snippet}"
    return {
        "id": str(uuid.uuid4()),
        "company_name": (title or "Unknown company")[:160],
        "website": url.strip(),
        "source": "Creatine pipeline (regional search)",
        "keywords": f"pipeline:{region_bucket}:{geo_token[:48]}",
        "ingredient_focus": _ingredient_focus_creatine_wedge(combined),
        "value_pitch": DEFAULT_VALUE_PITCH,
        "stage": "New",
        "sales_rep": "Unassigned",
        "priority": "Medium",
        "next_action": "Creatine wedge: confirm monohydrate spec/MOQ + procurement contact.",
        "last_call_outcome": "",
        "notes": f"Query: {search_query}\n---\n{snippet[:450]}",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "lane": "Demand (buyer)",
        "region": region_bucket,
        "segment": "Supplement brand",
        "lead_source_type": "Discovery tool (search)",
        "lead_source_detail": f"{geo_token} · {search_query[:200]}",
    }


def run_creatine_regional_pipeline(
    region_buckets: list[str],
    *,
    per_query: int,
    max_total: int,
    max_queries: int,
) -> tuple[list[dict], int]:
    """
    Run round-robin DDG searches across selected CRM region buckets.
    Returns (new leads, number of search queries executed). Not exhaustive vs paid data.
    """
    if DDGS is None:
        return [], 0
    per_query = max(3, min(per_query, PIPELINE_PER_QUERY_CAP))
    max_total = max(5, min(max_total, PIPELINE_MAX_NEW_LEADS_PER_RUN))
    max_queries = max(1, min(max_queries, PIPELINE_MAX_QUERIES_PER_RUN))
    ddg = DDGS()

    task_queues: list[deque[tuple[str, str, str]]] = []
    for bucket in region_buckets:
        geos = PIPELINE_REGIONS.get(bucket, [])[:8]
        tasks: list[tuple[str, str, str]] = []
        for geo in geos:
            for tmpl in CREATINE_PIPELINE_TEMPLATES:
                tasks.append((bucket, geo, tmpl.format(geo=geo)))
        if tasks:
            task_queues.append(deque(tasks))

    collected: list[dict] = []
    seen_urls: set[str] = set()
    queries_run = 0

    while True:
        if len(collected) >= max_total or queries_run >= max_queries:
            break
        active = [dq for dq in task_queues if dq]
        if not active:
            break
        for dq in active:
            if len(collected) >= max_total or queries_run >= max_queries:
                break
            bucket, geo, qstr = dq.popleft()
            queries_run += 1
            try:
                results = ddg.text(qstr, max_results=per_query)
            except Exception:
                results = []
            for result in results:
                if len(collected) >= max_total:
                    break
                url = (result.get("href") or "").strip()
                if not url.startswith("http") or not _pipeline_hit_allowed(url):
                    continue
                ukey = url.lower().split("#")[0]
                if ukey in seen_urls:
                    continue
                title = (result.get("title") or "").strip()
                snippet = (result.get("body") or "").strip()
                combined = f"{title} {snippet}".lower()
                if "creatine" not in combined:
                    continue
                seen_urls.add(ukey)
                collected.append(
                    _lead_from_pipeline_hit(
                        url=url,
                        title=title,
                        snippet=snippet,
                        region_bucket=bucket,
                        geo_token=geo,
                        search_query=qstr,
                    )
                )

    return collected, queries_run


def dedupe_merge(existing: list[dict], incoming: list[dict]) -> tuple[list[dict], int]:
    seen = {lead.get("website", "").strip().lower() for lead in existing if lead.get("website")}
    added = 0
    for lead in incoming:
        website = lead.get("website", "").strip().lower()
        if website and website in seen:
            continue
        existing.append(lead)
        if website:
            seen.add(website)
        added += 1
    return existing, added


@app.context_processor
def inject_form_choices() -> dict:
    return {
        "lane_options": LANES,
        "region_options": REGIONS,
        "segment_options": SEGMENTS,
        "source_type_options": LEAD_SOURCE_TYPES,
        "touch_channels": TOUCH_CHANNELS,
        "loss_reasons": [""] + LOSS_REASONS,
        "volume_bands": VOLUME_BANDS,
        "icp_scores": ICP_SCORES,
        "wedge_product": WEDGE_PRODUCT,
        "wedge_phase_copy": WEDGE_PHASE_COPY,
        "default_value_pitch": DEFAULT_VALUE_PITCH,
        "pipeline_max_queries": PIPELINE_MAX_QUERIES_PER_RUN,
        "pipeline_max_leads": PIPELINE_MAX_NEW_LEADS_PER_RUN,
        "pipeline_per_query_cap": PIPELINE_PER_QUERY_CAP,
        "marketplace_vig_pct": int(MARKETPLACE_VIG_RATE * 100),
        "supplier_subscription_monthly": int(SUPPLIER_SUBSCRIPTION_MONTHLY_USD),
        "stripe_checkout_enabled": STRIPE_CHECKOUT_ENABLED,
    }


@app.route("/playbook")
def sales_playbook():
    return render_template("sales_playbook.html")


@app.route("/sell-sheet")
def sell_sheet():
    return render_template("sell_sheet.html")


@app.route("/legal-agreements")
def legal_agreements():
    return render_template("legal_agreements.html")


@app.route("/marketplace")
def marketplace():
    summary = build_marketplace_summary()
    listings_for_view = listings_for_marketplace_view()
    return render_template(
        "marketplace_home.html",
        summary=summary,
        listings=listings_for_view,
        marketplace_nav_active="marketplace",
    )


@app.route("/marketplace/listings")
def marketplace_listings_page():
    return redirect(url_for("marketplace"))


@app.route("/marketplace/buy")
def marketplace_buy():
    listings_for_view = listings_for_marketplace_view()
    matches = build_marketplace_matches()
    summary = build_marketplace_summary()
    raw_listing = request.args.get("listing", "").strip()
    prefill_listing_id = ""
    if raw_listing and any(str(x.get("id")) == raw_listing for x in listings_for_view):
        prefill_listing_id = raw_listing
    return render_template(
        "marketplace_buy.html",
        listings=listings_for_view,
        matches=matches,
        summary=summary,
        marketplace_nav_active="buy",
        prefill_listing_id=prefill_listing_id,
    )


@app.route("/marketplace/suppliers")
def marketplace_suppliers():
    listings_for_view = listings_for_marketplace_view()
    summary = build_marketplace_summary()
    return render_template(
        "marketplace_suppliers.html",
        listings=listings_for_view,
        summary=summary,
        marketplace_nav_active="suppliers",
    )


@app.route("/marketplace/community")
def marketplace_community():
    forum_threads = sorted(load_forum_threads(), key=lambda x: x.get("created_at", ""), reverse=True)
    summary = build_marketplace_summary()
    return render_template(
        "marketplace_community.html",
        forum_threads=forum_threads,
        summary=summary,
        marketplace_nav_active="community",
    )


@app.route("/marketplace/deals")
def marketplace_deals_page():
    return redirect(url_for("marketplace"))


@app.route("/marketplace/terms")
def marketplace_terms():
    ensure_all_listing_supplier_codes()
    summary = build_marketplace_summary()
    pending = session.get(SESSION_PENDING_COMMIT_KEY)
    listing_preview: dict | None = None
    if pending and pending.get("listing_id"):
        lst = next((x for x in load_marketplace_listings() if x.get("id") == pending["listing_id"]), None)
        if lst:
            listing_preview = {
                "ingredient": lst.get("ingredient"),
                "supplier_public_code": lst.get("supplier_public_code"),
                "price_per_kg": lst.get("price_per_kg"),
            }
    return render_template(
        "marketplace_terms.html",
        summary=summary,
        pending=pending,
        listing_preview=listing_preview,
        agreement_version=MARKETPLACE_AGREEMENT_VERSION,
        marketplace_nav_active="terms",
    )


@app.route("/marketplace/chat", methods=["POST"])
def marketplace_chat():
    payload = request.get_json(silent=True) or {}
    msg = str(payload.get("message", "")).strip()
    return jsonify({"reply": marketplace_assistant_reply(msg)})


@app.route("/marketplace/supplier-subscribe", methods=["POST"])
def supplier_subscribe():
    company = request.form.get("company_name", "").strip()
    email = request.form.get("contact_email", "").strip()
    contact_name = request.form.get("contact_name", "").strip()
    ack = request.form.get("ack_amount") == "yes"
    if not company or not email:
        flash("Company name and contact email are required to start a supplier subscription.", "error")
        return redirect(url_for("marketplace_suppliers"))
    if not ack:
        flash("Please confirm the subscription amount to continue.", "error")
        return redirect(url_for("marketplace_suppliers"))
    subs = load_supplier_subscriptions()
    ne = _norm_email(email)
    if any(
        _norm_email(s.get("contact_email", "")) == ne
        and (s.get("status") or "active").lower() in ("active", "trialing")
        for s in subs
    ):
        flash("This email already has an active supplier subscription.", "success")
        return redirect(url_for("marketplace_suppliers"))

    if STRIPE_CHECKOUT_ENABLED and stripe is not None:
        stripe.api_key = STRIPE_SECRET_KEY
        base = request.host_url.rstrip("/")
        try:
            checkout_session = stripe.checkout.Session.create(
                mode="subscription",
                customer_email=email,
                line_items=[{"price": STRIPE_SUPPLIER_PRICE_ID, "quantity": 1}],
                success_url=base + url_for("supplier_subscribe_success") + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=base + url_for("marketplace_suppliers") + "?checkout=canceled",
                metadata={
                    "company_name": company[:500],
                    "contact_email": email[:500],
                    "contact_name": contact_name[:500],
                },
                subscription_data={
                    "metadata": {
                        "company_name": company[:500],
                        "contact_email": email[:500],
                    }
                },
            )
        except Exception as exc:  # pragma: no cover - network/SDK
            flash(f"Could not start payment checkout: {exc}", "error")
            return redirect(url_for("marketplace_suppliers"))
        return redirect(str(checkout_session.url), code=303)

    subs.append(
        {
            "id": str(uuid.uuid4()),
            "company_name": company,
            "contact_name": contact_name,
            "contact_email": email,
            "monthly_amount_usd": SUPPLIER_SUBSCRIPTION_MONTHLY_USD,
            "billing_provider": "manual",
            "status": "active",
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "public_supplier_code": _generate_unique_supplier_public_code(),
        }
    )
    save_supplier_subscriptions(subs)
    flash(
        f"Supplier subscription recorded at ${int(SUPPLIER_SUBSCRIPTION_MONTHLY_USD)}/month (demo mode—no card charged). "
        f"You can now post listings for {company}.",
        "success",
    )
    return redirect(url_for("marketplace_suppliers"))


@app.route("/marketplace/supplier-subscribe/success")
def supplier_subscribe_success():
    if not STRIPE_CHECKOUT_ENABLED or stripe is None:
        flash("Card billing is not configured.", "error")
        return redirect(url_for("marketplace_suppliers"))
    session_id = request.args.get("session_id", "").strip()
    if not session_id:
        flash("Missing checkout session.", "error")
        return redirect(url_for("marketplace_suppliers"))
    stripe.api_key = STRIPE_SECRET_KEY
    try:
        sess = stripe.checkout.Session.retrieve(session_id, expand=["subscription"])
    except Exception as exc:  # pragma: no cover
        flash(f"Could not verify checkout: {exc}", "error")
        return redirect(url_for("marketplace_suppliers"))

    if getattr(sess, "status", None) != "complete":
        flash("Checkout did not complete successfully.", "error")
        return redirect(url_for("marketplace_suppliers"))

    sub_obj = getattr(sess, "subscription", None)
    if sub_obj is None:
        flash("No subscription was created for this checkout.", "error")
        return redirect(url_for("marketplace_suppliers"))
    if isinstance(sub_obj, str):
        try:
            sub_obj = stripe.Subscription.retrieve(sub_obj)
        except Exception as exc:  # pragma: no cover
            flash(f"Could not load subscription: {exc}", "error")
            return redirect(url_for("marketplace_suppliers"))

    st = str(getattr(sub_obj, "status", "") or "")
    if st not in ("active", "trialing"):
        flash(f"Subscription status is {st or 'unknown'}—try again or contact support.", "error")
        return redirect(url_for("marketplace_suppliers"))

    meta = getattr(sess, "metadata", None) or {}
    company = str(meta.get("company_name") or "").strip()
    email = str(meta.get("contact_email") or getattr(sess, "customer_email", None) or "").strip()
    contact_name = str(meta.get("contact_name") or "").strip()
    if not email:
        flash("Checkout is missing an email; cannot activate subscription.", "error")
        return redirect(url_for("marketplace_suppliers"))

    upsert_local_subscription_from_stripe(
        company=company,
        email=email,
        contact_name=contact_name,
        customer_id=str(getattr(sess, "customer", "") or "") or None,
        subscription_id=str(getattr(sub_obj, "id", "") or "") or None,
        stripe_status=st,
    )
    flash(
        f"Subscription active. Stripe will charge ${int(SUPPLIER_SUBSCRIPTION_MONTHLY_USD)}/month. "
        f"Use the same company ({company or 'as entered'}) and email when you create listings.",
        "success",
    )
    return redirect(url_for("marketplace_suppliers"))


@app.route("/marketplace/stripe-webhook", methods=["POST"])
def stripe_webhook():
    if not STRIPE_WEBHOOK_SECRET or stripe is None:
        return jsonify({"error": "webhook not configured"}), 400
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        return jsonify({"error": "invalid payload"}), 400
    except stripe.error.SignatureVerificationError:  # type: ignore[attr-defined]
        return jsonify({"error": "invalid signature"}), 400

    et = getattr(event, "type", None) or (event["type"] if isinstance(event, dict) else None)
    data = getattr(event, "data", None) if not isinstance(event, dict) else event.get("data")
    obj = getattr(data, "object", None) if data is not None and not isinstance(data, dict) else (data or {}).get("object")
    if et in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ) and obj is not None:
        raw = obj.to_dict() if hasattr(obj, "to_dict") else (obj if isinstance(obj, dict) else {})
        if isinstance(raw, dict):
            apply_stripe_subscription_object(raw)
    return jsonify({"received": True})


@app.route("/marketplace/supplier-rating", methods=["POST"])
def submit_supplier_rating():
    listing_id = request.form.get("listing_id", "").strip()
    buyer_contact_email = request.form.get("buyer_contact_email", "").strip()
    stars_raw = request.form.get("stars", "").strip()
    comment = (request.form.get("comment") or "").strip()[:2000]
    if not listing_id or not buyer_contact_email:
        flash("Listing and buyer email are required to submit a rating.", "error")
        return redirect(url_for("marketplace_buy"))
    try:
        stars = int(stars_raw)
    except ValueError:
        flash("Stars must be a whole number 1–5.", "error")
        return redirect(url_for("marketplace_buy"))
    if stars < 1 or stars > 5:
        flash("Stars must be between 1 and 5.", "error")
        return redirect(url_for("marketplace_buy"))

    commit_lookup = build_commit_lookup()
    if not commit_lookup.get(_commit_key(listing_id, buyer_contact_email)):
        flash("Only buyers who committed on this listing can rate that supplier (identity stays masked until commitment).", "error")
        return redirect(url_for("marketplace_buy"))

    listings = load_marketplace_listings()
    listing = next((x for x in listings if x.get("id") == listing_id), None)
    if not listing:
        flash("Listing not found.", "error")
        return redirect(url_for("marketplace_buy"))

    code = str(listing.get("supplier_public_code") or "").strip()
    if not code:
        code = get_or_assign_supplier_public_code(
            str(listing.get("supplier_company", "")),
            str(listing.get("supplier_contact_email", "")),
        )
        listing["supplier_public_code"] = code
        save_marketplace_listings(listings)

    supplier_company = str(listing.get("supplier_company") or "")
    ratings = load_supplier_ratings()
    ne = _norm_email(buyer_contact_email)
    updated = False
    for row in ratings:
        if _norm_email(row.get("buyer_contact_email", "")) == ne and row.get("supplier_public_code") == code:
            row["stars"] = stars
            row["comment"] = comment
            row["listing_id"] = listing_id
            row["updated_at"] = datetime.now().isoformat(timespec="seconds")
            updated = True
            break
    if not updated:
        ratings.append(
            {
                "id": str(uuid.uuid4()),
                "supplier_public_code": code,
                "supplier_company": supplier_company,
                "listing_id": listing_id,
                "buyer_contact_email": buyer_contact_email,
                "stars": stars,
                "comment": comment,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
    save_supplier_ratings(ratings)
    flash(
        f"Thanks—recorded {stars}/5 for supplier {code}. Scores are shown anonymously on listings until a buyer unlocks the legal name.",
        "success",
    )
    return redirect(url_for("marketplace_buy"))


@app.route("/marketplace/forum/thread", methods=["POST"])
def forum_new_thread():
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    author_company = request.form.get("author_company", "").strip()
    author_email = request.form.get("author_email", "").strip()
    if not title or not body or not author_company or not author_email:
        flash("Thread title, message, company, and email are required.", "error")
        return redirect(url_for("marketplace_community"))
    threads = load_forum_threads()
    threads.append(
        {
            "id": str(uuid.uuid4()),
            "title": title[:200],
            "body": body[:8000],
            "author_company": author_company,
            "author_email": author_email,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "replies": [],
        }
    )
    save_forum_threads(threads)
    flash("Thread posted to the procurement community.", "success")
    return redirect(url_for("marketplace_community"))


@app.route("/marketplace/forum/reply", methods=["POST"])
def forum_reply():
    thread_id = request.form.get("thread_id", "").strip()
    body = request.form.get("body", "").strip()
    author_company = request.form.get("author_company", "").strip()
    author_email = request.form.get("author_email", "").strip()
    if not thread_id or not body or not author_company or not author_email:
        flash("Reply text, company, and email are required.", "error")
        return redirect(url_for("marketplace_community"))
    threads = load_forum_threads()
    for th in threads:
        if th.get("id") != thread_id:
            continue
        reps = th.get("replies")
        if not isinstance(reps, list):
            reps = []
            th["replies"] = reps
        reps.append(
            {
                "id": str(uuid.uuid4()),
                "body": body[:8000],
                "author_company": author_company,
                "author_email": author_email,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        save_forum_threads(threads)
        flash("Reply added.", "success")
        return redirect(url_for("marketplace_community"))
    flash("Thread not found.", "error")
    return redirect(url_for("marketplace_community"))


@app.route("/marketplace/listings/create", methods=["POST"])
def add_marketplace_listing():
    supplier_company = request.form.get("supplier_company", "").strip()
    supplier_contact_email = request.form.get("supplier_contact_email", "").strip()
    ingredient = request.form.get("ingredient", "").strip()
    price_per_kg = _num_or_none(request.form.get("price_per_kg", ""))
    quantity_kg = _num_or_none(request.form.get("quantity_kg", ""))
    coa_document = request.form.get("coa_document", "").strip()
    if not supplier_company or not supplier_contact_email or not ingredient or price_per_kg is None or quantity_kg is None or not coa_document:
        flash("Supplier company, contact email, ingredient, price, quantity, and COA reference are required for a listing.", "error")
        return redirect(url_for("marketplace_suppliers"))
    if not supplier_subscription_active(supplier_company, supplier_contact_email):
        flash(
            f"Active supplier subscription required (${int(SUPPLIER_SUBSCRIPTION_MONTHLY_USD)}/month). "
            "Subscribe using the same company name and email as your listing, then try again.",
            "error",
        )
        return redirect(url_for("marketplace_suppliers"))
    listing = {
        "id": str(uuid.uuid4()),
        "supplier_company": supplier_company,
        "supplier_contact_email": supplier_contact_email,
        "supplier_public_code": get_or_assign_supplier_public_code(supplier_company, supplier_contact_email),
        "ingredient": ingredient,
        "price_per_kg": price_per_kg,
        "quantity_kg": quantity_kg,
        "coa_document": coa_document,
        "expires_on": request.form.get("expires_on", "").strip(),
        "notes": request.form.get("notes", "").strip(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    listings = load_marketplace_listings()
    listings.append(listing)
    save_marketplace_listings(listings)

    matches = [m for m in build_marketplace_matches() if m.get("listing_id") == listing["id"]]
    if matches:
        flash(
            f"Listing created. {len(matches)} buyer alert match(es) triggered for {ingredient}.",
            "success",
        )
    else:
        flash("Listing created. No active buyer alert matches yet.", "success")
    return redirect(url_for("marketplace_suppliers"))


@app.route("/marketplace/commit/begin", methods=["POST"])
def commit_marketplace_begin():
    listing_id = request.form.get("listing_id", "").strip()
    buyer_company = request.form.get("buyer_company", "").strip()
    buyer_contact_email = request.form.get("buyer_contact_email", "").strip()
    if not listing_id or not buyer_company or not buyer_contact_email:
        flash("Listing, buyer company, and buyer email are required before the agreement.", "error")
        return redirect(url_for("marketplace_buy"))

    listings = load_marketplace_listings()
    if not any(item.get("id") == listing_id for item in listings):
        flash("Listing not found.", "error")
        return redirect(url_for("marketplace_buy"))

    commits = load_marketplace_commits()
    key = _commit_key(listing_id, buyer_contact_email)
    if any(_commit_key(c.get("listing_id", ""), c.get("buyer_contact_email", "")) == key for c in commits):
        flash("Commitment already recorded. Supplier details are already unlocked for this buyer.", "success")
        session.pop(SESSION_PENDING_COMMIT_KEY, None)
        return redirect(url_for("marketplace_buy"))

    session[SESSION_PENDING_COMMIT_KEY] = {
        "listing_id": listing_id,
        "buyer_company": buyer_company,
        "buyer_contact_email": buyer_contact_email,
    }
    return redirect(url_for("marketplace_terms"))


@app.route("/marketplace/commit/confirm", methods=["POST"])
def commit_marketplace_confirm():
    pending = session.get(SESSION_PENDING_COMMIT_KEY)
    if not pending or not pending.get("listing_id"):
        flash("No pending commitment. Start from Buyers → Commit to purchase.", "error")
        return redirect(url_for("marketplace_buy"))

    if request.form.get("accept_terms") != "yes":
        flash("You must accept the brokered transaction agreement to submit your signature.", "error")
        return redirect(url_for("marketplace_terms"))

    effective_date = request.form.get("effective_date", "").strip()
    signer_name = request.form.get("signer_name", "").strip()
    signer_title = request.form.get("signer_title", "").strip()
    signature = request.form.get("signature", "").strip()
    if not effective_date or not signer_name or not signer_title or not signature:
        flash("Effective date, your name, title, and electronic signature are required.", "error")
        return redirect(url_for("marketplace_terms"))

    listing_id = str(pending["listing_id"]).strip()
    buyer_company = str(pending.get("buyer_company") or "").strip()
    buyer_contact_email = str(pending.get("buyer_contact_email") or "").strip()

    listings = load_marketplace_listings()
    if not any(item.get("id") == listing_id for item in listings):
        session.pop(SESSION_PENDING_COMMIT_KEY, None)
        flash("Listing not found.", "error")
        return redirect(url_for("marketplace_buy"))

    commits = load_marketplace_commits()
    key = _commit_key(listing_id, buyer_contact_email)
    if any(_commit_key(c.get("listing_id", ""), c.get("buyer_contact_email", "")) == key for c in commits):
        session.pop(SESSION_PENDING_COMMIT_KEY, None)
        flash("Commitment already recorded. Supplier details are already unlocked for this buyer.", "success")
        return redirect(url_for("marketplace_buy"))

    commit_id = str(uuid.uuid4())
    accepted_at = datetime.now().isoformat(timespec="seconds")
    commit_row = {
        "id": commit_id,
        "listing_id": listing_id,
        "buyer_company": buyer_company,
        "buyer_contact_email": buyer_contact_email,
        "agreement_accepted": True,
        "agreement_version": MARKETPLACE_AGREEMENT_VERSION,
        "agreement_accepted_at": accepted_at,
        "effective_date": effective_date,
        "signer_name": signer_name,
        "signer_title": signer_title,
        "signature": signature,
    }
    commits.append(commit_row)
    save_marketplace_commits(commits)

    submissions = load_agreement_submissions()
    submissions.append(
        {
            "id": str(uuid.uuid4()),
            "commit_id": commit_id,
            "submitted_at": accepted_at,
            "listing_id": listing_id,
            "buyer_company": buyer_company,
            "buyer_contact_email": buyer_contact_email,
            "agreement_version": MARKETPLACE_AGREEMENT_VERSION,
            "effective_date": effective_date,
            "signer_name": signer_name,
            "signer_title": signer_title,
            "signature": signature,
            "status": "pending_counterparty_and_platform_execution",
        }
    )
    save_agreement_submissions(submissions)

    session.pop(SESSION_PENDING_COMMIT_KEY, None)
    flash(
        "Your signed agreement has been submitted to the platform for review. "
        "We do not execute agreements before your counterparty completes their signing process. "
        "Supplier identity will unlock for your buyer email once processing allows.",
        "success",
    )
    return redirect(url_for("marketplace_buy"))


@app.route("/marketplace/commit/cancel")
def commit_marketplace_cancel():
    session.pop(SESSION_PENDING_COMMIT_KEY, None)
    flash("Agreement flow canceled. No commitment was recorded.", "info")
    return redirect(url_for("marketplace_buy"))


@app.route("/marketplace/alerts", methods=["POST"])
def add_marketplace_alert():
    buyer_company = request.form.get("buyer_company", "").strip()
    buyer_contact_email = request.form.get("buyer_contact_email", "").strip()
    ingredients = _parse_csv_list(request.form.get("ingredient_watchlist", ""))
    if not buyer_company or not buyer_contact_email or not ingredients:
        flash("Buyer company, contact email, and ingredient watchlist are required.", "error")
        return redirect(url_for("marketplace_buy"))
    alert = {
        "id": str(uuid.uuid4()),
        "buyer_company": buyer_company,
        "buyer_contact_email": buyer_contact_email,
        "ingredient_watchlist": ingredients,
        "max_price_per_kg": _num_or_none(request.form.get("max_price_per_kg", "")),
        "min_quantity_kg": _num_or_none(request.form.get("min_quantity_kg", "")),
        "notes": request.form.get("notes", "").strip(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    alerts = load_marketplace_alerts()
    alerts.append(alert)
    save_marketplace_alerts(alerts)

    matches = [m for m in build_marketplace_matches() if m.get("alert_id") == alert["id"]]
    if matches:
        flash(
            f"Buyer alert created. {len(matches)} current listing match(es) found.",
            "success",
        )
    else:
        flash("Buyer alert created. Matching listings will trigger as suppliers post.", "success")
    return redirect(url_for("marketplace_buy"))


@app.route("/intake", methods=["GET", "POST"])
def lead_intake():
    blank = normalize_lead(
        {
            "id": "",
            "company_name": "",
            "website": "",
            "source": "Structured intake",
            "keywords": "intake",
            "ingredient_focus": [],
            "value_pitch": DEFAULT_VALUE_PITCH,
            "stage": "New",
            "sales_rep": "Unassigned",
            "priority": "Medium",
            "next_action": "",
            "last_call_outcome": "",
            "notes": "",
            "created_at": "",
        }
    )
    if request.method == "POST":
        company = request.form.get("company_name", "").strip()
        if not company:
            flash("Company name is required.", "error")
            return render_template("intake.html", lead=blank)
        lead = normalize_lead(
            {
                "id": str(uuid.uuid4()),
                "company_name": company,
                "website": request.form.get("website", "").strip(),
                "source": "Structured intake",
                "keywords": "intake",
                "ingredient_focus": [],
                "value_pitch": DEFAULT_VALUE_PITCH,
                "stage": "New",
                "sales_rep": "Unassigned",
                "priority": "Medium",
                "next_action": "",
                "last_call_outcome": "",
                "notes": "",
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        merge_core_lead_fields(lead, request.form)
        leads = load_leads()
        leads.append(lead)
        save_leads(leads)
        flash("Lead created from intake form.", "success")
        return redirect(url_for("lead_detail", lead_id=lead["id"]))
    return render_template("intake.html", lead=blank)


@app.route("/lead/<lead_id>")
def lead_detail(lead_id: str):
    lead = get_lead_by_id(lead_id)
    if not lead:
        flash("Lead not found.", "error")
        return redirect(url_for("index"))
    touch_log = list(reversed(lead.get("touch_log") or []))
    return render_template("lead_detail.html", lead=lead, touch_log=touch_log)


@app.route("/lead/<lead_id>/save", methods=["POST"])
def save_lead_full(lead_id: str):
    leads = load_leads()
    target: dict | None = None
    for lead in leads:
        if lead.get("id") == lead_id:
            target = lead
            break
    if not target:
        flash("Lead not found.", "error")
        return redirect(url_for("index"))
    if not request.form.get("company_name", "").strip():
        flash("Company name is required.", "error")
        return redirect(url_for("lead_detail", lead_id=lead_id))
    merge_core_lead_fields(target, request.form)
    save_leads(leads)
    flash("Lead record saved.", "success")
    return redirect(url_for("lead_detail", lead_id=lead_id))


@app.route("/lead/<lead_id>/touch", methods=["POST"])
def add_touch(lead_id: str):
    channel = request.form.get("touch_channel", "").strip()
    summary = request.form.get("touch_summary", "").strip()
    if not summary:
        flash("Touch summary is required to log outreach.", "error")
        return redirect(url_for("lead_detail", lead_id=lead_id))
    leads = load_leads()
    for lead in leads:
        if lead.get("id") != lead_id:
            continue
        log = lead.get("touch_log")
        if not isinstance(log, list):
            log = []
            lead["touch_log"] = log
        log.append(
            {
                "at": datetime.now().isoformat(timespec="seconds"),
                "channel": channel or "Other",
                "summary": summary[:2000],
            }
        )
        break
    else:
        flash("Lead not found.", "error")
        return redirect(url_for("index"))
    save_leads(leads)
    flash("Outreach touch logged.", "success")
    return redirect(url_for("lead_detail", lead_id=lead_id))


@app.route("/")
def index():
    leads = load_leads()
    leads.sort(key=lambda lead: lead.get("created_at", ""), reverse=True)
    buyer_leads, supplier_leads = split_leads_for_dashboard(leads)
    return render_template(
        "index.html",
        leads=leads,
        buyer_leads=buyer_leads,
        supplier_leads=supplier_leads,
        exclusives=load_exclusives(),
        summary=build_summary(leads),
        stages=STAGES,
        reps=SALES_REPS,
    )


@app.route("/buyers")
def buyers():
    leads = load_leads()
    leads.sort(key=lambda lead: lead.get("created_at", ""), reverse=True)
    buyer_leads, _ = split_leads_for_dashboard(leads)
    return render_template(
        "buyers.html",
        leads=buyer_leads,
        summary=build_summary(buyer_leads),
        stages=STAGES,
        reps=SALES_REPS,
    )


@app.route("/suppliers")
def suppliers():
    leads = load_leads()
    leads.sort(key=lambda lead: lead.get("created_at", ""), reverse=True)
    _, supplier_leads = split_leads_for_dashboard(leads)
    return render_template(
        "suppliers.html",
        leads=supplier_leads,
        summary=build_summary(supplier_leads),
        stages=STAGES,
        reps=SALES_REPS,
    )


@app.route("/pipeline/creatine", methods=["POST"])
def run_creatine_pipeline():
    """Multi-query regional seeding — not a complete universe of all creatine holders."""
    selected = [r.strip() for r in request.form.getlist("regions") if r.strip() in PIPELINE_REGIONS]
    if not selected:
        flash("Select at least one region to run the creatine pipeline.", "error")
        return redirect(url_for("index"))
    per_query = int(request.form.get("per_query", "8"))
    max_total = int(request.form.get("max_total", "80"))
    max_queries = int(request.form.get("max_queries", str(PIPELINE_MAX_QUERIES_PER_RUN)))

    if DDGS is None:
        flash(
            "Creatine pipeline needs the duckduckgo-search package and outbound network. "
            "Install deps and retry, or add leads manually / via intake.",
            "error",
        )
        return redirect(url_for("index"))

    discovered, queries_run = run_creatine_regional_pipeline(
        selected,
        per_query=per_query,
        max_total=max_total,
        max_queries=max_queries,
    )
    leads = load_leads()
    leads, added = dedupe_merge(leads, discovered)
    save_leads(leads)
    if added == 0:
        flash(
            f"Pipeline ran {queries_run} searches but added 0 new rows "
            "(duplicates, filtered URLs, or no creatine mentions in snippets). "
            "Try different region mix or run again later.",
            "error",
        )
    else:
        flash(
            f"Creatine pipeline: {queries_run} searches → {added} new accounts added "
            f"(deduped by website). Not exhaustive—verify brands/CMOs on LinkedIn.",
            "success",
        )
    return redirect(url_for("index"))


@app.route("/add-manual", methods=["POST"])
def add_manual():
    company_name = request.form.get("company_name", "").strip()
    website = request.form.get("website", "").strip()
    ingredient_focus = request.form.get("ingredient_focus", "").strip()
    if not company_name:
        flash("Company name is required for manual lead entry.", "error")
        return redirect(url_for("index"))

    ing = [item.strip() for item in ingredient_focus.split(",") if item.strip()]
    if not ing:
        ing = ["ingredients", "packaging", "merchandise"]
    lead = {
        "id": str(uuid.uuid4()),
        "company_name": company_name,
        "website": website,
        "source": "Manual marketplace lead",
        "keywords": "manual-entry",
        "ingredient_focus": ing,
        "value_pitch": DEFAULT_VALUE_PITCH,
        "stage": "New",
        "sales_rep": "Unassigned",
        "priority": request.form.get("priority", "Medium"),
        "next_action": (
            request.form.get("next_action", "").strip()
            or "Confirm spec, MOQ, documentation, and procurement contact."
        ),
        "last_call_outcome": "",
        "notes": request.form.get("notes", "").strip(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    leads = load_leads()
    leads.append(lead)
    save_leads(leads)
    flash("Manual lead added.", "success")
    return redirect(url_for("index"))


@app.route("/lead/<lead_id>/update", methods=["POST"])
def update_lead(lead_id: str):
    leads = load_leads()
    for lead in leads:
        if lead.get("id") != lead_id:
            continue
        new_stage = request.form.get("stage", lead.get("stage", "New"))
        lead["stage"] = new_stage if new_stage in STAGES else lead.get("stage", "New")
        lead["sales_rep"] = request.form.get("sales_rep", lead.get("sales_rep", "Unassigned"))
        lead["priority"] = request.form.get("priority", lead.get("priority", "Medium"))
        lead["next_action"] = request.form.get("next_action", lead.get("next_action", "")).strip()
        notes = request.form.get("notes", "").strip()
        if notes:
            existing_notes = lead.get("notes", "")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            lead["notes"] = f"{existing_notes}\n[{timestamp}] {notes}".strip()
        break
    save_leads(leads)
    flash("Lead updated.", "success")
    return redirect(url_for("index"))


@app.route("/lead/<lead_id>/log-call", methods=["POST"])
def log_call(lead_id: str):
    outcome = request.form.get("outcome", "").strip()
    leads = load_leads()
    for lead in leads:
        if lead.get("id") == lead_id:
            lead["last_call_outcome"] = outcome or "No outcome entered"
            lead["last_called_at"] = datetime.now().isoformat(timespec="seconds")
            if lead.get("stage") == "New":
                lead["stage"] = "Contacted"
            break
    save_leads(leads)
    flash("Call outcome logged.", "success")
    return redirect(url_for("index"))


@app.route("/lead/<lead_id>/delete", methods=["POST"])
def delete_lead(lead_id: str):
    leads = load_leads()
    updated = [lead for lead in leads if lead.get("id") != lead_id]
    if len(updated) != len(leads):
        save_leads(updated)
        flash("Lead deleted.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    ensure_data_store()
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_DEBUG", "1") not in ("0", "false", "False")
    app.run(host=host, port=port, debug=debug, threaded=True)
