from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
import os
import yt_dlp

router = Router()

@router.message(Command("start"))
async def start_handler(msg: Message):
    await msg.answer("Привет, я бот скачивающий видосики по ссылке. Дай мне ссылку, а отправлю тебе mp4 файл")


# @router.message()
# async def message_handler(msg: Message):
#     await msg.answer(f": ")

@router.message(F.text)
async def download_video(msg: Message):
    url = msg.text.strip()

    # Проверка, что это ссылка
    if not (url.startswith("http://") or url.startswith("https://")):
        await msg.reply("Пожалуйста, отправьте корректную ссылку на видео.")
        return

    await msg.reply("Скачиваю видео... ⏳")

    try:
        # Создаем папку downloads, если её нет
        os.makedirs("Downloads", exist_ok=True)

        # Настройки yt-dlp для скачивания в MP4
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': 'Downloads/%(title)s.%(ext)s',
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        # Проверяем, существует ли файл
        if not os.path.exists(filename):
            raise FileNotFoundError("Файл не был создан.")

        # Отправляем видео пользователю
        video = FSInputFile(filename)
        await msg.reply_video(video, caption="Вот ваше видео! 🎬")

        # Удаляем файл после отправки
        os.remove(filename)

    except Exception as e:
        error_message = f"Произошла ошибка при скачивании видео: {str(e)}"
        await msg.reply(error_message)
