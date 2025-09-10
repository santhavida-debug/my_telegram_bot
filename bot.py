# bot.py
import os
import logging
from dotenv import load_dotenv

# Telegram
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# OpenAI
import openai
hf_generator = None  # Hugging Face lazy load

# Carga .env local (Render usará env vars en dashboard)
load_dotenv()

# Variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # ejemplo: https://mi-app.onrender.com
PORT = int(os.getenv("PORT", "8443"))

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Inicializar OpenAI si está configurado
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola — bot activo. Escribe y responderé usando OpenAI (o HF si falla)."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - inicia\n/help - ayuda")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text or ""
    if not user_msg.strip():
        await update.message.reply_text("Envía texto para que te responda.")
        return

    # Intentamos OpenAI primero
    if OPENAI_API_KEY:
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": user_msg}],
                max_tokens=300,
                temperature=0.7,
            )
            content = resp["choices"][0]["message"]["content"].strip()
            await update.message.reply_text(content)
            return
        except Exception as e:
            logger.error("OpenAI error: %s", e)

    # Fallback Hugging Face
    global hf_generator
    try:
        if hf_generator is None:
            from transformers import pipeline
            hf_generator = pipeline(
                "text-generation", model="gpt2", use_auth_token=HF_TOKEN
            )
        out = hf_generator(user_msg, max_length=150, do_sample=True)
        text = out[0].get("generated_text", "")
        await update.message.reply_text(text)
    except Exception as e:
        logger.error("HF error: %s", e)
        await update.message.reply_text(
            "Lo siento, no pude generar una respuesta (OpenAI/HF fallaron)."
        )

def main():
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN no encontrado en variables de entorno.")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Webhook
    if WEBHOOK_URL:
        webhook_path = f"/webhook/{TELEGRAM_TOKEN}"
        full_url = WEBHOOK_URL.rstrip("/") + webhook_path
        logger.info("Iniciando webhook en %s:%s -> %s", "0.0.0.0", PORT, full_url)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=full_url,
            path=webhook_path,
        )
    else:
        logger.info("WEBHOOK_URL no configurada: iniciando polling local.")
        app.run_polling()

if __name__ == "__main__":
    main()

