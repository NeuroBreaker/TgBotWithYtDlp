import asyncio
import logging
import config
from handlers import router, logger
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN=config.BOT_TOKEN

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

async def main():
    try:
        print("🚀 Bot starting")

        await bot.delete_webhook(drop_pending_updates=True)

        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except Exception as e:
        logger.error(f"❌ Error on startup: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
