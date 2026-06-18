"""Optional SMTP notification when a buyer signs the marketplace agreement."""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

log = logging.getLogger(__name__)

# Used when AGREEMENT_NOTIFY_EMAIL is unset (override in env for other deploys).
_DEFAULT_AGREEMENT_NOTIFY = "max@sportsnutrition.com"


def _smtp_settings() -> dict[str, Any]:
    raw_to = (os.environ.get("AGREEMENT_NOTIFY_EMAIL") or "").strip()
    if not raw_to:
        raw_to = _DEFAULT_AGREEMENT_NOTIFY
    return {
        "host": os.environ.get("SMTP_HOST", "").strip(),
        "port": int(os.environ.get("SMTP_PORT", "587") or 587),
        "user": os.environ.get("SMTP_USER", "").strip(),
        "password": os.environ.get("SMTP_PASSWORD", "").strip(),
        "from_addr": os.environ.get("MAIL_FROM", os.environ.get("SMTP_USER", "")).strip(),
        "to": [x.strip() for x in raw_to.split(",") if x.strip()],
        "use_tls": os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes"),
    }


def send_agreement_signed_notice(
    submission: dict[str, Any],
    listing: dict[str, Any] | None,
) -> bool:
    """
    Email platform owner when an agreement is signed.
    Returns True if an email was sent, False if skipped or failed (check logs).
    """
    cfg = _smtp_settings()
    if not cfg["host"]:
        log.info(
            "Agreement email skipped: set SMTP_HOST (and SMTP_USER / SMTP_PASSWORD / MAIL_FROM) "
            "so messages can be delivered to %s.",
            ", ".join(cfg["to"]),
        )
        return False
    if not cfg["from_addr"]:
        log.warning("Agreement email skipped: set MAIL_FROM or SMTP_USER.")
        return False

    subj = f"[Marketplace] Agreement signed — {submission.get('buyer_company', '')}"
    lines = [
        "A buyer submitted a signed brokered transaction agreement.",
        "",
        "--- Submission ---",
        f"id: {submission.get('id')}",
        f"submitted_at: {submission.get('submitted_at')}",
        f"listing_id: {submission.get('listing_id')}",
        f"buyer_company: {submission.get('buyer_company')}",
        f"buyer_contact_email: {submission.get('buyer_contact_email')}",
        f"agreement_version: {submission.get('agreement_version')}",
        f"effective_date: {submission.get('effective_date')}",
        f"signer_name: {submission.get('signer_name')}",
        f"signer_title: {submission.get('signer_title')}",
        f"signature (typed): {submission.get('signature')}",
        f"status: {submission.get('status')}",
        f"commit_id: {submission.get('commit_id')}",
        "",
        "--- Listing (if matched) ---",
    ]
    if listing:
        lines.extend(
            [
                f"ingredient: {listing.get('ingredient')}",
                f"supplier_company: {listing.get('supplier_company')}",
                f"supplier_contact_email: {listing.get('supplier_contact_email')}",
                f"supplier_public_code: {listing.get('supplier_public_code')}",
            ]
        )
    else:
        lines.append("(listing not found for listing_id)")
    body = "\n".join(lines)

    msg = EmailMessage()
    msg["Subject"] = subj[:998]
    msg["From"] = cfg["from_addr"]
    msg["To"] = ", ".join(cfg["to"])
    msg.set_content(body)

    try:
        if cfg["use_tls"]:
            context = ssl.create_default_context()
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                if cfg["user"] and cfg["password"]:
                    smtp.login(cfg["user"], cfg["password"])
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as smtp:
                if cfg["user"] and cfg["password"]:
                    smtp.login(cfg["user"], cfg["password"])
                smtp.send_message(msg)
        log.info("Agreement notification email sent to %s", cfg["to"])
        return True
    except Exception:
        log.exception("Failed to send agreement notification email")
        return False


