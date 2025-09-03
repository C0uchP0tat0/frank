import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile


router = Router()


@router.callback_query(F.data.startswith("report:"))
async def on_report(c: CallbackQuery):
    uid = c.data.split(":",1)[1]
    path = f"reports/report_{uid}.json"
    if not os.path.exists(path):
        await c.answer("Отчёт не найден", show_alert=True)
        return
    await c.message.answer_document(FSInputFile(path))
    await c.answer()