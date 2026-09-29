# Jarvis Telegram Production Activation V1

This runbook activates the already deployed, channel-agnostic Jarvis Access Layer. It does not deploy code and does not bypass the NEXUS Orchestrator.

## Required Render secrets

Configure these only in the `nexus-backend` Render environment:

- `TELEGRAM_BOT_TOKEN`: token issued by BotFather.
- `JARVIS_TELEGRAM_WEBHOOK_SECRET`: high-entropy random secret used by Telegram's webhook header.
- `JARVIS_TELEGRAM_ALLOWED_USER_IDS`: comma-separated Telegram numeric user IDs.
- `NEXUS_PUBLIC_URL=https://nexus-backend-8o4y.onrender.com`

Never place these values in the repository, Vault, fixtures, command history, or logs. A partial configuration is reported as `PARTIAL`; the webhook fails closed when the adapter token or allowlist is absent.

## Pre-activation verification

After an explicitly approved deploy/restart, verify:

```text
GET /api/health
GET /api/ready
GET /api/version
GET /api/jarvis/telegram/status   (authenticated)
```

The version SHA must match the approved commit. Telegram status must report `configuration_state=READY`, `webhook_ready=true`, and the expected allowlist count. It never returns tokens, the webhook secret, or user IDs.

## Register and verify webhook

Run in a secure environment containing the four variables above:

```bash
python server/jarvis_v1/configure_telegram_webhook.py set
python server/jarvis_v1/configure_telegram_webhook.py verify
```

The target is exactly:

```text
https://nexus-backend-8o4y.onrender.com/api/jarvis/telegram/webhook
```

`set` is idempotent. `verify` uses Telegram `getWebhookInfo` and verifies the URL. Telegram does not return the configured secret, so the script truthfully reports only that the local secret is configured.

## Real acceptance sequence

1. From an allowlisted private chat send `Jarvis, cosa è successo oggi?`; confirm an answer, `premium_calls=0`, and no task creation.
2. Send the same webhook update twice in an isolated test; confirm the second result is `DUPLICATE` and creates no application action.
3. Send `Jarvis, crea una task per analizzare un Review Kit QR/NFC per attività locali.`; confirm a real task/queue/ledger entry. This remains `business_analysis` and may require review.
4. Send `A che punto è?`; confirm it resolves the preceding conversation task and creates no new task.
5. For a real `WAITING_APPROVAL` task, use `APPROVE`, `REJECT`, and `DETAILS`; confirm valid Orchestrator state transitions and audit events.
6. Test a non-allowlisted user and an invalid webhook secret; confirm 403 and 401 respectively, with no internal information returned.

## Known V1 limitations

- Conversation-to-task context is process-local. It survives normal messages in the same running instance but not a restart; callers can still use explicit task IDs.
- Telegram activation and phone acceptance require the production secrets and an approved restart/deploy; they cannot be proven by repository tests alone.
- Provider availability is projected from the existing registry. Jarvis never claims Claude, Codex, or another premium provider is connected unless the registry reports it.
- Low-value notifications are aggregated by the V1 notification policy; real-time voice, WhatsApp, and PWA clients remain out of scope.
