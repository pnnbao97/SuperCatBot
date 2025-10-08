"""
Constants for SuperCat Bot application.
"""
from typing import Final

# API Endpoints
class Endpoints:
    HEALTH_CHECK: Final[str] = "/"
    WEBHOOK: Final[str] = "/webhook"
    WEBHOOK_INFO: Final[str] = "/webhook-info"

# Webhook Configuration
class WebhookConfig:
    DEFAULT_URL: Final[str] = "https://supercat.onrender.com/webhook"
    PATH_SUFFIX: Final[str] = "/webhook"

# Bot Messages
class BotMessages:
    WELCOME: Final[str] = (
        "🐱 Welcome to SuperCat Bot!\n\n"
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show help message"
    )
    
    HELP: Final[str] = (
        "Need help? Here's what I can do:\n\n"
        "• Send me any message\n"
        "• Use /start to begin\n"
        "• Use /help to see this message"
    )
    
    ECHO_PREFIX: Final[str] = "You said: "

# Log Messages
class LogMessages:
    STARTING_BOT: Final[str] = "Starting SuperCat Bot..."
    BOT_STARTED: Final[str] = "SuperCat Bot started successfully"
    STOPPING_BOT: Final[str] = "Stopping SuperCat Bot..."
    BOT_STOPPED: Final[str] = "SuperCat Bot stopped"
    WEBHOOK_SET: Final[str] = "Webhook configured successfully"
    WEBHOOK_URL_MISSING: Final[str] = "No webhook URL provided"
    UPDATE_RECEIVED: Final[str] = "Received update"
    UPDATE_PROCESSED: Final[str] = "Update processed successfully"
    HANDLERS_SETUP: Final[str] = "Bot handlers setup complete"

# Error Messages
class ErrorMessages:
    BOT_NOT_INITIALIZED: Final[str] = "Bot not initialized"
    INVALID_JSON: Final[str] = "Invalid JSON payload"
    WEBHOOK_ERROR: Final[str] = "Webhook processing error"
    UNEXPECTED_ERROR: Final[str] = "Unexpected error occurred"

# HTTP Status Codes
class StatusCodes:
    OK: Final[int] = 200
    BAD_REQUEST: Final[int] = 400
    INTERNAL_SERVER_ERROR: Final[int] = 500
