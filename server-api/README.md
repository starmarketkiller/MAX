# EA Licensing Server API + Telegram WebApp auth

## Features
- Stripe-ready licensing backend (optional in local dev)
- Max 2 seats per license (bind by MT5 login+server)
- Verify endpoint for EA with bind-on-first-use
- Admin unbind endpoint
- WebApp read-only status endpoint protected by Telegram initData signature
- DEV bypass for initData via `DEV_BYPASS_INITDATA=true`

## Setup
1. Copy env:
   ```bash
   cp .env.example .env
   ```
2. Edit secrets (`ADMIN_API_KEY`, `BOT_TOKEN`, Stripe vars optional for now).
3. Start stack from repo root:
   ```bash
   docker compose up --build
   ```
4. Seed a license:
   ```bash
   docker compose exec server-api npm run seed
   ```

## ngrok local tunnel
```bash
ngrok http 8080
```
Use the HTTPS URL as:
- Telegram WebApp URL: `https://xxxx.ngrok-free.app/webapp`
- MT5 `InpLicenseApiBase`: `https://xxxx.ngrok-free.app`

## Curl tests
Verify bind:
```bash
curl -s http://localhost:8080/api/v1/license/verify \
  -H 'Content-Type: application/json' \
  -d '{"license_key":"EDL-AB12-CD34-EF56","account_login":123456,"account_server":"Broker-Server","ea_id":"MarketKiller","ea_version":"3.13"}'
```

Admin unbind:
```bash
curl -s http://localhost:8080/api/v1/admin/license/unbind \
  -H 'Content-Type: application/json' \
  -H 'x-admin-key: change_me_super_secret' \
  -d '{"license_key":"EDL-AB12-CD34-EF56","seat_index":0}'
```

Create checkout (optional now):
```bash
curl -s http://localhost:8080/api/v1/checkout/create-session \
  -H 'Content-Type: application/json' \
  -d '{"license_key":"EDL-AB12-CD34-EF56"}'
```
