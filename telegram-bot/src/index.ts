import dotenv from "dotenv";
import { Bot, Keyboard } from "grammy";

dotenv.config({ path: process.env.BOT_ENV_FILE || "../server-api/.env" });

const token = process.env.BOT_TOKEN;
const webAppUrl = process.env.WEBAPP_URL || "http://localhost:8080/webapp";

if (!token) throw new Error("Missing BOT_TOKEN");

const bot = new Bot(token);

bot.command("start", async (ctx) => {
  const kb = new Keyboard().text("🚀 Apri App", { web_app: { url: webAppUrl } }).resized();
  await ctx.reply("Benvenuto nel pannello licenze EA.", { reply_markup: kb });
});

bot.command("menu", async (ctx) => {
  const kb = new Keyboard().text("🚀 Apri App", { web_app: { url: webAppUrl } }).resized();
  await ctx.reply("Menu pronto.", { reply_markup: kb });
});

bot.catch((err) => {
  console.error("Bot error", err.error);
});

bot.start();
console.log("Telegram bot started");
