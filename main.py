from fastapi import FastAPI, Request
from telegram.ext import Application
from telegram import Update
from config.config import get_settings
from contextlib import asynccontextmanager
import logging
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot_application = None
settings = get_settings()

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
    from utils.handlers import setup_handlers
    setup_handlers(bot_application)
    
    await bot_application.initialize()
    await bot_application.start()

    # Setup webhook
    if settings.webhook_url:
        webhook_url = settings.webhook_url
        if not webhook_url.endswith('/webhook'):
            webhook_url = f"{webhook_url.rstrip('/')}/webhook"
        
        logger.info(f"Setting webhook to: {webhook_url}")
        await bot_application.bot.set_webhook(url=webhook_url)
        logger.info("✅ Webhook set")

    else:
        logger.warning("No webhook URL provided")
    
    logger.info("🎉 Supercat started")

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

@app.post('/webhook')
async def webhook(request: Request):
    """Handle Telegram webhook updates"""
    if not bot_application:
        logger.error("Bot not initialized!")
        return {'error': 'Bot not initialized'}, 500
    
    try:
        data = await request.json()
        update_id = data.get('update_id', 'unknown')
        logger.info(f"📨 Received update: {update_id}")
        
        await bot_application.process_update(
            Update.de_json(data, bot_application.bot)
        )
        
        return {'ok': True}
        
    except Exception as e:
        logger.error(f"❌ Error processing update: {e}")
        return {'error': str(e)}, 500

@app.get('/webhook-info')
async def webhook_info():
    """Get current webhook status"""
    if not bot_application:
        return {'error': 'Bot not initialized'}
    
    try:
        info = await bot_application.bot.get_webhook_info()
        return {
            'url': info.url,
            'has_custom_certificate': info.has_custom_certificate,
            'pending_update_count': info.pending_update_count,
            'last_error_date': info.last_error_date,
            'last_error_message': info.last_error_message,
            'max_connections': info.max_connections
        }
    except Exception as e:
        return {'error': str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)