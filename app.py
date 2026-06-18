from __future__ import annotations

from collections import deque
from datetime import date, datetime, timedelta
import os
from pathlib import Path
import json
import uuid

try:
    import stripe
except ImportError:  # pragma: no cover
    stripe = None  # type: ignore

from urllib.parse import urlencode

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from duckduckgo_search import DDGS
except ImportError:  # pragma: no cover
    DDGS = None

try:
    from agreement_mail import send_intro_request_notice, send_supplier_inquiry_notice
except ImportError:  # pragma: no cover
    def send_intro_request_notice(commit: dict) -> bool:  # type: ignore[misc]
        return False

    def send_supplier_inquiry_notice(inquiry: dict) -> bool:  # type: ignore[misc]
        return False

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
MARKETPLACE_REPORTED_TRANSACTIONS_FILE = DATA_DIR / "marketplace_reported_transactions.json"
MARKETPLACE_SUPPLIER_SUBSCRIPTIONS_FILE = DATA_DIR / "marketplace_supplier_subscriptions.json"
MARKETPLACE_FORUM_THREADS_FILE = DATA_DIR / "marketplace_forum_threads.json"
MARKETPLACE_SUPPLIER_RATINGS_FILE = DATA_DIR / "marketplace_supplier_ratings.json"
MARKETPLACE_AGREEMENT_SUBMISSIONS_FILE = DATA_DIR / "marketplace_agreement_submissions.json"
MARKETPLACE_BUYER_ACCESS_FILE = DATA_DIR / "marketplace_buyer_access_requests.json"
MARKETPLACE_SUPPLIER_INQUIRIES_FILE = DATA_DIR / "marketplace_supplier_inquiries.json"
MARKETPLACE_BIDS_FILE = DATA_DIR / "marketplace_bids.json"
MARKETPLACE_ORDERS_FILE = DATA_DIR / "marketplace_orders.json"
MARKETPLACE_BUYER_ACCOUNTS_FILE = DATA_DIR / "marketplace_buyer_accounts.json"
MARKETPLACE_SUPPLIER_ACCOUNTS_FILE = DATA_DIR / "marketplace_supplier_accounts.json"
AUCTION_NOTE_KEYWORDS = (
    "48-hour",
    "liquidation",
    "urgent",
    "best bid",
    "overstock",
    "clearance",
    "surplus",
)
DEFAULT_BID_INCREMENT = 0.05
MARKETPLACE_VIG_RATE = 0.05
SUPPLIER_SUBSCRIPTION_MONTHLY_USD = 100.0
SUPPLIER_LAUNCH_FREE = os.environ.get("SUPPLIER_LAUNCH_FREE", "1").lower() in ("1", "true", "yes")
SUPPLIER_ONBOARDING_EMAIL = (
    os.environ.get("SUPPLIER_ONBOARDING_EMAIL", "").strip()
    or os.environ.get("SUPPLIER_INQUIRY_NOTIFY_EMAIL", "").strip()
    or os.environ.get("AGREEMENT_NOTIFY_EMAIL", "").strip()
    or "max@sportsnutrition.com"
)
MARKETPLACE_AGREEMENT_VERSION = "v2-supplier-direct-terms"
SESSION_PENDING_COMMIT_KEY = "marketplace_pending_commit"
SESSION_MARKETPLACE_ACCESS = "marketplace_member_access"
SESSION_SUPPLIER_REPORT_AUTH = "marketplace_supplier_report_auth"
SESSION_ADMIN_AUTH = "marketplace_admin_auth"
SESSION_BUYER_ACCOUNT_ID = "marketplace_buyer_account_id"
SESSION_SUPPLIER_ACCOUNT_ID = "marketplace_supplier_account_id"
PAYOUT_HOLD_DAYS = 14
MARKETPLACE_ADMIN_PASSWORD = os.environ.get("MARKETPLACE_ADMIN_PASSWORD", "").strip()
PLATFORM_SOURCED_FOLLOWUP_DAYS = 45
SITE_NAME = "TheNutraMarket"
SITE_TAGLINE = "Instant inventory marketplace for sports nutrition"
SITE_LEGAL_NAME = os.environ.get("SITE_LEGAL_NAME", "TheNutraMarket.com")
SITE_URL = os.environ.get("SITE_URL", "https://www.TheNutraMarket.com").rstrip("/")
CANONICAL_HOST = os.environ.get("CANONICAL_HOST", "www.thenutramarket.com").strip().lower()
CANONICAL_HOST_REDIRECT = os.environ.get("CANONICAL_HOST_REDIRECT", "1").strip().lower() in ("1", "true", "yes")
MARKETPLACE_DEMO_ACCESS_CODE = os.environ.get("MARKETPLACE_DEMO_ACCESS_CODE", "NM-DEMO").strip().upper()

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
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "").strip()
STRIPE_SUPPLIER_PRICE_ID = os.environ.get("STRIPE_SUPPLIER_PRICE_ID", "").strip()
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_CHECKOUT_ENABLED = bool(stripe and STRIPE_SECRET_KEY and STRIPE_SUPPLIER_PRICE_ID)
STRIPE_BUYER_CHECKOUT_ENABLED = bool(stripe and STRIPE_SECRET_KEY)
WEDGE_PRODUCT = SITE_NAME
WEDGE_PHASE_COPY = SITE_TAGLINE
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
    if not MARKETPLACE_REPORTED_TRANSACTIONS_FILE.exists():
        MARKETPLACE_REPORTED_TRANSACTIONS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_SUPPLIER_SUBSCRIPTIONS_FILE.exists():
        MARKETPLACE_SUPPLIER_SUBSCRIPTIONS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_FORUM_THREADS_FILE.exists():
        MARKETPLACE_FORUM_THREADS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_SUPPLIER_RATINGS_FILE.exists():
        MARKETPLACE_SUPPLIER_RATINGS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_AGREEMENT_SUBMISSIONS_FILE.exists():
        MARKETPLACE_AGREEMENT_SUBMISSIONS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_BUYER_ACCESS_FILE.exists():
        MARKETPLACE_BUYER_ACCESS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_SUPPLIER_INQUIRIES_FILE.exists():
        MARKETPLACE_SUPPLIER_INQUIRIES_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_BIDS_FILE.exists():
        MARKETPLACE_BIDS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_ORDERS_FILE.exists():
        MARKETPLACE_ORDERS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_BUYER_ACCOUNTS_FILE.exists():
        MARKETPLACE_BUYER_ACCOUNTS_FILE.write_text("[]", encoding="utf-8")
    if not MARKETPLACE_SUPPLIER_ACCOUNTS_FILE.exists():
        MARKETPLACE_SUPPLIER_ACCOUNTS_FILE.write_text("[]", encoding="utf-8")


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
    return [normalize_commit_record(row) for row in _safe_load_json_list(MARKETPLACE_COMMITS_FILE)]


def save_marketplace_commits(commits: list[dict]) -> None:
    prior: dict[str, dict] = {}
    if MARKETPLACE_COMMITS_FILE.exists():
        for row in _safe_load_json_list(MARKETPLACE_COMMITS_FILE):
            cid = str(row.get("id") or "")
            if cid:
                prior[cid] = row
    merged: list[dict] = []
    for commit in commits:
        row = normalize_commit_record(dict(commit))
        old = prior.get(str(row.get("id") or ""))
        if old and old.get("platform_sourced"):
            row["platform_sourced"] = True
        merged.append(row)
    MARKETPLACE_COMMITS_FILE.write_text(json.dumps(merged, indent=2), encoding="utf-8")


def load_reported_transactions() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_REPORTED_TRANSACTIONS_FILE)


def save_reported_transactions(rows: list[dict]) -> None:
    MARKETPLACE_REPORTED_TRANSACTIONS_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def normalize_commit_record(commit: dict, listing: dict | None = None) -> dict:
    """Ensure commit rows include platform-sourced fields; flag is sticky once true."""
    out = dict(commit)
    if listing:
        out.setdefault("supplier_public_code", str(listing.get("supplier_public_code") or ""))
        out.setdefault("supplier_company", str(listing.get("supplier_company") or ""))
        out.setdefault("ingredient", str(listing.get("ingredient") or ""))
    if out.get("platform_sourced"):
        out["platform_sourced"] = True
    elif out.get("buyer_name") or out.get("agreement_accepted"):
        out["platform_sourced"] = True
    return out


def mark_commit_platform_sourced(commit: dict, listing: dict) -> dict:
    row = normalize_commit_record(commit, listing)
    row["platform_sourced"] = True
    row["supplier_public_code"] = str(listing.get("supplier_public_code") or row.get("supplier_public_code") or "")
    row["supplier_company"] = str(listing.get("supplier_company") or row.get("supplier_company") or "")
    row["listing_id"] = str(listing.get("id") or row.get("listing_id") or "")
    row.setdefault("ingredient", str(listing.get("ingredient") or ""))
    return row


def _parse_commit_timestamp(commit: dict) -> datetime | None:
    raw = commit.get("timestamp") or commit.get("agreement_accepted_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")[:19])
    except ValueError:
        return None


def commit_matches_reported_transaction(commit: dict, report: dict) -> bool:
    if str(commit.get("supplier_public_code") or "") != str(report.get("supplier_public_code") or ""):
        return False
    commit_company = _norm_company(str(commit.get("buyer_company") or ""))
    commit_email = _norm_email(str(commit.get("buyer_contact_email") or ""))
    report_company = _norm_company(str(report.get("buyer_company") or ""))
    report_email = _norm_email(str(report.get("buyer_contact_email") or ""))
    if commit_email and report_email and commit_email == report_email:
        return True
    if commit_company and report_company and commit_company == report_company:
        return True
    return False


