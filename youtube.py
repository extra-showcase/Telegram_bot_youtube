import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
import re
import uuid
import tempfile
import pytube
from urllib.parse import urlparse

# === CONFIGURATION === #
BOT_TOKEN = "8088556649:AAFayjdQ2Fmqf_y9dpayI6hKs8ed2vVnu1s"
BOT_USERNAME = "sh_youtube_downloader_bot"
MAIN_CHANNEL_URL = "https://t.me/your_main_channel" 
DOWNLOAD_EXPIRY_MINUTES = 20  # 20 minute expiry for download links

# URLs for other platform bots
PLATFORM_BOTS = {
    "tiktok": "https://t.me/sh_tiktok_downloader_bot",
    "pinterest": "https://t.me/sh_pinterest_downloader_bot",
    "linkedin": "https://t.me/sh_linkein_downloader_bot",
    "instagram": "https://t.me/sh_instagram_downloader_bot",
    "youtube": "https://t.me/sh_youtube_downloader_bot" 
}

# Rate limiting configuration
MAX_REQUESTS_PER_MINUTE = 10

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === RATE LIMITING CLASS === #
class RateLimiter:
    def __init__(self):
        self.user_activity = defaultdict(list)
    
    async def check_rate_limit(self, user_id: int) -> bool:
        """Check if user has exceeded rate limit"""
        now = datetime.now()
        self.user_activity[user_id] = [
            t for t in self.user_activity[user_id]
            if now - t < timedelta(minutes=1)
        ]
        
        if len(self.user_activity[user_id]) >= MAX_REQUESTS_PER_MINUTE:
            return True
        
        self.user_activity[user_id].append(now)
        return False

rate_limiter = RateLimiter()

# === HELPER FUNCTIONS === #
def get_main_menu() -> InlineKeyboardMarkup:
    """Returns the main menu with platform buttons."""
    keyboard = [
        [InlineKeyboardButton("📌 Join Our Main Channel", url=MAIN_CHANNEL_URL)],
        [InlineKeyboardButton("🎵 TikTok Downloader", url=PLATFORM_BOTS["tiktok"])],
        [InlineKeyboardButton("📷 Pinterest Downloader", url=PLATFORM_BOTS["pinterest"])],
        [InlineKeyboardButton("🔗 LinkedIn Downloader", url=PLATFORM_BOTS["linkedin"])],
        [InlineKeyboardButton("📸 Instagram Downloader", url=PLATFORM_BOTS["instagram"])],
        [InlineKeyboardButton("🎥 YouTube Downloader", callback_data="youtube")]
    ]
    return InlineKeyboardMarkup(keyboard)

def is_valid_youtube_url(url: str) -> bool:
    """Check if URL is a valid YouTube URL"""
    patterns = [
        r'^https?://(www\.)?youtube\.com/watch\?v=',
        r'^https?://youtu\.be/',
        r'^https?://(www\.)?youtube\.com/shorts/'
    ]
    return any(re.search(pattern, url) for pattern in patterns)

async def generate_download_link(youtube_url: str) -> str:
    """Generate a temporary download link for the YouTube video"""
    try:
        yt = pytube.YouTube(youtube_url)
        stream = yt.streams.get_highest_resolution()
        
        # Generate a unique download token
        download_token = str(uuid.uuid4())
        
        # In a real implementation, you would:
        # 1. Store the download token with expiry time
        # 2. Set up a web server to handle the download
        # 3. Return the download URL with token
        
        # For this example, we'll return a mock URL
        return f"https://your-download-server.com/download/{download_token}"
    except Exception as e:
        logger.error(f"Error generating download link: {e}")
        raise

# === HANDLERS === #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message"""
    if await rate_limiter.check_rate_limit(update.effective_user.id):
        await update.message.reply_text("⚠️ Too many requests! Please wait a minute.")
        return
    
    user = update.effective_user
    logger.info(f"User {user.id} started the bot")
    
    welcome_text = (
        f"👋 Hello {user.first_name}!\n\n"
        "Welcome to YouTube Video Downloader Bot!\n"
        "Send me a YouTube link to get a download link.\n\n"
        "Or choose another download service:"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu()
    )

async def handle_youtube_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle YouTube links sent by users"""
    if await rate_limiter.check_rate_limit(update.effective_user.id):
        await update.message.reply_text("⚠️ Too many requests! Please wait a minute.")
        return
    
    url = update.message.text
    
    if not is_valid_youtube_url(url):
        await update.message.reply_text(
            "❌ Invalid YouTube URL. Please send a valid YouTube link.\n"
            "Examples:\n"
            "- https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
            "- https://youtu.be/dQw4w9WgXcQ\n"
            "- https://www.youtube.com/shorts/VIDEO_ID"
        )
        return
    
    try:
        # Show typing indicator
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        # Generate download link
        download_url = await generate_download_link(url)
        expiry_time = (datetime.now() + timedelta(minutes=DOWNLOAD_EXPIRY_MINUTES)).strftime("%H:%M")
        
        await update.message.reply_text(
            f"✅ Here's your download link (expires at {expiry_time}):\n"
            f"{download_url}\n\n"
            "⚠️ Note: This link will expire in 20 minutes. "
            "Please download the video before then.",
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error processing YouTube link: {e}")
        await update.message.reply_text(
            "❌ Error processing your YouTube link. Please try again later."
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and notify user"""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    if update and hasattr(update, 'effective_user'):
        user_id = update.effective_user.id
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠️ An error occurred. Please try again later."
            )
        except Exception as e:
            logger.error(f"Couldn't send error message to user {user_id}: {e}")

# === MAIN FUNCTION === #
def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_youtube_link))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    logger.info("🚀 Starting YouTube Downloader Bot...")
    application.run_polling()

if __name__ == '__main__':
    # Install required packages if not already installed
    try:
        import pytube
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "pytube"])
    
    main()