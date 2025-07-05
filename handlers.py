from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from urllib.parse import urlparse
import os
import logging
import asyncio
import tempfile
import aiofiles
import aiohttp
import yt_dlp

MAX_FILE_SIZE=50 * 1024 * 1024

router = Router()

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self):
        self.ydl_opts = {
            'format': 'best[filesize<50M]/best',
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        
    async def download_video(self, url: str, output_path: str):
        try:
            # Обновляем путь вывода
            self.ydl_opts['outtmpl'] = os.path.join(output_path, '%(title)s.%(ext)s')
            
            # Запускаем в отдельном потоке, чтобы не блокировать event loop
            loop = asyncio.get_event_loop()
            
            def download_sync():
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    # Получаем информацию о видео
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'video')
                    
                    # Проверяем размер файла
                    filesize = info.get('filesize') or info.get('filesize_approx', 0)
                    if filesize > MAX_FILE_SIZE:
                        return None, f"Файл слишком большой ({filesize / 1024 / 1024:.1f} MB). Максимум 50MB."
                    
                    # Скачиваем видео
                    ydl.download([url])
                    return title, None
            
            result = await loop.run_in_executor(None, download_sync)
            
            if result[1]:  # Если есть ошибка
                return None, result[1]
            
            title = result[0]
            
            # Находим скачанный файл
            for file in os.listdir(output_path):
                if file.endswith(('.mp4', '.avi', '.mkv', '.webm', '.mov', '.flv')):
                    return os.path.join(output_path, file), title
            
            return None, "Не удалось найти скачанный файл"
            
        except Exception as e:
            logger.error(f"Ошибка при скачивании через yt-dlp: {e}")
            return None, f"Ошибка при скачивании: {str(e)}"

    async def download_direct_video(self, url: str, output_path: str):
        """Скачивает видео напрямую по прямой ссылке"""
        try:
            timeout = aiohttp.ClientTimeout(total=300)  # 5 минут
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None, f"Не удалось загрузить файл (код: {response.status})"
                    
                    # Проверяем размер файла
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > MAX_FILE_SIZE:
                        return None, f"Файл слишком большой ({int(content_length) / 1024 / 1024:.1f} MB)"
                    
                    # Определяем имя файла
                    filename = os.path.basename(urlparse(url).path)
                    if not filename or '.' not in filename:
                        filename = "video.mp4"
                    
                    filepath = os.path.join(output_path, filename)
                    
                    # Скачиваем файл
                    total_size = 0
                    async with aiofiles.open(filepath, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                            total_size += len(chunk)
                            # Проверяем размер во время скачивания
                            if total_size > MAX_FILE_SIZE:
                                await f.close()
                                os.remove(filepath)
                                return None, f"Файл слишком большой ({total_size / 1024 / 1024:.1f} MB)"
                    
                    return filepath, filename
        except Exception as e:
            logger.error(f"Ошибка при прямом скачивании: {e}")
            return None, f"Ошибка при скачивании: {str(e)}"

downloader = VideoDownloader()

@router.message(Command("start"))
async def start_handler(msg: Message):
    welcome_message = """
🎬 <b>Привет! Я бот для скачивания видео.</b>

Отправь мне ссылку на видео, и я скачаю его для тебя!

<b>Поддерживаются:</b>
• YouTube, YouTube Shorts
• TikTok
• Instagram (посты и reels)
• Twitter/X
• VK Video
• Rutube
• И многие другие платформы
• Прямые ссылки на видеофайлы

<b>Ограничения:</b>
📁 Максимальный размер файла: 50MB 
⏱ Время ожидания: 5 минут

<b>Как использовать:</b>
1. Отправь ссылку на видео
2. Жди, пока я его скачаю
3. Получи видео в чате!

🚀 <i>Просто отправь ссылку и жди!</i>
    """
    await msg.answer(welcome_message, parse='HTML')

@dp.message(Command("help"))
async def help_handler(message: Message):
    """Обработчик команды /help"""
    help_text = """
🆘 <b>Помощь по использованию бота:</b>

<b>Основные команды:</b>
/start - Главное меню
/help - Эта справка

<b>Как скачать видео:</b>
1. Скопируй ссылку на видео
2. Отправь её боту
3. Жди завершения скачивания

<b>Поддерживаемые форматы:</b>
📹 MP4, AVI, MKV, WebM, MOV, FLV

<b>Если видео не скачивается:</b>
• Проверь, что ссылка рабочая
• Убедись, что видео не приватное
• Проверь размер файла (макс. 50MB)
• Попробуй другую ссылку

<b>Примеры поддерживаемых ссылок:</b>
• https://youtube.com/watch?v=...
• https://youtu.be/...
• https://tiktok.com/@user/video/...
• https://instagram.com/p/...
• https://twitter.com/user/status/...

❓ <i>Возникли вопросы? Свяжитесь с администратором.</i>
    """
    await message.answer(help_text, parse_mode='HTML')

async def is_valid_url(url) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

@router.message(F.text)
async def text_handler(msg: Message):
    text = msg.text.strip()
    
    if not is_valid_url(text):
        await msg.reply(
            "🤔 <b>Это не похоже на ссылку.</b>\n\n"
            "Отправьте мне корректную ссылку на видео или используйте /help для получения помощи.\n\n"
            "Пример: https://youtube.com/watch?v=...",
            parse_mode='HTML'
        )
        return
    
    status_message = await msg.reply("⏳ <b>Начинаю скачивание...</b>", parse_mode='HTML')

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            await status_message.edit_text("📥 <b>Анализирую ссылку...</b>", parse_mode='HTML')
            filepath, title = await downloader.download_video(text, temp_dir)

            if not filepath:
                await status_message.edit_text("📥 <b>Пробую альтернативный способ...</b>", parse_mode='HTML')
                filepath, title = await downloader.download_direct_video(text, temp_dir)

            if not filepath:
                await status_message.edit_text(f"❌ <b>Ошибка:</b> {title}", parse_mode='HTML')
                return

            if not os.path.exists(filepath):
                await status_message.edit_text("❌ <b>Файл не найден после скачивания</b>", parse_mode='HTML')
                return

            file_size = os.path.getsize(filepath)
            if file_size > MAX_FILE_SIZE:
                await status_message.edit_text(
                    f"❌ <b>Файл слишком большой</b>\n"
                    f"Размер: {file_size / 1024 / 1024:.1f} MB\n"
                    f"Максимум: 50 MB",
                    parse_mode='HTML'
                )
                return

            await status_message.edit_text("📤 <b>Отправляю видео...</b>", parse_mode='HTML')

            video_file = FSInputFile(filepath)

            caption = f"🎬 <b>{title}</b>\n📊 Размер: {file_size / 1024 / 1024:.1f} MB"

            await msg.answer_video(
                video = video_file,
                caption = caption,
                parse_mode = 'HTML',
                supports_streaming = True,
            )

            await status_message.delete()

        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")
            await status_message.edit_text(
                f"❌ <b>Произошла ошибка:</b>\n<code>{str(e)}</code>",
                parse_mode='HTML'
            )