def commit_has_matching_report(commit: dict, reports: list[dict]) -> bool:
    return any(commit_matches_reported_transaction(commit, r) for r in reports)


def commit_is_unreported_platform_sourced(commit: dict, reports: list[dict], ref: datetime | None = None) -> bool:
    if not commit.get("platform_sourced"):
        return False
    ts = _parse_commit_timestamp(commit)
    if not ts:
        return False
    now = ref or datetime.now()
    if (now - ts).days <= PLATFORM_SOURCED_FOLLOWUP_DAYS:
        return False
    return not commit_has_matching_report(commit, reports)


def supplier_subscription_by_access(company: str, access_code: str) -> dict | None:
    company_n = _norm_company(company)
    code = (access_code or "").strip().upper()
    if not company_n or not code:
        return None
    for sub in load_supplier_subscriptions():
        st = (sub.get("status") or "active").lower()
        if st not in ("active", "trialing"):
            continue
        if _norm_company(sub.get("company_name", "")) != company_n:
            continue
        sub_code = str(sub.get("access_code") or "").strip().upper()
        if sub_code == code:
            return sub
    return None


def platform_sourced_commits_for_supplier(supplier_public_code: str) -> list[dict]:
    code = str(supplier_public_code or "").strip()
    return [
        c
        for c in load_marketplace_commits()
        if c.get("platform_sourced") and str(c.get("supplier_public_code") or "") == code
    ]


def admin_authenticated() -> bool:
    return bool(SESSION_ADMIN_AUTH in session and session.get(SESSION_ADMIN_AUTH) is True)


def supplier_report_authenticated() -> dict | None:
    row = session.get(SESSION_SUPPLIER_REPORT_AUTH)
    return row if isinstance(row, dict) else None


def load_buyer_accounts() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_BUYER_ACCOUNTS_FILE)


def save_buyer_accounts(rows: list[dict]) -> None:
    MARKETPLACE_BUYER_ACCOUNTS_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def load_supplier_accounts() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_SUPPLIER_ACCOUNTS_FILE)


def save_supplier_accounts(rows: list[dict]) -> None:
    MARKETPLACE_SUPPLIER_ACCOUNTS_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def load_marketplace_orders() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_ORDERS_FILE)


def save_marketplace_orders(rows: list[dict]) -> None:
    MARKETPLACE_ORDERS_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def find_buyer_account_by_id(account_id: str) -> dict | None:
    aid = str(account_id or "").strip()
    if not aid:
        return None
    return next((a for a in load_buyer_accounts() if str(a.get("id")) == aid), None)


def find_supplier_account_by_id(account_id: str) -> dict | None:
    aid = str(account_id or "").strip()
    if not aid:
        return None
    return next((a for a in load_supplier_accounts() if str(a.get("id")) == aid), None)


def find_buyer_account_by_email(email: str) -> dict | None:
    ne = _norm_email(email)
    if not ne:
        return None
    return next((a for a in load_buyer_accounts() if _norm_email(a.get("email", "")) == ne), None)


def find_supplier_account_by_email(email: str) -> dict | None:
    ne = _norm_email(email)
    if not ne:
        return None
    return next((a for a in load_supplier_accounts() if _norm_email(a.get("email", "")) == ne), None)


def current_buyer_account() -> dict | None:
    return find_buyer_account_by_id(str(session.get(SESSION_BUYER_ACCOUNT_ID) or ""))


def current_supplier_account() -> dict | None:
    return find_supplier_account_by_id(str(session.get(SESSION_SUPPLIER_ACCOUNT_ID) or ""))


def login_buyer(account: dict) -> None:
    session.pop(SESSION_SUPPLIER_ACCOUNT_ID, None)
    session[SESSION_BUYER_ACCOUNT_ID] = account["id"]


def login_supplier(account: dict) -> None:
    session.pop(SESSION_BUYER_ACCOUNT_ID, None)
    session[SESSION_SUPPLIER_ACCOUNT_ID] = account["id"]


def logout_marketplace_accounts() -> None:
    session.pop(SESSION_BUYER_ACCOUNT_ID, None)
    session.pop(SESSION_SUPPLIER_ACCOUNT_ID, None)


def buyer_login_required():
    account = current_buyer_account()
    if account:
        return account
    flash("Please sign in as a buyer to continue.", "error")
    return None


def supplier_login_required():
    account = current_supplier_account()
    if account:
        return account
    flash("Please sign in as a supplier to continue.", "error")
    return None


def listing_total_amount(listing: dict) -> float:
    unit_price = float(listing.get("price_per_kg") or 0)
    quantity = float(listing.get("quantity_kg") or 0)
    return round(unit_price * quantity, 2)


def payout_release_date_from(created_at: str) -> str:
    try:
        dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00")[:19])
    except ValueError:
        dt = datetime.now()
    return (dt + timedelta(days=PAYOUT_HOLD_DAYS)).date().isoformat()


def create_order_from_checkout_session(session_obj: dict) -> dict | None:
    if str(session_obj.get("payment_status") or "") != "paid":
        return None
    session_id = str(session_obj.get("id") or "")
    if not session_id:
        return None
    orders = load_marketplace_orders()
    existing = next((o for o in orders if o.get("stripe_session_id") == session_id), None)
    if existing:
        return existing

    metadata = session_obj.get("metadata") or {}
    listing_id = str(metadata.get("listing_id") or "")
    buyer_account_id = str(metadata.get("buyer_account_id") or "")
    listings = load_marketplace_listings()
    listing = next((x for x in listings if str(x.get("id")) == listing_id), None)
    if not listing:
        return None

    quantity = float(metadata.get("quantity") or listing.get("quantity_kg") or 0)
    unit_price = float(metadata.get("unit_price") or listing.get("price_per_kg") or 0)
    total_amount = float(metadata.get("total_amount") or listing_total_amount(listing))
    buyer = find_buyer_account_by_id(buyer_account_id)
    buyer_email = str(
        metadata.get("buyer_email")
        or (buyer or {}).get("email")
        or session_obj.get("customer_email")
        or ""
    )
    created_at = datetime.now().isoformat(timespec="seconds")
    order = {
        "order_id": str(uuid.uuid4()),
        "stripe_session_id": session_id,
        "listing_id": listing_id,
        "ingredient": str(listing.get("ingredient") or ""),
        "quantity": quantity,
        "unit_price": unit_price,
        "total_amount": total_amount,
        "buyer_account_id": buyer_account_id,
        "buyer_email": buyer_email,
        "supplier_public_code": str(listing.get("supplier_public_code") or ""),
        "order_status": "paid",
        "payout_status": "pending",
        "payout_release_date": payout_release_date_from(created_at),
        "created_at": created_at,
    }
    orders.append(order)
    save_marketplace_orders(orders)
    return order


def build_listing_row_from_form(form, supplier_company: str, supplier_contact_email: str, existing: dict | None = None) -> dict:
    ingredient = form.get("ingredient", "").strip()
    price_per_kg = _num_or_none(form.get("price_per_kg", ""))
    quantity_kg = _num_or_none(form.get("quantity_kg", ""))
    coa_document = form.get("coa_document", "").strip()
    category = form.get("category", "Ingredient").strip() or "Ingredient"
    sale_mode = form.get("sale_mode", "buy_now").strip().lower()
    if sale_mode not in ("buy_now", "auction"):
        sale_mode = "buy_now"
    if category not in ("Ingredient", "Flavoring", "Packaging"):
        category = "Ingredient"
    listing = dict(existing) if existing else {}
    listing.update(
        {
            "category": category,
            "supplier_company": supplier_company,
            "supplier_contact_email": supplier_contact_email,
            "supplier_public_code": get_or_assign_supplier_public_code(supplier_company, supplier_contact_email),
            "ingredient": ingredient,
            "unit": str(listing.get("unit") or "kg"),
            "price_per_kg": price_per_kg,
            "quantity_kg": quantity_kg,
            "coa_document": coa_document,
            "expires_on": form.get("expires_on", "").strip(),
            "notes": form.get("notes", "").strip(),
            "sale_mode": sale_mode,
        }
    )
    if not existing:
        listing["id"] = str(uuid.uuid4())
        listing["created_at"] = datetime.now().isoformat(timespec="seconds")
    if sale_mode == "auction":
        starting_bid = _num_or_none(form.get("starting_bid_per_kg", ""))
        auction_days_raw = form.get("auction_days", "3").strip()
        try:
            auction_days = max(1, min(14, int(auction_days_raw)))
        except ValueError:
            auction_days = 3
        listing["starting_bid_per_kg"] = starting_bid if starting_bid is not None else round(float(price_per_kg or 0) * 0.82, 2)
        listing["bid_increment"] = listing_bid_increment(listing)
        listing["auction_ends_at"] = (datetime.now() + timedelta(days=auction_days)).isoformat(timespec="seconds")
    return listing


def load_marketplace_bids() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_BIDS_FILE)


def save_marketplace_bids(bids: list[dict]) -> None:
    MARKETPLACE_BIDS_FILE.write_text(json.dumps(bids, indent=2), encoding="utf-8")


def load_agreement_submissions() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_AGREEMENT_SUBMISSIONS_FILE)


def save_agreement_submissions(rows: list[dict]) -> None:
    ensure_data_store()
    MARKETPLACE_AGREEMENT_SUBMISSIONS_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def ensure_supplier_access_codes() -> None:
    subs = load_supplier_subscriptions()
    changed = False
    for row in subs:
        status = (row.get("status") or "active").lower()
        if status in ("active", "trialing") and not row.get("access_code"):
            row["access_code"] = _generate_unique_access_code()
            changed = True
    if changed:
        save_supplier_subscriptions(subs)


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


