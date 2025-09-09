import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# Tu token del bot de Telegram
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")  # Lo guardaremos como variable de entorno
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")        # Tu URL pública para Render o cualquier hosting

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu bot libre y en la nube.")

# Responder mensajes de texto
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text(f"Recibido: {text}")

if __name__ == "__main__":
    # Creamos la aplicación del bot
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Comandos y handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Activamos el webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),  # Render o Heroku usa variable PORT
        webhook_url=f"{WEBHOOK_URL}/webhook/{TELEGRAM_TOKEN}"
    )
