const TelegramBot = require('node-telegram-bot-api');

const token = '8729285214:AAFKY-GMUDgCT9I7L8LVcevGKXqcWpEHMk4';
const bot = new TelegramBot(token, { polling: true });

bot.on('message', (msg) => {
  bot.sendMessage(msg.chat.id, 'Hello! Bot is running 🚀');
});
