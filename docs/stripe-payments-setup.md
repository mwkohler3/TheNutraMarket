# Stripe payments setup — TheNutraMarket

Payments are already built into the app. Configure Stripe + Railway to turn them on.

## How it works

1. Buyer clicks **Inquire** on a Shop now listing
2. Fills name, company, email, phone, quantity (kg)
3. App creates a Stripe Checkout session (`POST /marketplace/checkout/begin`)
4. Buyer pays on Stripe’s hosted checkout page
5. Stripe webhook fires → order saved to `data/marketplace_orders.json`
6. You get an email alert (if SMTP is configured)

**National Chemical listings** use “pricing on request.” Buyers pay a **platform commitment fee** (default **$250**, set via `PLATFORM_COMMITMENT_FEE_USD`) so deals stay on-platform before final pricing.

---

## 1. Stripe account

1. [dashboard.stripe.com/register](https://dashboard.stripe.com/register)
2. Complete business verification for live payments
3. Use **Test mode** while setting up

---

## 2. API keys

Stripe Dashboard → **Developers → API keys**

| Variable | Value |
|----------|--------|
| `STRIPE_SECRET_KEY` | `sk_test_…` or `sk_live_…` (server only — Railway) |
| `STRIPE_PUBLISHABLE_KEY` | `pk_test_…` or `pk_live_…` (optional today) |

---

## 3. Railway environment variables

Railway project → **web** service → **Variables**:

```bash
STRIPE_SECRET_KEY=sk_test_xxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxx
PLATFORM_COMMITMENT_FEE_USD=250
```

**Email alerts when someone pays** (optional but recommended):

```bash
AGREEMENT_NOTIFY_EMAIL=max@sportsnutrition.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
MAIL_FROM=your-email@gmail.com
SMTP_USE_TLS=true
```

Redeploy after saving.

---

## 4. Webhook (required)

Without this, Stripe can charge the card but your app may not record the order.

1. Stripe Dashboard → **Developers → Webhooks → Add endpoint**
2. **URL:** `https://thenutramarket.up.railway.app/marketplace/stripe-webhook`  
   (or your custom domain when DNS is live)
3. **Event:** `checkout.session.completed`
4. Copy the **Signing secret** (`whsec_…`) → set as `STRIPE_WEBHOOK_SECRET` on Railway

---

## 5. Test

1. Test card: `4242 4242 4242 4242`, any future expiry, any CVC
2. Site → **Shop now** → **Inquire** → complete checkout
3. Confirm:
   - Success page at `/marketplace/checkout/success`
   - Payment in Stripe Dashboard → **Payments**
   - Webhook event succeeded under **Developers → Webhooks**
   - Order in `data/marketplace_orders.json` (on Railway volume / deploy)

---

## 6. Go live

1. Stripe → **Live mode**
2. Replace test keys with live keys on Railway
3. Create a **new live webhook** (same URL + event)
4. Update `STRIPE_WEBHOOK_SECRET` with the live signing secret

---

## Checklist

- [ ] `STRIPE_SECRET_KEY` on Railway
- [ ] Webhook endpoint `/marketplace/stripe-webhook` + `checkout.session.completed`
- [ ] `STRIPE_WEBHOOK_SECRET` on Railway
- [ ] SMTP vars for payment emails
- [ ] Test payment with `4242…` card

---

## Code reference

| Piece | Location |
|-------|----------|
| Checkout start | `app.py` → `marketplace_checkout_begin()` |
| Webhook | `app.py` → `stripe_webhook()` |
| Order creation | `app.py` → `create_order_from_checkout_session()` |
| Payment email | `agreement_mail.py` → `send_marketplace_order_notice()` |
| Orders data | `data/marketplace_orders.json` |

---

## Not built yet (future)

- **Stripe Connect** — pay suppliers (e.g. National Chemical) minus platform fee
- **Full lot checkout** — set `price_per_kg` on listings instead of `price_on_request`
- **Balance invoices** — Stripe Invoices after you quote final price