def _all_access_codes() -> set[str]:
    codes: set[str] = set()
    for sub in load_supplier_subscriptions():
        code = (sub.get("access_code") or "").strip().upper()
        if code:
            codes.add(code)
    for raw in os.environ.get("MARKETPLACE_ACCESS_CODES", "").split(","):
        code = raw.strip().upper()
        if code:
            codes.add(code)
    if MARKETPLACE_DEMO_ACCESS_CODE:
        codes.add(MARKETPLACE_DEMO_ACCESS_CODE)
    return codes


def _generate_unique_access_code() -> str:
    existing = _all_access_codes()
    for _ in range(80):
        cand = "NM-" + uuid.uuid4().hex[:8].upper()
        if cand not in existing:
            return cand
    return "NM-" + uuid.uuid4().hex[:12].upper()


def get_or_assign_access_code(company: str, email: str) -> str:
    subs = load_supplier_subscriptions()
    row = _find_subscription_row(subs, company, email)
    if row and row.get("access_code"):
        return str(row["access_code"])
    code = _generate_unique_access_code()
    if row:
        row["access_code"] = code
        save_supplier_subscriptions(subs)
    return code


def marketplace_has_access() -> bool:
    return True


def valid_marketplace_access_code(code: str) -> bool:
    normalized = (code or "").strip().upper()
    if not normalized:
        return False
    return normalized in _all_access_codes()


def grant_marketplace_access() -> None:
    session[SESSION_MARKETPLACE_ACCESS] = True


def load_buyer_access_requests() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_BUYER_ACCESS_FILE)


def save_buyer_access_requests(rows: list[dict]) -> None:
    MARKETPLACE_BUYER_ACCESS_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def load_supplier_inquiries() -> list[dict]:
    return _safe_load_json_list(MARKETPLACE_SUPPLIER_INQUIRIES_FILE)


def save_supplier_inquiries(rows: list[dict]) -> None:
    MARKETPLACE_SUPPLIER_INQUIRIES_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


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
    if not row.get("access_code"):
        row["access_code"] = _generate_unique_access_code()
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
    if not row.get("access_code"):
        row["access_code"] = _generate_unique_access_code()
    save_supplier_subscriptions(subs)


def _marketplace_assistant_meaningful_tokens(low: str) -> list[str]:
    raw = [t for t in low.replace(",", " ").split() if len(t) > 2]
    return [t for t in raw if t not in _MARKETPLACE_ASSISTANT_STOPWORDS]


