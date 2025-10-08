from fastapi import FastAPI
from telegram.ext import Application
from config.config import settings
from contextlib import asynccontextmanager
import logging
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot_application = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan for the FastAPI application.
    """
    global bot_application

    # Start the bot
    logger.info("Starting Supercat...")

    bot_application = Application.builder().token(settings.telegram_bot_token.get_secret_value()).build()

    # Setup handlers
    from handlers import setup_handlers
    setup_handlers(bot_application)
    
    await bot_application.initialize()
    await bot_application.start()

    # Setup webhook
    if settings.webhook_url:
        logger.info("Setting up webhook")
        await bot_application.bot.set_webhook(settings.webhook_url)
        logger.info("Webhook set")
    else:
        logger.warning("No webhook URL provided")
    
    logger.info("Supercat started")

    yield

    # Stop the bot
    logger.info("Stopping Supercat...")
    await bot_application.stop()
    await bot_application.shutdown()
    logger.info("Supercat stopped")

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def health_check():
    return {"message": "OK"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)