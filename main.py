import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
from handlers import router
from performance_monitor import performance_monitor
from scaling_config import BOT_CONFIG, LOGGING_CONFIG


async def main():
    # Запуск мониторинга производительности
    performance_monitor.start_monitoring(interval=60)
    
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Устанавливаем описание бота (текст над кнопкой "Начать")
    bot_description = (
        "👋 Привет!\n\n"
        "Этот бот поможет тебе разделять расходы в поездках и не тратить на это много времени"
    )
    try:
        await bot.set_my_description(description=bot_description)
        print("✅ Описание бота установлено")
    except Exception as e:
        print(f"⚠️ Не удалось установить описание бота: {e}")
    
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
