import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import TELEGRAM_TOKEN
from handlers import commands, callbacks
from services.process_manager import ProcessManager

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """Запуск бота"""
    try:
        # Проверяем и очищаем старые процессы
        if ProcessManager.is_bot_running():
            logger.warning("Found running bot instance, cleaning up...")
            ProcessManager.cleanup_old_processes()

        # Сохраняем PID текущего процесса
        ProcessManager.save_pid()

        # Инициализация бота и диспетчера
        bot = Bot(token=TELEGRAM_TOKEN)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        # Регистрация роутеров
        dp.include_router(commands.router)
        dp.include_router(callbacks.router)

        # Запуск бота
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        raise
    finally:
        # Удаляем PID файл при завершении
        ProcessManager.remove_pid()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")