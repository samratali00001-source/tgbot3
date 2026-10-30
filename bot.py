import asyncio
import logging
import os
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from dotenv import load_dotenv

load_dotenv()

# ==================== CONFIG ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "DarkBugBountyHunter"          # without @
CHANNEL_LINK = f"https://t.me/{CHANNEL_USERNAME}"
CHANNEL_NAME = "Dark Bug Bounty Hunter"           # সুন্দর নাম বাটনে দেখাবে

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# ==================== HELPER ====================
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        return member.status in {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR
        }
    except Exception:
        return False


def get_join_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"🔗 Join {CHANNEL_NAME}",
                url=CHANNEL_LINK
            )
        ],
        [
            InlineKeyboardButton(
                text="✅ I Have Joined – Verify",
                callback_data="check_sub"
            )
        ]
    ])


# ==================== FORCE JOIN MIDDLEWARE ====================
class ForceJoinMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Only in groups
        if event.chat.type not in {"group", "supergroup"}:
            return await handler(event, data)

        # Skip bots and service messages
        if not event.from_user or event.from_user.is_bot:
            return await handler(event, data)

        # Check subscription
        if await is_subscribed(event.from_user.id):
            return await handler(event, data)

        # Not joined → Delete message
        try:
            await event.delete()
        except (TelegramBadRequest, TelegramForbiddenError):
            pass

        # Send warning with beautiful button
        text = (
            f"🚫 <b>{event.from_user.full_name}</b>, you must join our channel to send messages here!\n\n"
            f"Please join the channel below and then press <b>I Have Joined</b>."
        )

        try:
            await event.answer(text, reply_markup=get_join_keyboard(), disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Error sending warning: {e}")

        return  # Stop processing


dp.message.middleware(ForceJoinMiddleware())


# ==================== HANDLERS ====================
@dp.message(CommandStart())
async def start_handler(message: Message):
    if message.chat.type == "private":
        await message.answer(
            "👋 <b>Force Join Bot is Ready!</b>\n\n"
            f"Required Channel: <b>{CHANNEL_NAME}</b>\n"
            f"Link: {CHANNEL_LINK}\n\n"
            "Add me to your group as <b>Administrator</b> with these permissions:\n"
            "• Delete Messages\n"
            "• Ban Users\n"
            "• Restrict Members",
            reply_markup=get_join_keyboard()
        )
    else:
        await message.answer("✅ Bot is active in this group!")


@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        await callback.message.edit_text(
            f"✅ <b>{callback.from_user.full_name}</b>, verification successful!\n"
            "You can now chat freely. Enjoy! 🎉"
        )
        await callback.answer("Successfully verified!", show_alert=True)
    else:
        await callback.answer(
            "❌ You have not joined the channel yet!\nPlease join and try again.",
            show_alert=True
        )


# ==================== MAIN ====================
async def main():
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN not found in .env file")
    
    logger.info("Bot is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