def marketplace_assistant_reply(message: str) -> str:
    """Rule-based assistant + search listings, alerts, and forum (no external API)."""
    raw = (message or "").strip()
    if not raw:
        return "Ask about ingredients, flavorings, packaging, supplier enrollment, COA requirements, or community threads."

    low = raw.lower()

    if any(
        k in low
        for k in (
            "fee",
            "brokerage",
            "commission",
            "vig",
            "percent",
            "platform fee",
            "marketplace fee",
            "agreement",
            "contract",
            "terms",
        )
    ):
        return (
            "Commercial terms are negotiated directly between buyers and our onboarded suppliers. "
            f"{SITE_NAME} facilitates introductions only—we are not a party to supplier agreements. "
            "Use Request intro on a listing to start the supplier-direct process."
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
        return (
            f"Supplier onboarding is handled by our team. Go to List inventory, submit the inquiry form, "
            f"or email {SUPPLIER_ONBOARDING_EMAIL}. We will follow up before any listings go live."
        )

    if any(
        k in low
        for k in (
            "list inventory",
            "sell on",
            "become a supplier",
            "supplier enrollment",
            "enroll as supplier",
            "post a listing",
            "publish a lot",
        )
    ):
        return (
            f"To list inventory, open List inventory and submit your company details—we will email you "
            f"to complete onboarding. You can also reach us at {SUPPLIER_ONBOARDING_EMAIL}."
        )

    if "rating" in low or "review" in low or "stars" in low:
        n = len(load_supplier_ratings())
        return (
            f"Buyers who have committed on a listing can rate the supplier using the anonymous supplier code (SX-…) shown on that row—"
            f"company names stay hidden until commitment. There are {n} rating record(s) on file."
        )

    if any(k in low for k in ("forum", "community", "procurement", "network")) and "listing" not in low:
        return (
            "Open Community to start or reply to sourcing threads with other buyers and suppliers. "
            "For deals, use Live inventory and Request intro on a specific lot."
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
            "Listing prices vary by product and lot—search Live inventory or name an ingredient. "
            f"To sell on the marketplace, submit a supplier inquiry under List inventory or email {SUPPLIER_ONBOARDING_EMAIL}."
        )

    return (
        f"I could not match that to a specific listing. Try a product name (e.g. collagen), "
        f"or ask about supplier enrollment, COA, or community threads."
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


def listing_sale_mode(listing: dict) -> str:
    mode = str(listing.get("sale_mode") or "").strip().lower()
    if mode in ("buy_now", "auction"):
        return mode
    notes = (listing.get("notes") or "").lower()
    if any(k in notes for k in AUCTION_NOTE_KEYWORDS):
        return "auction"
    return "buy_now"


def listing_starting_bid_per_kg(listing: dict) -> float:
    raw = listing.get("starting_bid_per_kg")
    if raw is not None:
        return float(raw)
    return round(float(listing.get("price_per_kg") or 0) * 0.82, 2)


def listing_bid_increment(listing: dict) -> float:
    raw = listing.get("bid_increment")
    if raw is not None:
        return float(raw)
    price = float(listing.get("price_per_kg") or 0)
    if price >= 20:
        return 0.25
    if price >= 10:
        return 0.10
    return DEFAULT_BID_INCREMENT


def listing_auction_ends_at(listing: dict) -> datetime | None:
    raw = listing.get("auction_ends_at")
    if raw:
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00")[:19])
        except ValueError:
            pass
    expires = listing.get("expires_on")
    if expires:
        try:
            return datetime.combine(date.fromisoformat(str(expires)[:10]), datetime.max.time()).replace(
                hour=23, minute=59, second=0, microsecond=0
            )
        except ValueError:
            pass
    created = listing.get("created_at")
    if created:
        try:
            return datetime.fromisoformat(str(created)[:19]) + timedelta(days=3)
        except ValueError:
            pass
    return None


def bids_for_listing(listing_id: str, bids: list[dict] | None = None) -> list[dict]:
    rows = bids if bids is not None else load_marketplace_bids()
    return [b for b in rows if str(b.get("listing_id")) == str(listing_id)]


def current_bid_per_kg(listing: dict, bids: list[dict] | None = None) -> float:
    listing_bids = bids_for_listing(str(listing.get("id")), bids)
    if not listing_bids:
        return listing_starting_bid_per_kg(listing)
    return max(float(b.get("bid_per_kg") or 0) for b in listing_bids)


def min_next_bid_per_kg(listing: dict, bids: list[dict] | None = None) -> float:
    current = current_bid_per_kg(listing, bids)
    starting = listing_starting_bid_per_kg(listing)
    increment = listing_bid_increment(listing)
    if not bids_for_listing(str(listing.get("id")), bids):
        return starting
    return round(current + increment, 2)


def auction_is_open(listing: dict, now: datetime | None = None) -> bool:
    if listing_sale_mode(listing) != "auction":
        return False
    ends = listing_auction_ends_at(listing)
    if not ends:
        return True
    ref = now or datetime.now()
    return ref <= ends


def auction_time_left_label(listing: dict, now: datetime | None = None) -> str:
    ends = listing_auction_ends_at(listing)
    if not ends:
        return "Open auction"
    ref = now or datetime.now()
    if ref > ends:
        return "Auction ended"
    delta = ends - ref
    if delta.days >= 1:
        return f"{delta.days} day{'s' if delta.days != 1 else ''} left"
    hours = max(1, int(delta.total_seconds() // 3600))
    return f"{hours} hour{'s' if hours != 1 else ''} left"


def listing_display_badge(listing: dict) -> str:
    notes = (listing.get("notes") or "").lower()
    qty = float(listing.get("quantity_kg") or 0)
    price = float(listing.get("price_per_kg") or 0)
    if any(x in notes for x in ("48-hour", "liquidation", "urgent", "best bid")):
        return "Trending"
    if qty < 800 or price >= 25:
        return "Rare"
    if price <= 4.5:
        return "Value"
    return "Classic"


def listing_days_left(expires_on: str | None) -> int | None:
    if not expires_on:
        return None
    try:
        exp = date.fromisoformat(str(expires_on)[:10])
        return max(0, (exp - date.today()).days)
    except ValueError:
        return None


INGREDIENT_TAXONOMY_OPTIONS = (
    ("vitamins", "Vitamins"),
    ("minerals", "Minerals"),
    ("amino_acids", "Amino acids"),
    ("botanicals", "Botanicals"),
    ("protein", "Protein"),
    ("other", "Other"),
)

CERTIFICATION_FILTER_OPTIONS = ("Organic", "Non-GMO", "Kosher", "Halal", "NSF")


def listing_ingredient_taxonomy(ingredient: str, category: str) -> str:
    text = (ingredient or "").lower()
    if category in ("Packaging", "Flavoring"):
        return "other"
    if any(x in text for x in ("whey", "protein", "collagen", "peptide", "isolate 90", "hydrolyzed whey")):
        return "protein"
    if any(
        x in text
        for x in (
            "creatine",
            "beta-alanine",
            "citrulline",
            "glutamine",
            "taurine",
            "bcaa",
            "eaa",
            "hmb",
            "amino",
        )
    ):
        return "amino_acids"
    if any(x in text for x in ("vitamin", "cholecalciferol", "ascorbic", "vit d", "d3")):
        return "vitamins"
    if any(
        x in text
        for x in ("magnesium", "zinc", "sodium", "electrolyte", "bicarbonate", "bisglycinate", "glycinate")
    ):
        return "minerals"
    if any(
        x in text
        for x in (
            "ashwagandha",
            "rhodiola",
            "turmeric",
            "curcumin",
            "green tea",
            "beet",
            "botanical",
            "herbal",
            "extract",
            "ksm-66",
            "stevia",
            "monk fruit",
        )
    ):
        return "botanicals"
    return "other"


def listing_taxonomy_monogram(taxonomy: str) -> str:
    return {
        "vitamins": "VI",
        "minerals": "MI",
        "amino_acids": "AA",
        "botanicals": "BO",
        "protein": "PR",
        "other": "OT",
    }.get(taxonomy, "OT")


def listing_form_label(ingredient: str, notes: str) -> str:
    text = f"{ingredient} {notes}".lower()
    if "liquid" in text or " oil" in text:
        return "Liquid"
    if "granular" in text:
        return "Granular"
    if any(x in text for x in ("mesh", "micronized", "powder", "instantized", "instant")):
        return "Powder"
    if "unit" in text or "bottle" in text or "pouch" in text or "cap" in text:
        return "Unit"
    return "Powder"


def listing_visual_type(category: str) -> str:
    c = (category or "Ingredient").strip().lower()
    if c == "packaging":
        return "packaging"
    if c == "flavoring":
        return "flavoring"
    return "ingredient"


def listing_certifications_from_notes(notes: str) -> list[str]:
    n = (notes or "").lower()
    found: list[str] = []
    for cert, keys in (
        ("Organic", ("organic",)),
        ("Non-GMO", ("non-gmo", "nongmo")),
        ("Kosher", ("kosher",)),
        ("Halal", ("halal",)),
        ("NSF", ("nsf",)),
    ):
        if any(k in n for k in keys):
            found.append(cert)
    return found


def listing_price_tier_chips(listing: dict) -> list[str]:
    """Volume tier hints from notes; estimated $/kg when notes mention breaks/thresholds."""
    notes = (listing.get("notes") or "").lower()
    price = float(listing.get("price_per_kg") or 0)
    if not price or not any(k in notes for k in ("moq", "threshold", "volume", "break", "drop")):
        return []
    return [
        f"25kg+: ${price * 0.92:.2f}",
        f"100kg+: ${price * 0.85:.2f}",
    ]


def listing_listed_date_label(created_at: str | None) -> str:
    if not created_at:
        return ""
    try:
        dt = datetime.fromisoformat(str(created_at)[:19])
        return f"Listed {dt.strftime('%b %d, %Y')}"
    except ValueError:
        return ""


def _num_arg(val: str | None) -> float | None:
    if val is None or not str(val).strip():
        return None
    try:
        return float(val)
    except ValueError:
        return None


def apply_buy_now_listing_filters(listings: list[dict], args) -> list[dict]:
    taxonomies = [t.strip() for t in args.getlist("taxonomy") if t.strip()]
    certs = [c.strip() for c in args.getlist("cert") if c.strip()]
    price_min = _num_arg(args.get("price_min"))
    price_max = _num_arg(args.get("price_max"))
    qty_min = _num_arg(args.get("qty_min"))
    rating_floor = (args.get("rating") or "any").strip().lower()
    coa_only = (args.get("coa_only") or "").strip().lower() in ("1", "true", "yes", "on")
    cat = (args.get("category") or "").strip()
    q = (args.get("q") or "").strip().lower()

    out = listings
    if cat:
        out = [x for x in out if x.get("category") == cat]
    if taxonomies:
        out = [x for x in out if x.get("ingredient_taxonomy") in taxonomies]
    if certs:
        out = [x for x in out if any(c in (x.get("certifications") or []) for c in certs)]
    if price_min is not None:
        out = [x for x in out if float(x.get("price_per_kg") or 0) >= price_min]
    if price_max is not None:
        out = [x for x in out if float(x.get("price_per_kg") or 0) <= price_max]
    if qty_min is not None:
        out = [x for x in out if float(x.get("quantity_kg") or 0) >= qty_min]
    if rating_floor == "4":
        out = [x for x in out if float(x.get("supplier_rating_avg") or 0) >= 4]
    elif rating_floor == "3":
        out = [x for x in out if float(x.get("supplier_rating_avg") or 0) >= 3]
    if coa_only:
        out = [x for x in out if x.get("coa_on_file")]
    if q:
        out = [
            x
            for x in out
            if q
            in f"{x.get('ingredient', '')} {x.get('supplier_public_name', '')} {x.get('notes', '')} {x.get('coa_document', '')}".lower()
        ]
    return out


def sort_buy_now_listings(listings: list[dict], sort_key: str) -> list[dict]:
    key = (sort_key or "newest").strip().lower()
    items = list(listings)
    if key == "price_asc":
        items.sort(key=lambda x: float(x.get("price_per_kg") or 0))
    elif key == "price_desc":
        items.sort(key=lambda x: float(x.get("price_per_kg") or 0), reverse=True)
    elif key == "qty_desc":
        items.sort(key=lambda x: float(x.get("quantity_kg") or 0), reverse=True)
    elif key == "rating_desc":
        items.sort(key=lambda x: float(x.get("supplier_rating_avg") or 0), reverse=True)
    else:
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


def listings_for_marketplace_view(sale_mode: str | None = None) -> list[dict]:
    """Public catalog rows with supplier name, category, WineBid-style display fields."""
    ensure_all_listing_supplier_codes()
    listings = sorted(load_marketplace_listings(), key=lambda x: x.get("created_at", ""), reverse=True)
    all_bids = load_marketplace_bids()
    rating_agg = build_supplier_rating_aggregates()
    out: list[dict] = []
    for listing in listings:
        mode = listing_sale_mode(listing)
        if sale_mode and mode != sale_mode:
            continue
        if sale_mode == "auction" and not auction_is_open(listing):
            continue
        item = dict(listing)
        code = str(listing.get("supplier_public_code") or "")
        agg = rating_agg.get(code)
        unit = str(listing.get("unit") or "kg").lower()
        price = float(listing.get("price_per_kg") or 0)
        qty = float(listing.get("quantity_kg") or 0)
        item["sale_mode"] = mode
        item["supplier_public_code"] = code
        item["supplier_rating_display"] = format_supplier_rating_pill(agg)
        item["supplier_rating_avg"] = float(agg["avg"]) if agg and agg.get("count") else 0.0
        item["supplier_public_name"] = str(listing.get("supplier_company") or "Supplier")
        item["category"] = str(listing.get("category") or "Ingredient")
        item["unit"] = unit
        taxonomy = listing_ingredient_taxonomy(str(listing.get("ingredient") or ""), item["category"])
        item["ingredient_taxonomy"] = taxonomy
        item["taxonomy_monogram"] = listing_taxonomy_monogram(taxonomy)
        item["form_label"] = listing_form_label(str(listing.get("ingredient") or ""), str(listing.get("notes") or ""))
        item["visual_type"] = listing_visual_type(item["category"])
        item["certifications"] = listing_certifications_from_notes(str(listing.get("notes") or ""))
        item["price_tier_chips"] = listing_price_tier_chips(listing)
        item["coa_on_file"] = bool(str(listing.get("coa_document") or "").strip())
        item["supplier_verified"] = supplier_subscription_active(
            str(listing.get("supplier_company") or ""),
            str(listing.get("supplier_contact_email") or ""),
        )
        item["listed_date_label"] = listing_listed_date_label(listing.get("created_at"))
        days = listing_days_left(listing.get("expires_on"))
        item["days_left"] = days
        item["expires_soon"] = days is not None and days <= 14
        item["expires_urgent"] = days is not None and days < 5
        item["badge"] = "Auction" if mode == "auction" else listing_display_badge(listing)
        item["days_left_label"] = f"{days} days left" if days is not None else "Open lot"
        listing_bids = bids_for_listing(str(listing.get("id")), all_bids)
        item["bid_count"] = len(listing_bids)
        item["auction_open"] = auction_is_open(listing)
        item["auction_time_left_label"] = auction_time_left_label(listing)
        item["starting_bid_per_kg"] = listing_starting_bid_per_kg(listing)
        item["bid_increment"] = listing_bid_increment(listing)
        item["current_bid_per_kg"] = current_bid_per_kg(listing, all_bids)
        item["min_next_bid_per_kg"] = min_next_bid_per_kg(listing, all_bids)
        if unit == "kg":
            item["quantity_display"] = f"{qty:,.0f} kg available"
        else:
            item["quantity_display"] = f"{qty:,.0f} units available"
        if mode == "auction":
            current = item["current_bid_per_kg"]
            item["price_amount"] = f"${current:,.2f}"
            item["price_unit_label"] = f"current bid per {unit if unit != 'kg' else 'kg'}"
            item["compare_price_display"] = f"${price:,.2f}/{unit if unit != 'kg' else 'kg'} list"
            item["price_display"] = f"${current:,.2f}/{unit if unit != 'kg' else 'kg'}"
            item["time_label"] = item["auction_time_left_label"]
        else:
            item["price_amount"] = f"${price:,.2f}"
            item["price_unit_label"] = f"per {unit if unit != 'kg' else 'kg'}"
            item["price_display"] = f"${price:,.2f}/{unit if unit != 'kg' else 'kg'}"
            item["total_lot_amount"] = listing_total_amount(listing)
            item["total_lot_display"] = f"${item['total_lot_amount']:,.2f}"
            item["time_label"] = item["days_left_label"]
        out.append(item)
    if sale_mode != "auction":
        out.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    else:
        out.sort(key=lambda x: str(x.get("ingredient") or "").lower())
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
        "supplier_launch_free": SUPPLIER_LAUNCH_FREE,
        "supplier_onboarding_email": SUPPLIER_ONBOARDING_EMAIL,
        "stripe_checkout_enabled": STRIPE_CHECKOUT_ENABLED,
        "stripe_buyer_checkout_enabled": STRIPE_BUYER_CHECKOUT_ENABLED,
        "stripe_publishable_key": STRIPE_PUBLISHABLE_KEY,
        "current_buyer_account": current_buyer_account(),
        "current_supplier_account": current_supplier_account(),
        "site_name": SITE_NAME,
        "site_tagline": SITE_TAGLINE,
        "site_legal_name": SITE_LEGAL_NAME,
        "site_url": SITE_URL,
        "canonical_url": f"{SITE_URL}{request.path}" if request.path else SITE_URL,
        "marketplace_has_access": marketplace_has_access(),
        "marketplace_mode": (
            (lambda m: m if m in ("buy_now", "auction") else "buy_now")(
                request.args.get("mode", "buy_now").strip().lower()
            )
            if (request.path or "").startswith("/marketplace") and request.endpoint == "marketplace"
            else "buy_now"
        ),
    }


@app.before_request
def redirect_to_canonical_host() -> None | object:
    if not CANONICAL_HOST_REDIRECT or not CANONICAL_HOST:
        return None
    host = (request.host or "").split(":")[0].lower()
    if host in ("127.0.0.1", "localhost") or host.endswith(".railway.app"):
        return None
    if host == CANONICAL_HOST:
        return None
    bare = CANONICAL_HOST.removeprefix("www.")
    if host == bare:
        target = f"{SITE_URL}{request.path}"
        if request.query_string:
            target += f"?{request.query_string.decode()}"
        return redirect(target, code=301)
    return None


@app.template_global()
def marketplace_listing_href(listing_id: str) -> str:
    """Preserve current marketplace query params when linking to a listing."""
    pairs: list[tuple[str, str]] = []
    for key in request.args:
        if key == "listing":
            continue
        for val in request.args.getlist(key):
            pairs.append((key, val))
    pairs.append(("listing", listing_id))
    qs = urlencode(pairs)
    return f"{url_for('marketplace')}?{qs}" if qs else url_for("marketplace", listing=listing_id)


def render_marketplace():
    summary = build_marketplace_summary()
    mode = request.args.get("mode", "buy_now").strip().lower()
    if mode not in ("buy_now", "auction"):
        mode = "auction"
    listings_for_view = listings_for_marketplace_view(sale_mode=mode)
    q = request.args.get("q", "").strip().lower()
    cat = request.args.get("category", "").strip()
    sort_key = request.args.get("sort", "newest").strip()
    filter_taxonomies = [t.strip() for t in request.args.getlist("taxonomy") if t.strip()]
    filter_certs = [c.strip() for c in request.args.getlist("cert") if c.strip()]
    filter_price_min = request.args.get("price_min", "").strip()
    filter_price_max = request.args.get("price_max", "").strip()
    filter_qty_min = request.args.get("qty_min", "").strip()
    filter_rating = request.args.get("rating", "any").strip()
    filter_coa_only = request.args.get("coa_only", "").strip().lower() in ("1", "true", "yes", "on")

    if mode == "buy_now":
        listings_for_view = apply_buy_now_listing_filters(listings_for_view, request.args)
        listings_for_view = sort_buy_now_listings(listings_for_view, sort_key)
    else:
        if cat:
            listings_for_view = [x for x in listings_for_view if x.get("category") == cat]
        if q:
            listings_for_view = [
                x
                for x in listings_for_view
                if q
                in f"{x.get('ingredient', '')} {x.get('supplier_public_name', '')} {x.get('notes', '')} {x.get('coa_document', '')}".lower()
            ]
    matches = build_marketplace_matches()
    raw_listing = request.args.get("listing", "").strip()
    prefill_listing_id = ""
    if raw_listing and any(str(x.get("id")) == raw_listing for x in listings_for_view):
        prefill_listing_id = raw_listing
    return render_template(
        "marketplace_home.html",
        summary=summary,
        listings=listings_for_view,
        matches=matches,
        prefill_listing_id=prefill_listing_id,
        marketplace_nav_active="marketplace",
        marketplace_mode=mode,
        filter_q=q,
        filter_category=cat,
        filter_sort=sort_key,
        filter_taxonomies=filter_taxonomies,
        filter_certs=filter_certs,
        filter_price_min=filter_price_min,
        filter_price_max=filter_price_max,
        filter_qty_min=filter_qty_min,
        filter_rating=filter_rating,
        filter_coa_only=filter_coa_only,
        ingredient_taxonomy_options=INGREDIENT_TAXONOMY_OPTIONS,
        certification_filter_options=CERTIFICATION_FILTER_OPTIONS,
    )


@app.route("/")
@app.route("/marketplace")
def marketplace():
    return render_marketplace()


@app.route("/marketplace/hub")
def marketplace_hub():
    return redirect(url_for("marketplace_suppliers"))


@app.route("/marketplace/enter", methods=["POST"])
def marketplace_enter():
    code = request.form.get("access_code", "").strip()
    if valid_marketplace_access_code(code):
        grant_marketplace_access()
        flash("Welcome to the marketplace.", "success")
    else:
        flash("Invalid access code.", "error")
    return redirect(url_for("marketplace"))


@app.route("/marketplace/buyer-access", methods=["POST"])
def marketplace_buyer_access():
    company = request.form.get("company_name", "").strip()
    email = request.form.get("contact_email", "").strip()
    contact_name = request.form.get("contact_name", "").strip()
    if not company or not email:
        flash("Company name and contact email are required.", "error")
        return redirect(url_for("marketplace"))
    rows = load_buyer_access_requests()
    rows.append(
        {
            "id": str(uuid.uuid4()),
            "company_name": company,
            "contact_name": contact_name,
            "contact_email": email,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    save_buyer_access_requests(rows)
    flash(
        f"Thanks, {company} — you can browse listings and set ingredient alerts anytime.",
        "success",
    )
    return redirect(url_for("marketplace"))


@app.route("/playbook")
def sales_playbook():
    return render_template("sales_playbook.html")


@app.route("/sell-sheet")
def sell_sheet():
    return render_template("sell_sheet.html")


@app.route("/legal-agreements")
def legal_agreements():
    return render_template("legal_agreements.html")


@app.route("/marketplace/auctions")
def marketplace_auctions():
    args = {k: v for k, v in request.args.items() if k != "mode"}
    return redirect(url_for("marketplace", mode="auction", **args))


@app.route("/marketplace/bid", methods=["POST"])
def place_marketplace_bid():
    listing_id = request.form.get("listing_id", "").strip()
    company = request.form.get("bidder_company", "").strip()
    email = request.form.get("bidder_contact_email", "").strip()
    bid_per_kg = _num_or_none(request.form.get("bid_per_kg", ""))
    if not listing_id or not company or not email or bid_per_kg is None:
        flash("Listing, company, email, and bid amount are required.", "error")
        return redirect(url_for("marketplace", mode="auction", listing=listing_id or None))
    listings = load_marketplace_listings()
    listing = next((x for x in listings if str(x.get("id")) == listing_id), None)
    if not listing or listing_sale_mode(listing) != "auction":
        flash("That lot is not an open auction.", "error")
        return redirect(url_for("marketplace", mode="auction"))
    if not auction_is_open(listing):
        flash("This auction has ended.", "error")
        return redirect(url_for("marketplace", mode="auction"))
    min_bid = min_next_bid_per_kg(listing)
    if bid_per_kg + 1e-9 < min_bid:
        flash(f"Minimum bid is ${min_bid:,.2f} per unit.", "error")
        return redirect(url_for("marketplace", mode="auction", listing=listing_id) + "#bid-flow")
    bids = load_marketplace_bids()
    bids.append(
        {
            "id": str(uuid.uuid4()),
            "listing_id": listing_id,
            "bidder_company": company,
            "bidder_contact_email": email,
            "bid_per_kg": bid_per_kg,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    save_marketplace_bids(bids)
    flash(
        f"Bid recorded at ${bid_per_kg:,.2f} on {listing.get('ingredient')}. "
        "Winning bidders complete terms directly with the supplier.",
        "success",
    )
    return redirect(url_for("marketplace", mode="auction", listing=listing_id) + "#bid-flow")


@app.route("/marketplace/listings")
def marketplace_listings_page():
    return redirect(url_for("marketplace"))


@app.route("/marketplace/buy")
def marketplace_buy():
    return redirect(url_for("marketplace", **request.args))


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


@app.route("/marketplace/suppliers/report", methods=["GET", "POST"])
def marketplace_supplier_report():
    auth = supplier_report_authenticated()
    if request.method == "POST" and request.form.get("action") == "login":
        company = request.form.get("company_name", "").strip()
        access_code = request.form.get("access_code", "").strip()
        sub = supplier_subscription_by_access(company, access_code)
        if not sub:
            flash("Company and access code did not match an active supplier subscription.", "error")
            return redirect(url_for("marketplace_supplier_report"))
        session[SESSION_SUPPLIER_REPORT_AUTH] = {
            "company_name": sub.get("company_name"),
            "public_supplier_code": sub.get("public_supplier_code"),
            "access_code": sub.get("access_code"),
        }
        flash("Signed in for transaction reporting.", "success")
        return redirect(url_for("marketplace_supplier_report"))

    if request.method == "POST" and request.form.get("action") == "logout":
        session.pop(SESSION_SUPPLIER_REPORT_AUTH, None)
        flash("Signed out of transaction reporting.", "info")
        return redirect(url_for("marketplace_supplier_report"))

    platform_buyers: list[dict] = []
    recent_reports: list[dict] = []
    if auth:
        code = str(auth.get("public_supplier_code") or "")
        platform_buyers = platform_sourced_commits_for_supplier(code)
        recent_reports = sorted(
            [
                r
                for r in load_reported_transactions()
                if str(r.get("supplier_public_code") or "") == code
            ],
            key=lambda r: r.get("reported_at", ""),
            reverse=True,
        )[:20]

    summary = build_marketplace_summary()
    return render_template(
        "marketplace_supplier_report.html",
        summary=summary,
        marketplace_nav_active="suppliers",
        supplier_auth=auth,
        platform_buyers=platform_buyers,
        recent_reports=recent_reports,
        vig_rate_pct=int(MARKETPLACE_VIG_RATE * 100),
    )


@app.route("/marketplace/suppliers/report/submit", methods=["POST"])
def marketplace_supplier_report_submit():
    auth = supplier_report_authenticated()
    if not auth:
        flash("Sign in with your supplier company and access code to report a transaction.", "error")
        return redirect(url_for("marketplace_supplier_report"))

    supplier_company = str(auth.get("company_name") or "").strip()
    supplier_public_code = str(auth.get("public_supplier_code") or "").strip()
    buyer_company = request.form.get("buyer_company", "").strip()
    buyer_contact_email = request.form.get("buyer_contact_email", "").strip()
    transaction_date = request.form.get("transaction_date", "").strip()
    gross_raw = request.form.get("gross_value", "").strip()
    note = request.form.get("note", "").strip()

    if not buyer_company or not transaction_date or not gross_raw:
        flash("Buyer company, transaction date, and gross value are required.", "error")
        return redirect(url_for("marketplace_supplier_report"))

    try:
        gross_value = float(gross_raw)
    except ValueError:
        flash("Gross value must be a number.", "error")
        return redirect(url_for("marketplace_supplier_report"))
    if gross_value <= 0:
        flash("Gross value must be greater than zero.", "error")
        return redirect(url_for("marketplace_supplier_report"))

    try:
        datetime.strptime(transaction_date, "%Y-%m-%d")
    except ValueError:
        flash("Transaction date must be YYYY-MM-DD.", "error")
        return redirect(url_for("marketplace_supplier_report"))

    platform_commits = platform_sourced_commits_for_supplier(supplier_public_code)
    probe = {
        "supplier_public_code": supplier_public_code,
        "buyer_company": buyer_company,
        "buyer_contact_email": buyer_contact_email,
    }
    if not any(commit_matches_reported_transaction(c, probe) for c in platform_commits):
        flash(
            "That buyer does not match a platform-sourced intro on file. "
            "Use the company (and email if known) from your platform introduction.",
            "error",
        )
        return redirect(url_for("marketplace_supplier_report"))

    fee_owed = round(gross_value * MARKETPLACE_VIG_RATE, 2)
    row = {
        "id": str(uuid.uuid4()),
        "supplier_company": supplier_company,
        "supplier_public_code": supplier_public_code,
        "buyer_company": buyer_company,
        "buyer_contact_email": buyer_contact_email,
        "transaction_date": transaction_date,
        "gross_value": gross_value,
        "fee_owed": fee_owed,
        "note": note,
        "reported_at": datetime.now().isoformat(timespec="seconds"),
        "verified": False,
    }
    reports = load_reported_transactions()
    reports.append(row)
    save_reported_transactions(reports)
    flash(
        f"Transaction reported. Platform fee owed: ${fee_owed:,.2f} ({int(MARKETPLACE_VIG_RATE * 100)}% of ${gross_value:,.2f}).",
        "success",
    )
    return redirect(url_for("marketplace_supplier_report"))


@app.route("/marketplace/admin/login", methods=["GET", "POST"])
def marketplace_admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if not MARKETPLACE_ADMIN_PASSWORD:
            flash("Admin access is not configured (set MARKETPLACE_ADMIN_PASSWORD).", "error")
            return redirect(url_for("marketplace_admin_login"))
        if password == MARKETPLACE_ADMIN_PASSWORD:
            session[SESSION_ADMIN_AUTH] = True
            return redirect(url_for("marketplace_admin_transactions"))
        flash("Invalid admin password.", "error")
    return render_template("marketplace_admin_login.html")


@app.route("/marketplace/admin/logout")
def marketplace_admin_logout():
    session.pop(SESSION_ADMIN_AUTH, None)
    flash("Signed out of admin.", "info")
    return redirect(url_for("marketplace_admin_login"))


@app.route("/marketplace/admin/transactions")
def marketplace_admin_transactions():
    if not admin_authenticated():
        return redirect(url_for("marketplace_admin_login"))

    reports = sorted(load_reported_transactions(), key=lambda r: r.get("transaction_date", ""), reverse=True)
    commits = [c for c in load_marketplace_commits() if c.get("platform_sourced")]
    unreported_commits: list[dict] = []
    for commit in commits:
        if commit_is_unreported_platform_sourced(commit, reports):
            unreported_commits.append(commit)
    unreported_commits.sort(key=lambda c: c.get("timestamp", ""), reverse=True)

    return render_template(
        "marketplace_admin_transactions.html",
        reported_transactions=reports,
        unreported_commits=unreported_commits,
        vig_rate_pct=int(MARKETPLACE_VIG_RATE * 100),
        followup_days=PLATFORM_SOURCED_FOLLOWUP_DAYS,
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
    return redirect(url_for("marketplace", mode="buy_now"))


@app.route("/marketplace/chat", methods=["POST"])
def marketplace_chat():
    payload = request.get_json(silent=True) or {}
    msg = str(payload.get("message", "")).strip()
    return jsonify({"reply": marketplace_assistant_reply(msg)})


def _parse_supplier_inventory_lines(form) -> list[dict]:
    names = form.getlist("product_name")
    categories = form.getlist("product_category")
    quantities = form.getlist("product_quantity_kg")
    coas = form.getlist("product_coa")
    sale_modes = form.getlist("product_sale_mode")
    prices = form.getlist("product_price_per_kg")
    rows: list[dict] = []
    for i, raw_name in enumerate(names):
        name = raw_name.strip()
        if not name:
            continue
        rows.append(
            {
                "ingredient": name,
                "category": (categories[i] if i < len(categories) else "").strip(),
                "quantity_kg": (quantities[i] if i < len(quantities) else "").strip(),
                "coa_document": (coas[i] if i < len(coas) else "").strip(),
                "sale_mode": (sale_modes[i] if i < len(sale_modes) else "").strip(),
                "price_per_kg": (prices[i] if i < len(prices) else "").strip(),
            }
        )
    return rows


def _handle_supplier_inquiry(source: str = "list_inventory") -> object:
    company = request.form.get("company_name", "").strip()
    email = request.form.get("contact_email", "").strip()
    contact_name = request.form.get("contact_name", "").strip()
    phone = request.form.get("phone", "").strip()
    country = request.form.get("country", "").strip()
    region = request.form.get("region", "").strip()
    note = request.form.get("note", "").strip()
    listing_types = request.form.getlist("listing_types")
    documentation = request.form.getlist("documentation")
    sale_preferences = request.form.getlist("sale_preferences")
    inventory_lines = _parse_supplier_inventory_lines(request.form)
    ack = request.form.get("ack_contact") == "yes"
    redirect_to = url_for("marketplace_suppliers") + "#inquiry"
    if not company or not email or not contact_name:
        flash("Company name, contact name, and email are required.", "error")
        return redirect(redirect_to)
    if not listing_types:
        flash("Select at least one product category you plan to list.", "error")
        return redirect(redirect_to)
    if not documentation:
        flash("Select at least one documentation type you can provide.", "error")
        return redirect(redirect_to)
    if not ack:
        flash("Please confirm you understand onboarding requires approval from our team.", "error")
        return redirect(redirect_to)

    inquiry = {
        "id": str(uuid.uuid4()),
        "company_name": company,
        "contact_name": contact_name,
        "contact_email": email,
        "phone": phone,
        "country": country,
        "region": region,
        "note": note,
        "listing_types": listing_types,
        "documentation": documentation,
        "sale_preferences": sale_preferences,
        "inventory_lines": inventory_lines,
        "status": "pending",
        "source": source,
        "submitted_at": datetime.now().isoformat(timespec="seconds"),
    }
    rows = load_supplier_inquiries()
    rows.append(inquiry)
    save_supplier_inquiries(rows)
    sent = send_supplier_inquiry_notice(inquiry)
    flash(
        "Thanks — we've received your inquiry. Someone from our team will reach out by email shortly."
        + ("" if sent else " (We could not send an internal alert email; please also email us directly.)"),
        "success",
    )
    return redirect(redirect_to)


@app.route("/marketplace/supplier-subscribe", methods=["POST"])
def supplier_subscribe():
    return _handle_supplier_inquiry(source="list_inventory")


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
    access_code = get_or_assign_access_code(company, email)
    grant_marketplace_access()
    flash(
        f"Subscription active. Your marketplace access code: {access_code}. "
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
    if et == "checkout.session.completed" and obj is not None:
        raw = obj.to_dict() if hasattr(obj, "to_dict") else (obj if isinstance(obj, dict) else {})
        if isinstance(raw, dict):
            metadata = raw.get("metadata") or {}
            if metadata.get("order_type") == "listing_purchase":
                create_order_from_checkout_session(raw)
    return jsonify({"received": True})


@app.route("/marketplace/checkout/begin", methods=["POST"])
def marketplace_checkout_begin():
    buyer = buyer_login_required()
    if not buyer:
        session["post_login_redirect"] = request.referrer or url_for("marketplace", mode="buy_now")
        return redirect(url_for("marketplace_account_login", role="buyer"))

    listing_id = request.form.get("listing_id", "").strip()
    listings = load_marketplace_listings()
    listing = next((x for x in listings if str(x.get("id")) == listing_id), None)
    if not listing or listing_sale_mode(listing) != "buy_now":
        flash("That listing is not available for direct purchase.", "error")
        return redirect(url_for("marketplace", mode="buy_now"))

    if not STRIPE_BUYER_CHECKOUT_ENABLED or stripe is None:
        flash("Card checkout is not configured yet. Contact support or use Request intro.", "error")
        return redirect(url_for("marketplace", mode="buy_now", listing=listing_id))

    quantity = float(listing.get("quantity_kg") or 0)
    unit_price = float(listing.get("price_per_kg") or 0)
    total_amount = listing_total_amount(listing)
    if total_amount <= 0:
        flash("Listing price is invalid for checkout.", "error")
        return redirect(url_for("marketplace", mode="buy_now"))

    stripe.api_key = STRIPE_SECRET_KEY
    base = request.host_url.rstrip("/")
    unit = str(listing.get("unit") or "kg")
    ingredient = str(listing.get("ingredient") or "Ingredient lot")
    try:
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            customer_email=str(buyer.get("email") or ""),
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": ingredient[:500],
                            "description": (
                                f"{quantity:,.0f} {unit} @ ${unit_price:,.2f}/{unit} — "
                                f"supplier {listing.get('supplier_public_code', '')}"
                            )[:500],
                        },
                        "unit_amount": int(round(total_amount * 100)),
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "order_type": "listing_purchase",
                "listing_id": listing_id,
                "buyer_account_id": str(buyer.get("id") or ""),
                "buyer_email": str(buyer.get("email") or ""),
                "quantity": str(quantity),
                "unit_price": str(unit_price),
                "total_amount": str(total_amount),
            },
            success_url=base + url_for("marketplace_checkout_success") + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=base + url_for("marketplace_checkout_cancel", listing_id=listing_id),
        )
    except Exception as exc:  # pragma: no cover
        flash(f"Could not start checkout: {exc}", "error")
        return redirect(url_for("marketplace", mode="buy_now", listing=listing_id))
    return redirect(str(checkout_session.url), code=303)


@app.route("/marketplace/checkout/success")
def marketplace_checkout_success():
    session_id = request.args.get("session_id", "").strip()
    order = None
    if session_id and STRIPE_BUYER_CHECKOUT_ENABLED and stripe is not None:
        stripe.api_key = STRIPE_SECRET_KEY
        try:
            sess = stripe.checkout.Session.retrieve(session_id)
            raw = sess.to_dict() if hasattr(sess, "to_dict") else dict(sess)
            order = create_order_from_checkout_session(raw)
        except Exception:
            order = next((o for o in load_marketplace_orders() if o.get("stripe_session_id") == session_id), None)
    if not order and session_id:
        order = next((o for o in load_marketplace_orders() if o.get("stripe_session_id") == session_id), None)
    return render_template(
        "marketplace/order_confirmation.html",
        order=order,
        session_id=session_id,
        marketplace_nav_active="marketplace",
    )


@app.route("/marketplace/checkout/cancel")
def marketplace_checkout_cancel():
    listing_id = request.args.get("listing_id", "").strip()
    flash("Checkout canceled. No payment was collected.", "info")
    if listing_id:
        return redirect(url_for("marketplace", mode="buy_now", listing=listing_id))
    return redirect(url_for("marketplace", mode="buy_now"))


@app.route("/marketplace/account/login", methods=["GET", "POST"])
def marketplace_account_login():
    role = (request.args.get("role") or request.form.get("role") or "buyer").strip().lower()
    if role not in ("buyer", "supplier"):
        role = "buyer"
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if role == "supplier":
            account = find_supplier_account_by_email(email)
            if account and check_password_hash(account.get("password_hash", ""), password):
                login_supplier(account)
                flash("Signed in as supplier.", "success")
                dest = session.pop("post_login_redirect", None) or url_for("supplier_account_dashboard")
                return redirect(dest)
        else:
            account = find_buyer_account_by_email(email)
            if account and check_password_hash(account.get("password_hash", ""), password):
                login_buyer(account)
                flash("Signed in as buyer.", "success")
                dest = session.pop("post_login_redirect", None) or url_for("buyer_account_orders")
                return redirect(dest)
        flash("Invalid email or password.", "error")
    return render_template(
        "marketplace/account_login.html",
        role=role,
        marketplace_nav_active="account",
    )


@app.route("/marketplace/account/logout")
def marketplace_account_logout():
    logout_marketplace_accounts()
    flash("Signed out.", "info")
    return redirect(url_for("marketplace"))


@app.route("/marketplace/account/register/buyer", methods=["GET", "POST"])
def marketplace_register_buyer():
    if request.method == "POST":
        company_name = request.form.get("company_name", "").strip()
        contact_name = request.form.get("contact_name", "").strip()
        email = request.form.get("contact_email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        if not company_name or not contact_name or not email or not phone or not password:
            flash("All buyer signup fields are required.", "error")
            return redirect(url_for("marketplace_register_buyer"))
        if find_buyer_account_by_email(email):
            flash("A buyer account with that email already exists. Please sign in.", "error")
            return redirect(url_for("marketplace_account_login", role="buyer"))
        account = {
            "id": str(uuid.uuid4()),
            "company_name": company_name,
            "contact_name": contact_name,
            "email": email,
            "phone": phone,
            "password_hash": generate_password_hash(password),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        rows = load_buyer_accounts()
        rows.append(account)
        save_buyer_accounts(rows)
        login_buyer(account)
        flash("Buyer account created.", "success")
        return redirect(url_for("buyer_account_orders"))
    return render_template("marketplace/account_register_buyer.html", marketplace_nav_active="account")


@app.route("/marketplace/account/register/supplier", methods=["GET", "POST"])
def marketplace_register_supplier():
    if request.method == "POST":
        return _handle_supplier_inquiry(source="account_register")
    return redirect(url_for("marketplace_suppliers") + "#inquiry")


@app.route("/marketplace/account/buyer/orders")
def buyer_account_orders():
    buyer = buyer_login_required()
    if not buyer:
        return redirect(url_for("marketplace_account_login", role="buyer"))
    orders = sorted(
        [o for o in load_marketplace_orders() if str(o.get("buyer_account_id")) == str(buyer.get("id"))],
        key=lambda o: o.get("created_at", ""),
        reverse=True,
    )
    return render_template(
        "marketplace/buyer_orders.html",
        buyer=buyer,
        orders=orders,
        marketplace_nav_active="account",
    )


@app.route("/marketplace/account/supplier")
def supplier_account_dashboard():
    account = supplier_login_required()
    if not account:
        return redirect(url_for("marketplace_account_login", role="supplier"))
    company = str(account.get("company_name") or "")
    email = str(account.get("email") or "")
    listings = [
        x
        for x in load_marketplace_listings()
        if _norm_company(x.get("supplier_company", "")) == _norm_company(company)
        and _norm_email(x.get("supplier_contact_email", "")) == _norm_email(email)
    ]
    listings.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    edit_id = request.args.get("edit", "").strip()
    edit_listing = next((x for x in listings if str(x.get("id")) == edit_id), None) if edit_id else None
    return render_template(
        "marketplace/supplier_dashboard.html",
        account=account,
        listings=listings,
        edit_listing=edit_listing,
        supplier_subscription_active=supplier_subscription_active(company, email),
        supplier_launch_free=SUPPLIER_LAUNCH_FREE,
        marketplace_nav_active="account",
    )


@app.route("/marketplace/account/supplier/listing/save", methods=["POST"])
def supplier_account_save_listing():
    account = supplier_login_required()
    if not account:
        return redirect(url_for("marketplace_account_login", role="supplier"))
    company = str(account.get("company_name") or "")
    email = str(account.get("email") or "")
    if not SUPPLIER_LAUNCH_FREE and not supplier_subscription_active(company, email):
        flash("Your account is not yet cleared to publish listings. Contact our team for help.", "error")
        return redirect(url_for("supplier_account_dashboard"))

    listing_id = request.form.get("listing_id", "").strip()
    listings = load_marketplace_listings()
    existing = next((x for x in listings if str(x.get("id")) == listing_id), None) if listing_id else None
    if existing:
        if (
            _norm_company(existing.get("supplier_company", "")) != _norm_company(company)
            or _norm_email(existing.get("supplier_contact_email", "")) != _norm_email(email)
        ):
            flash("You can only edit your own listings.", "error")
            return redirect(url_for("supplier_account_dashboard"))

    price_per_kg = _num_or_none(request.form.get("price_per_kg", ""))
    quantity_kg = _num_or_none(request.form.get("quantity_kg", ""))
    if not request.form.get("ingredient", "").strip() or price_per_kg is None or quantity_kg is None or not request.form.get("coa_document", "").strip():
        flash("Ingredient, price, quantity, and COA reference are required.", "error")
        return redirect(url_for("supplier_account_dashboard"))

    row = build_listing_row_from_form(request.form, company, email, existing)
    if existing:
        listings = [row if str(x.get("id")) == listing_id else x for x in listings]
    else:
        listings.append(row)
    save_marketplace_listings(listings)
    flash("Listing saved.", "success")
    return redirect(url_for("supplier_account_dashboard"))


@app.route("/marketplace/supplier-rating", methods=["POST"])
def submit_supplier_rating():
    listing_id = request.form.get("listing_id", "").strip()
    buyer_contact_email = request.form.get("buyer_contact_email", "").strip()
    stars_raw = request.form.get("stars", "").strip()
    comment = (request.form.get("comment") or "").strip()[:2000]
    if not listing_id or not buyer_contact_email:
        flash("Listing and buyer email are required to submit a rating.", "error")
        return redirect(url_for("marketplace"))
    try:
        stars = int(stars_raw)
    except ValueError:
        flash("Stars must be a whole number 1–5.", "error")
        return redirect(url_for("marketplace"))
    if stars < 1 or stars > 5:
        flash("Stars must be between 1 and 5.", "error")
        return redirect(url_for("marketplace"))

    commit_lookup = build_commit_lookup()
    if not commit_lookup.get(_commit_key(listing_id, buyer_contact_email)):
        flash("Only buyers who committed on this listing can rate that supplier (identity stays masked until commitment).", "error")
        return redirect(url_for("marketplace"))

    listings = load_marketplace_listings()
    listing = next((x for x in listings if x.get("id") == listing_id), None)
    if not listing:
        flash("Listing not found.", "error")
        return redirect(url_for("marketplace"))

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
    return redirect(url_for("marketplace"))


@app.route("/marketplace/forum/thread", methods=["POST"])
def forum_new_thread():
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    author_company = request.form.get("author_company", "").strip()
    author_email = request.form.get("author_email", "").strip()
    category = request.form.get("category", "General").strip() or "General"
    if not title or not body or not author_company or not author_email:
        flash("Thread title, message, company, and email are required.", "error")
        return redirect(url_for("marketplace_community"))
    threads = load_forum_threads()
    threads.append(
        {
            "id": str(uuid.uuid4()),
            "title": title[:200],
            "body": body[:8000],
            "category": category[:60],
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
    category = request.form.get("category", "Ingredient").strip() or "Ingredient"
    sale_mode = request.form.get("sale_mode", "buy_now").strip().lower()
    if sale_mode not in ("buy_now", "auction"):
        sale_mode = "buy_now"
    if category not in ("Ingredient", "Flavoring", "Packaging"):
        category = "Ingredient"
    if not supplier_company or not supplier_contact_email or not ingredient or price_per_kg is None or quantity_kg is None or not coa_document:
        flash("Supplier company, contact email, ingredient, price, quantity, and COA reference are required for a listing.", "error")
        return redirect(url_for("marketplace_suppliers") + "#inquiry")
    account = current_supplier_account()
    if account:
        flash("Use your supplier dashboard to publish listings.", "info")
        return redirect(url_for("supplier_account_dashboard"))
    flash(
        "Listing inventory requires onboarding with our team. Submit an inquiry on this page or sign in if you already have an account.",
        "error",
    )
    return redirect(url_for("marketplace_suppliers") + "#inquiry")


@app.route("/marketplace/intro/request", methods=["POST"])
def request_marketplace_intro():
    listing_id = request.form.get("listing_id", "").strip()
    buyer_name = request.form.get("buyer_name", "").strip()
    buyer_company = request.form.get("buyer_company", "").strip()
    buyer_contact_email = request.form.get("buyer_contact_email", "").strip()
    buyer_phone = request.form.get("buyer_phone", "").strip()
    note = request.form.get("note", "").strip()
    wants_json = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def respond_error(message: str, status: int = 400):
        if wants_json:
            return jsonify({"ok": False, "error": message}), status
        flash(message, "error")
        return redirect(url_for("marketplace", mode="buy_now"))

    if not listing_id or not buyer_name or not buyer_company or not buyer_contact_email or not buyer_phone:
        return respond_error("Name, company, email, and phone are required.")

    listings = load_marketplace_listings()
    listing = next((item for item in listings if str(item.get("id")) == listing_id), None)
    if not listing or listing_sale_mode(listing) != "buy_now":
        return respond_error("That listing is not available for a direct intro request.")

    commit_row = mark_commit_platform_sourced(
        {
            "id": str(uuid.uuid4()),
            "listing_id": listing_id,
            "ingredient": str(listing.get("ingredient") or ""),
            "supplier_public_code": str(listing.get("supplier_public_code") or ""),
            "buyer_name": buyer_name,
            "buyer_company": buyer_company,
            "buyer_contact_email": buyer_contact_email,
            "buyer_phone": buyer_phone,
            "note": note,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "agreement_accepted": False,
        },
        listing,
    )
    commits = load_marketplace_commits()
    commits.append(commit_row)
    save_marketplace_commits(commits)
    send_intro_request_notice(commit_row)

    success_message = "Thanks — we'll reach out to connect you with the supplier shortly."
    if wants_json:
        return jsonify({"ok": True, "message": success_message})
    flash(success_message, "success")
    return redirect(url_for("marketplace", mode="buy_now"))


@app.route("/marketplace/commit/begin", methods=["POST"])
def commit_marketplace_begin():
    listing_id = request.form.get("listing_id", "").strip()
    buyer_company = request.form.get("buyer_company", "").strip()
    buyer_contact_email = request.form.get("buyer_contact_email", "").strip()
    if not listing_id or not buyer_company or not buyer_contact_email:
        flash("Listing, buyer company, and buyer email are required before the agreement.", "error")
        return redirect(url_for("marketplace"))

    listings = load_marketplace_listings()
    if not any(item.get("id") == listing_id for item in listings):
        flash("Listing not found.", "error")
        return redirect(url_for("marketplace"))

    commits = load_marketplace_commits()
    key = _commit_key(listing_id, buyer_contact_email)
    if any(_commit_key(c.get("listing_id", ""), c.get("buyer_contact_email", "")) == key for c in commits):
        flash("Commitment already recorded. Supplier details are already unlocked for this buyer.", "success")
        session.pop(SESSION_PENDING_COMMIT_KEY, None)
        return redirect(url_for("marketplace"))

    session[SESSION_PENDING_COMMIT_KEY] = {
        "listing_id": listing_id,
        "buyer_company": buyer_company,
        "buyer_contact_email": buyer_contact_email,
    }
    flash("Use Request intro on the listing in Shop now to connect with the supplier.", "info")
    return redirect(url_for("marketplace", mode="buy_now"))


@app.route("/marketplace/commit/confirm", methods=["POST"])
def commit_marketplace_confirm():
    pending = session.get(SESSION_PENDING_COMMIT_KEY)
    if not pending or not pending.get("listing_id"):
        flash("No pending commitment. Start from Buyers → Commit to purchase.", "error")
        return redirect(url_for("marketplace"))

    if request.form.get("accept_terms") != "yes":
        flash("You must accept the introduction terms to submit.", "error")
        return redirect(url_for("marketplace", mode="buy_now"))

    effective_date = request.form.get("effective_date", "").strip()
    signer_name = request.form.get("signer_name", "").strip()
    signer_title = request.form.get("signer_title", "").strip()
    signature = request.form.get("signature", "").strip()
    if not effective_date or not signer_name or not signer_title or not signature:
        flash("Effective date, your name, title, and electronic signature are required.", "error")
        return redirect(url_for("marketplace", mode="buy_now"))

    listing_id = str(pending["listing_id"]).strip()
    buyer_company = str(pending.get("buyer_company") or "").strip()
    buyer_contact_email = str(pending.get("buyer_contact_email") or "").strip()

    listings = load_marketplace_listings()
    listing = next((item for item in listings if str(item.get("id")) == listing_id), None)
    if not listing:
        session.pop(SESSION_PENDING_COMMIT_KEY, None)
        flash("Listing not found.", "error")
        return redirect(url_for("marketplace"))

    commits = load_marketplace_commits()
    key = _commit_key(listing_id, buyer_contact_email)
    if any(_commit_key(c.get("listing_id", ""), c.get("buyer_contact_email", "")) == key for c in commits):
        session.pop(SESSION_PENDING_COMMIT_KEY, None)
        flash("Commitment already recorded. Supplier details are already unlocked for this buyer.", "success")
        return redirect(url_for("marketplace"))

    commit_id = str(uuid.uuid4())
    accepted_at = datetime.now().isoformat(timespec="seconds")
    commit_row = mark_commit_platform_sourced(
        {
            "id": commit_id,
            "listing_id": listing_id,
            "buyer_company": buyer_company,
            "buyer_contact_email": buyer_contact_email,
            "buyer_phone": str(pending.get("buyer_phone") or ""),
            "timestamp": accepted_at,
            "agreement_accepted": True,
            "agreement_version": MARKETPLACE_AGREEMENT_VERSION,
            "agreement_accepted_at": accepted_at,
            "effective_date": effective_date,
            "signer_name": signer_name,
            "signer_title": signer_title,
            "signature": signature,
        },
        listing,
    )
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
    return redirect(url_for("marketplace"))


@app.route("/marketplace/commit/cancel")
def commit_marketplace_cancel():
    session.pop(SESSION_PENDING_COMMIT_KEY, None)
    flash("Agreement flow canceled. No commitment was recorded.", "info")
    return redirect(url_for("marketplace"))


@app.route("/marketplace/alerts", methods=["POST"])
def add_marketplace_alert():
    buyer_company = request.form.get("buyer_company", "").strip()
    buyer_contact_email = request.form.get("buyer_contact_email", "").strip()
    ingredients = _parse_csv_list(request.form.get("ingredient_watchlist", ""))
    if not buyer_company or not buyer_contact_email or not ingredients:
        flash("Buyer company, contact email, and ingredient watchlist are required.", "error")
        return redirect(url_for("marketplace"))
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
    return redirect(url_for("marketplace"))


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


@app.route("/dashboard")
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
