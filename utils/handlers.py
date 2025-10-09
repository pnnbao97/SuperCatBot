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
from agents.orchestration import OrchestratorAgent

logger = logging.getLogger(__name__)

orchestration_agent = OrchestratorAgent()

class BotHandlers:
    """Bot command and message handlers."""

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
    async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages with status updates."""
        try:
            message = update.message.text
            
            # Gửi tin nhắn placeholder ban đầu
            status_message = await update.message.reply_text("⏳ Đang xử lý...")
            
            # Định nghĩa callback để update status
            # async def update_status(status: str):
            #     try:
            #         if status == "searching":
            #             await status_message.edit_text("🔍 Đang tìm kiếm thông tin...")
            #         elif status == "answering":
            #             await status_message.edit_text("💭 Đang tổng hợp câu trả lời...")
            #     except Exception as e:
            #         logger.warning(f"Failed to update status: {e}")
            
            # Generate answer với callback
            response = await orchestration_agent.generate_answer(message)
            
            # Edit tin nhắn cuối cùng thành câu trả lời
            try:
                await status_message.edit_text(response)
            except Exception as e:
                # Nếu edit thất bại (tin nhắn quá cũ), gửi tin nhắn mới
                logger.warning(f"Failed to edit message, sending new one: {e}")
                await update.message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Error in text message: {e}")
            try:
                await update.message.reply_text("❌ Có lỗi xảy ra khi xử lý tin nhắn.")
            except:
                pass
            raise HandlerError(f"Failed to handle text message: {e}")
    
    @staticmethod
    async def photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle photo messages."""
        try:
            photo_file_id = update.message.photo[-1].file_id
            caption = update.message.caption
            chat_id = update.message.chat_id

            # Gửi lại ảnh
            await context.bot.send_photo(chat_id=chat_id, photo=photo_file_id, caption=caption)
        except Exception as e:
            logger.error(f"Error in photo message: {e}")
            raise HandlerError(f"Failed to handle photo message: {e}")

    @staticmethod
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle all messages."""
        try:
            await update.message.reply_text(BotMessages.ECHO_PREFIX + update.message.text)
        except Exception as e:
            logger.error(f"Error in handle message: {e}")
            raise HandlerError(f"Failed to handle message: {e}")

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
                    "Có lỗi xảy ra. Xem log để biết thêm chi tiết."
                )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")


def setup_handlers(application) -> None:
    """Setup all bot handlers."""
    try:
        # Command handlers
        application.add_handler(CommandHandler("help", BotHandlers.help_command))
        
        # Message handlers
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, BotHandlers.text_message))

        application.add_handler(MessageHandler(filters.PHOTO, BotHandlers.photo_message))

        # application.add_handler(MessageHandler(filters.VIDEO | filters.VIDEO_NOTE, BotHandlers.video_message))

        # application.add_handler(MessageHandler(filters.DOCUMENT, BotHandlers.document_message))

        # application.add_handler(MessageHandler(filters.AUDIO, BotHandlers.audio_message))

        # application.add_handler(MessageHandler(filters.VOICE, BotHandlers.voice_message))
        
        # Error handler
        application.add_error_handler(BotHandlers.error_handler)
        
        logger.info(LogMessages.HANDLERS_SETUP)
        
    except Exception as e:
        logger.error(f"Failed to setup handlers: {e}")
        raise HandlerError(f"Handler setup failed: {e}")