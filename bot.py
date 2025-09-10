# bot.py
import os
import logging
from dotenv import load_dotenv

# Telegram
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,  # <-- CORRECCIÓN AQUÍ
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# OpenAI
import openai
# Hugging Face lazy (no forzamos descarga hasta que haga falta)
hf_generator = None

# Carga .env si existe (local). En Render preferible usar env vars en dashboard.
load_dotenv()

# Variables de entorno (configúralas en Render dashboard)
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

# Inicializar OpenAI si hay clave
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

    # Intentamos OpenAI primero (si está configurada)
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

    # Si OpenAI falla o no está, fallback a HuggingFace (carga perezosa)
    global hf_generator
    try:
        if hf_generator is None:
            from transformers import pipeline
            # CUIDADO: model gpt2 es pequeño; cambia por otro si lo prefieres.
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

def build_and_run():
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN no encontrado en variables de entorno.")

    # Construimos la app usando la API recomendada
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Si tenemos WEBHOOK_URL preferimos webhook (mejor para Render Web Service).
    if WEBHOOK_URL:
        webhook_path = f"/webhook/{TELEGRAM_TOKEN}"
        full_url = WEBHOOK_URL.rstrip("/") + webhook_path
        logger.info("Iniciando webhook en %s:%s -> %s", "0.0.0.0", PORT, full_url)
        # run_webhook inicia un server aiohttp internamente y Telegram enviará updates
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=full_url,
            path=webhook_path,
        )
    else:
        # Si no hay webhook URL, usamos polling (útil para testing local o workers)
        logger.info("WEBHOOK_URL no configurada: iniciando polling (local/test).")
        app.run_polling()

if __name__ == "__main__":
    build_and_run()
