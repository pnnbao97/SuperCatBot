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
from agents.orchestrator import OrchestratorAgent
import os

logger = logging.getLogger(__name__)


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
            chat_id = update.message.chat_id
            user_name = update.effective_user.last_name
            message = f"Đây là câu hỏi của {user_name}: {message}"

            orchestration_agent = OrchestratorAgent(chat_id)

            # Gửi tin nhắn placeholder ban đầu
            status_message = await update.message.reply_text("⏳ Đang xử lý...")
            
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
    async def video_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle video messages."""
        try:
            caption = update.message.caption
            if not caption or not caption.startswith("/sc"):
                return
            chat_id = update.message.chat_id
            video_file_id = update.message.video.file_id
            video_file = await context.bot.get_file(video_file_id)
            
            # Tạo thư mục videos nếu không tồn tại
            os.makedirs("videos", exist_ok=True)
            # Tải video về
            video_path = f"videos/{video_file_id}.mp4"
            await video_file.download_to_drive(video_path)

            # Gửi lại video
            await context.bot.send_video(chat_id=chat_id, video=video_file_id, caption=caption)
        except Exception as e:
            logger.error(f"Error in video message: {e}")
            raise HandlerError(f"Failed to handle video message: {e}")

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

        application.add_handler(MessageHandler(filters.VIDEO | filters.VIDEO_NOTE, BotHandlers.video_message))

        # application.add_handler(MessageHandler(filters.DOCUMENT, BotHandlers.document_message))

        # application.add_handler(MessageHandler(filters.AUDIO, BotHandlers.audio_message))

        # application.add_handler(MessageHandler(filters.VOICE, BotHandlers.voice_message))
        
        # Error handler
        application.add_error_handler(BotHandlers.error_handler)
        
        logger.info(LogMessages.HANDLERS_SETUP)
        
    except Exception as e:
        logger.error(f"Failed to setup handlers: {e}")
        raise HandlerError(f"Handler setup failed: {e}")