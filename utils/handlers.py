"""
Bot handlers for SuperCat Bot.
"""
from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
import logging
from utils.constants import BotMessages, LogMessages
from utils.exceptions import HandlerError

logger = logging.getLogger(__name__)


class BotHandlers:
    """Bot command and message handlers."""
    
    @staticmethod
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        try:
            await update.message.reply_text(BotMessages.WELCOME)
            logger.info(f"Start command executed by user {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            raise HandlerError(f"Failed to execute start command: {e}")

    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        try:
            await update.message.reply_text(BotMessages.HELP)
            logger.info(f"Help command executed by user {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            raise HandlerError(f"Failed to execute help command: {e}")

    @staticmethod
    async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Echo user messages."""
        try:
            text = update.message.text
            user_id = update.effective_user.id
            username = update.effective_user.username or "Unknown"
            
            logger.info(f"Echo message from user {user_id} (@{username}): {text}")
            
            response = f"{BotMessages.ECHO_PREFIX}{text}"
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error in echo message: {e}")
            raise HandlerError(f"Failed to echo message: {e}")

    @staticmethod
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors."""
        error = context.error
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        
        logger.error(f"Error for user {user_id}: {error}")
        
        # Try to send error message to user
        try:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "Sorry, an error occurred while processing your request. Please try again."
                )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")


def setup_handlers(application) -> None:
    """Setup all bot handlers."""
    try:
        # Command handlers
        application.add_handler(CommandHandler("start", BotHandlers.start_command))
        application.add_handler(CommandHandler("help", BotHandlers.help_command))
        
        # Message handlers
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, BotHandlers.echo_message)
        )
        
        # Error handler
        application.add_error_handler(BotHandlers.error_handler)
        
        logger.info(LogMessages.HANDLERS_SETUP)
        
    except Exception as e:
        logger.error(f"Failed to setup handlers: {e}")
        raise HandlerError(f"Handler setup failed: {e}")