# Telegram Bot

## Setup
- Create bot via BotFather
- Put `BOT_TOKEN` in `server-api/.env`
- Set `WEBAPP_URL` env to your tunnel URL + `/webapp`

## Run standalone
npm install
npm run dev

## In Docker Compose
Service `telegram-bot` uses `BOT_TOKEN` and `WEBAPP_URL` env vars.
