# Telegram Bot (Telegraf)

Bot Telegram con Telegraf che espone i comandi `/start`, `/menu`, `/vip`, `/support` e usa una tastiera inline per aprire app, area VIP e supporto.

## Requisiti

- Node.js 18+
- Un bot Telegram creato con @BotFather

## Configurazione

Crea un file `.env` (oppure imposta le variabili d'ambiente) con:

```bash
BOT_TOKEN=your-telegram-bot-token
WEBAPP_URL=https://example.com/webapp
VIP_URL=https://example.com/vip
SUPPORT_URL=https://example.com/support
```

## Avvio locale

```bash
npm install
npm start
```

## Import to Replit + Secrets + Run

1. Importa questo repository in Replit (Import from GitHub).
2. Vai su **Tools > Secrets** e aggiungi:
   - `BOT_TOKEN`
   - `WEBAPP_URL`
   - `VIP_URL`
   - `SUPPORT_URL`
3. Clicca **Run** per avviare il bot in polling.

## Comandi

- `/start` → onboarding + tastiera inline
- `/menu` → mostra la tastiera inline
- `/vip` → link diretto area VIP
- `/support` → link diretto supporto
