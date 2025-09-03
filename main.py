import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from config import settings
from handlers import hr, start, interview, report, misc
from storage import load_state

print(settings.TELEGRAM_BOT_TOKEN)
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


dp.include_router(start.router)
dp.include_router(interview.router)
dp.include_router(hr.router)   # добавлено
dp.include_router(report.router)
dp.include_router(misc.router)


async def main():
    logging.basicConfig(level=logging.INFO)
    load_state()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())