def send_intro_request_notice(commit: dict[str, Any]) -> bool:
    """
    Notify platform owner when a buyer requests an intro on a shop-now listing.
    Only includes supplier_public_code — never supplier identity fields.
    """
    cfg = _smtp_settings()
    lines = [
        "A buyer requested an introduction on a shop-now listing.",
        "",
        "--- Listing ---",
        f"ingredient: {commit.get('ingredient', '')}",
        f"supplier_public_code: {commit.get('supplier_public_code', '')}",
        f"listing_id: {commit.get('listing_id', '')}",
        "",
        "--- Buyer ---",
        f"buyer_name: {commit.get('buyer_name', '')}",
        f"buyer_company: {commit.get('buyer_company', '')}",
        f"buyer_contact_email: {commit.get('buyer_contact_email', '')}",
        f"buyer_phone: {commit.get('buyer_phone', '')}",
        f"note: {commit.get('note', '')}",
        "",
        f"timestamp: {commit.get('timestamp', '')}",
        f"commit_id: {commit.get('id', '')}",
    ]
    body = "\n".join(lines)
    log.info("NEW MARKETPLACE INTRO REQUEST\n%s", body)

    if not cfg["host"]:
        log.info(
            "Intro request email skipped: set SMTP_HOST to deliver to %s.",
            ", ".join(cfg["to"]),
        )
        return False
    if not cfg["from_addr"]:
        log.warning("Intro request email skipped: set MAIL_FROM or SMTP_USER.")
        return False

    subj = f"[Marketplace] Intro request — {commit.get('buyer_company', '')} / {commit.get('ingredient', '')}"
    msg = EmailMessage()
    msg["Subject"] = subj[:998]
    msg["From"] = cfg["from_addr"]
    msg["To"] = ", ".join(cfg["to"])
    msg.set_content(body)

    try:
        if cfg["use_tls"]:
            context = ssl.create_default_context()
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                if cfg["user"] and cfg["password"]:
                    smtp.login(cfg["user"], cfg["password"])
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as smtp:
                if cfg["user"] and cfg["password"]:
                    smtp.login(cfg["user"], cfg["password"])
                smtp.send_message(msg)
        log.info("Intro request notification email sent to %s", cfg["to"])
        return True
    except Exception:
        log.exception("Failed to send intro request notification email")
        return False


def send_supplier_inquiry_notice(inquiry: dict[str, Any]) -> bool:
    """Notify platform team when a supplier requests to list inventory."""
    raw_to = (
        os.environ.get("SUPPLIER_INQUIRY_NOTIFY_EMAIL", "").strip()
        or os.environ.get("SUPPLIER_ONBOARDING_EMAIL", "").strip()
        or os.environ.get("AGREEMENT_NOTIFY_EMAIL", "").strip()
    )
    if not raw_to:
        raw_to = _DEFAULT_AGREEMENT_NOTIFY
    cfg = _smtp_settings()
    cfg["to"] = [x.strip() for x in raw_to.split(",") if x.strip()]

    lines = [
        "A supplier submitted a request to list inventory on the marketplace.",
        "",
        "--- Inquiry ---",
        f"id: {inquiry.get('id')}",
        f"submitted_at: {inquiry.get('submitted_at')}",
        f"source: {inquiry.get('source')}",
        f"company_name: {inquiry.get('company_name')}",
        f"contact_name: {inquiry.get('contact_name')}",
        f"contact_email: {inquiry.get('contact_email')}",
        f"phone: {inquiry.get('phone')}",
        f"country: {inquiry.get('country')}",
        f"region: {inquiry.get('region')}",
        f"listing_types: {', '.join(inquiry.get('listing_types') or [])}",
        f"documentation: {', '.join(inquiry.get('documentation') or [])}",
        f"sale_preferences: {', '.join(inquiry.get('sale_preferences') or [])}",
        f"note: {inquiry.get('note')}",
        f"status: {inquiry.get('status')}",
    ]
    inventory_lines = inquiry.get("inventory_lines") or []
    if inventory_lines:
        lines.extend(["", "--- Inventory lines ---"])
        for i, row in enumerate(inventory_lines, start=1):
            lines.append(
                f"{i}. {row.get('ingredient')} | {row.get('category')} | "
                f"{row.get('quantity_kg')} kg | COA: {row.get('coa_document') or '—'} | "
                f"{row.get('sale_mode') or '—'} | ${row.get('price_per_kg') or '—'}/kg"
            )
    else:
        lines.extend(["", "--- Inventory lines ---", "(none entered — see note)"])
    body = "\n".join(lines)
    log.info("NEW SUPPLIER INQUIRY\n%s", body)

    if not cfg["host"]:
        log.info(
            "Supplier inquiry email skipped: set SMTP_HOST to deliver to %s.",
            ", ".join(cfg["to"]),
        )
        return False
    if not cfg["from_addr"]:
        log.warning("Supplier inquiry email skipped: set MAIL_FROM or SMTP_USER.")
        return False

    subj = f"[Marketplace] Supplier inquiry — {inquiry.get('company_name', '')}"
    msg = EmailMessage()
    msg["Subject"] = subj[:998]
    msg["From"] = cfg["from_addr"]
    msg["To"] = ", ".join(cfg["to"])
    msg.set_content(body)

    try:
        if cfg["use_tls"]:
            context = ssl.create_default_context()
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                if cfg["user"] and cfg["password"]:
                    smtp.login(cfg["user"], cfg["password"])
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as smtp:
                if cfg["user"] and cfg["password"]:
                    smtp.login(cfg["user"], cfg["password"])
                smtp.send_message(msg)
        log.info("Supplier inquiry notification email sent to %s", cfg["to"])
        return True
    except Exception:
        log.exception("Failed to send supplier inquiry notification email")
        return False
