require('dotenv').config();

const { Telegraf, Markup } = require('telegraf');

const { BOT_TOKEN, WEBAPP_URL, VIP_URL, SUPPORT_URL } = process.env;

if (!BOT_TOKEN || !WEBAPP_URL || !VIP_URL || !SUPPORT_URL) {
  console.error('Missing required environment variables.');
  console.error('Required: BOT_TOKEN, WEBAPP_URL, VIP_URL, SUPPORT_URL');
  process.exit(1);
}

const bot = new Telegraf(BOT_TOKEN);

const onboardingText =
  'Benvenuto!\n\n' +
  'Da qui puoi aprire l\'app, accedere all\'area VIP o contattare il supporto.';

const mainKeyboard = Markup.inlineKeyboard([
  [Markup.button.webApp('🔓 Apri App', WEBAPP_URL)],
  [Markup.button.url('⭐ Area VIP', VIP_URL)],
  [Markup.button.url('📩 Supporto', SUPPORT_URL)],
]);

const sendMenu = async (ctx) => {
  try {
    await ctx.reply(onboardingText, mainKeyboard);
  } catch (error) {
    console.error('Failed to send menu:', error);
  }
};

bot.start(sendMenu);
bot.command('menu', sendMenu);
bot.command('vip', async (ctx) => {
  try {
    await ctx.reply('Accedi all\'area VIP:', Markup.inlineKeyboard([
      [Markup.button.url('⭐ Area VIP', VIP_URL)],
    ]));
  } catch (error) {
    console.error('Failed to send VIP link:', error);
  }
});

bot.command('support', async (ctx) => {
  try {
    await ctx.reply('Contatta il supporto:', Markup.inlineKeyboard([
      [Markup.button.url('📩 Supporto', SUPPORT_URL)],
    ]));
  } catch (error) {
    console.error('Failed to send support link:', error);
  }
});

bot.catch((error, ctx) => {
  console.error('Bot error', error, 'for update', ctx.update);
});

process.on('unhandledRejection', (reason) => {
  console.error('Unhandled promise rejection:', reason);
});

process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
});

bot.launch({
  polling: true,
});

console.log('Bot avviato in polling.');

process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
