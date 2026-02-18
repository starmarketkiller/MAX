# EA Licensing Server (MT5) - Stripe subscription + 2 seats

## Features
- Stripe subscription 199 EUR/month (Checkout mode subscription)
- License verify endpoint: bind max 2 MT5 accounts (login+server)
- Verify at EA startup and every 6 hours (EA side)
- Grace period 48h if API unreachable (EA side)
- Admin unbind seat endpoint (x-admin-key)
- Audit log in LicenseEvent
- Rate limiting per IP + per license_key

## Setup
1) Copy env:
   cp .env.example .env
   Edit STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, PRICE_ID_PRO_199, ADMIN_API_KEY

2) Start:
   docker compose up --build

3) Seed demo license:
   (in another terminal)
   docker compose exec api npm run seed

It will print a key like: EDL-AB12-CD34-EF56

## Stripe setup
- Create Product: "EA PRO"
- Create Price: 199 EUR / month
- Put PRICE_ID_PRO_199=price_xxx in .env

## Webhooks (local) via Stripe CLI
stripe login
stripe listen --forward-to localhost:8080/api/v1/stripe/webhook
Copy the shown webhook secret into STRIPE_WEBHOOK_SECRET.

Also enable events:
- customer.subscription.created
- customer.subscription.updated
- customer.subscription.deleted
- invoice.paid
- invoice.payment_failed
- checkout.session.completed

## Create Checkout Session
POST /api/v1/checkout/create-session
Body:
{"license_key":"EDL-...."}

Response:
{"url":"https://checkout.stripe.com/..."}
Open url, pay.

Webhook checkout.session.completed will link the subscription to the license (using metadata.license_key).

## Verify license (MT5 EA calls this)
POST /api/v1/license/verify
Body:
{
  "license_key":"EDL-....",
  "account_login":123456,
  "account_server":"Broker-Server",
  "ea_id":"MarketKiller",
  "ea_version":"3.13"
}

## Admin unbind
POST /api/v1/admin/license/unbind
Header: x-admin-key: ADMIN_API_KEY
Body: {"license_key":"EDL-....","seat_index":0}

## Notes
- This server trusts DB fields updated by Stripe webhooks as source-of-truth.
- Put behind HTTPS in production (reverse proxy like Nginx / Cloudflare).
