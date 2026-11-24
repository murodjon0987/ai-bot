import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    FSInputFile
)
from dotenv import load_dotenv

import database as db
import ai_service

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "xotira_ai_bot")
PORT = int(os.getenv("PORT", 8080))

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! .env faylini tekshiring.")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Vaqtinchalik fayllar papkasi
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp_photos")
os.makedirs(TEMP_DIR, exist_ok=True)

user_pending_photos = {}

def get_main_keyboard():
    kb = [
        [KeyboardButton(text="📸 Rasm yuborish")],
        [KeyboardButton(text="👤 Profilim / Balans"), KeyboardButton(text="👥 Do'stlarni taklif qilish (+2)")],
        [KeyboardButton(text="ℹ️ Bot haqida")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_action_keyboard(photo_id: str):
    kb = [
        [
            InlineKeyboardButton(text="✨ HD Tiniqlashtirish", callback_data=f"enhance:{photo_id}"),
            InlineKeyboardButton(text="🎨 Rangli qilish", callback_data=f"colorize:{photo_id}")
        ],
        [
            InlineKeyboardButton(text="🖼 Fonni o'chirish (PNG)", callback_data=f"remove_bg:{photo_id}"),
            InlineKeyboardButton(text="👔 3x4 Hujjatga rasm", callback_data=f"passport:{photo_id}")
        ],
        [
            InlineKeyboardButton(text="🎭 Anime / Art stili", callback_data=f"cartoon:{photo_id}"),
            InlineKeyboardButton(text="👀 Jonli harakat (GIF)", callback_data=f"animate:{photo_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    referrer_id = None
    if command.args and command.args.startswith("ref_"):
        try:
            referrer_id = int(command.args.replace("ref_", ""))
        except ValueError:
            referrer_id = None

    user = await db.get_or_create_user(user_id, username, full_name, referrer_id)
    
    if user["is_new"] and user["referred_by"]:
        try:
            await bot.send_message(
                user["referred_by"],
                f"🎉 Tabriklaymiz! Sizning taklif havolangiz orqali yangi do'stingiz (@{username or full_name}) qo'shildi!\n"
                f"🎁 Sizga **+2 ta bepul urinish** qo'shildi!"
            )
        except Exception:
            pass

    welcome_text = (
        f"Assalomu alaykum, **{full_name}**! 👋\n\n"
        f"Men **Jonli Xotira AI** (@{BOT_USERNAME}) ko'p funksiyali sun'iy intellekt boti bo'laman!\n\n"
        f"🌟 **Mening barcha imkoniyatlarim:**\n"
        f"✨ **HD Tiniqlashtirish** — Eski va xira yuzlarni o'ta aniq qilish\n"
        f"🎨 **Rangli qilish** — Oq-qora suratlarga jonli rang berish\n"
        f"🖼 **Fonni o'chirish** — Orqa fonni tozalab, tiniq PNG/stiker qilish\n"
        f"👔 **3x4 Hujjatga rasm** — Pasport va hujjatlar uchun 6 talik tayyor varaq\n"
        f"🎭 **Anime / Art stili** — Rasmingizni komiks/multfilm qahramoniga aylantirish\n"
        f"👀 **Jonli harakat** — Suratni nafas oluvchi jonli GIF animatsiya qilish\n\n"
        f"🎁 Sizda hozir **{user['credits']} ta bepul urinish** mavjud!\n\n"
        f"👉 Sinab ko'rish uchun menga **birorta rasm yuboring**!"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")


@dp.message(F.text == "📸 Rasm yuborish")
async def btn_send_photo(message: types.Message):
    await message.answer(
        "📷 Menga istalgan suratingizni yuboring (oddiy rasm yoki fayl ko'rinishida).\n"
        "Keyin esa 6 xil sehrli AI amalidan birini tanlaysiz!",
        parse_mode="Markdown"
    )


@dp.message(F.text == "👤 Profilim / Balans")
async def btn_profile(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        user = await db.get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
        
    ref_count = await db.get_referral_count(message.from_user.id)
    
    text = (
        f"👤 **Sizning profilingiz:**\n\n"
        f"🆔 ID: `{message.from_user.id}`\n"
        f"⚡️ Qolgan bepul urinishlar: **{user['credits']} ta**\n"
        f"🖼 Ishlov berilgan jami rasmlar: **{user['total_restored']} ta**\n"
        f"👥 Taklif qilgan do'stlaringiz: **{ref_count} ta**\n\n"
        f"🎁 *Urinishlar tugasa, do'stlaringizni taklif qilib, har bir do'stingiz uchun +2 tadan bepul urinish olishingiz mumkin!*"
    )
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text == "👥 Do'stlarni taklif qilish (+2)")
async def btn_invite(message: types.Message):
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{message.from_user.id}"
    ref_count = await db.get_referral_count(message.from_user.id)
    
    text = (
        f"👥 **Do'stlaringizni taklif qiling va bepul urinishlar oling!**\n\n"
        f"Har bir taklif qilgan do'stingiz botga kirganda, sizga **+2 ta bepul urinish** beriladi!\n\n"
        f"🔗 **Sizning shaxsiy taklif havolangiz:**\n"
        f"`{ref_link}`\n\n"
        f"📊 Hozirgacha taklif qilingan: **{ref_count} kishi**\n\n"
        f"👇 Havolani do'stlaringiz va guruhlarga yuboring:"
    )
    
    share_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📲 Do'stlarga ulashish",
            url=f"https://t.me/share/url?url={ref_link}&text=Rasmlarni%20HD%20tiniqlashtiruvchi,%20rangli%20qiluvchi%20va%20fonini%20o'chiruvchi%20universal%20AI%20bot!"
        )]
    ])
    await message.answer(text, reply_markup=share_kb, parse_mode="Markdown")


@dp.message(F.text == "ℹ️ Bot haqida")
async def btn_about(message: types.Message):
    stats = await db.get_stats()
    text = (
        f"ℹ️ **Jonli Xotira AI — Universal foto yordamchi**\n\n"
        f"Bot quyidagi 6 ta AI xizmatini o'z ichiga oladi:\n"
        f"1. ✨ HD Tiniqlashtirish\n"
        f"2. 🎨 Rangli qilish\n"
        f"3. 🖼 Fonni tozalash (Stiker yasash)\n"
        f"4. 👔 3x4 Pasport formati (Chop etishga tayyor 6 talik varaq)\n"
        f"5. 🎭 Anime va Komiks Art effekti\n"
        f"6. 👀 Jonli harakat (Animatsiya GIF)\n\n"
        f"📊 **Statistika:**\n"
        f"👥 Foydalanuvchilar: **{stats['total_users']} kishi**\n"
        f"📸 Ishlov berilgan rasmlar: **{stats['total_restored']} ta**"
    )
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.photo | F.document)
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        user = await db.get_or_create_user(user_id, message.from_user.username, message.from_user.full_name)

    if user["credits"] <= 0:
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
        await message.answer(
            "😔 **Kechirasiz, sizda bepul urinishlar tugadi!**\n\n"
            "Yana bepul foydalanish uchun o'z havolangizni do'stlaringizga yuboring:\n"
            f"`{ref_link}`\n\n"
            "Har bir taklif qilingan do'stingiz uchun **+2 ta urinish** olasiz! 🎁",
            parse_mode="Markdown"
        )
        return

    status_msg = await message.answer("⏳ Surat qabul qilinmoqda...")
    
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
        file_id = message.document.file_id
    else:
        await status_msg.edit_text("❌ Iltimos, faqat rasm (JPEG/PNG) formatidagi fayl yuboring!")
        return

    file = await bot.get_file(file_id)
    file_ext = os.path.splitext(file.file_path)[1] or ".jpg"
    local_filename = f"{user_id}_{message.message_id}{file_ext}"
    input_path = os.path.join(TEMP_DIR, local_filename)

    await bot.download_file(file.file_path, input_path)
    user_pending_photos[str(message.message_id)] = input_path

    await status_msg.delete()
    await message.answer(
        "Suratingiz qabul qilindi! Nima qilishni xohlaysiz? Quyidagi 6 ta amaldan birini tanlang 👇",
        reply_markup=get_action_keyboard(str(message.message_id))
    )


ACTION_NAMES = {
    "enhance": "✨ HD Tiniqlashtirish",
    "colorize": "🎨 Rangli qilish",
    "remove_bg": "🖼 Fonni o'chirish (PNG)",
    "passport": "👔 3x4 Hujjatga rasm",
    "cartoon": "🎭 Anime / Art stili",
    "animate": "👀 Jonli harakat (GIF)"
}

@dp.callback_query(F.data.func(lambda d: any(d.startswith(f"{k}:") for k in ACTION_NAMES.keys())))
async def process_photo_action(callback: types.CallbackQuery):
    action, photo_id = callback.data.split(":")
    input_path = user_pending_photos.get(photo_id)

    if not input_path or not os.path.exists(input_path):
        await callback.answer("⚠️ Surat muddati o'tib ketgan, iltimos qaytadan yuboring!", show_alert=True)
        return

    user_id = callback.from_user.id
    has_credit = await db.use_credit(user_id)
    if not has_credit:
        await callback.answer("Urinishlaringiz tugagan!", show_alert=True)
        return

    action_label = ACTION_NAMES.get(action, "Ishlov berish")
    await callback.message.edit_text(
        f"⏳ **Sun'iy intellekt ishlamoqda...**\n\n"
        f"Amal: *{action_label}*\n"
        f"Iltimos, bir necha soniya kuting...",
        parse_mode="Markdown"
    )

    ext = ".png" if action == "remove_bg" else (".gif" if action == "animate" else ".jpg")
    output_filename = f"result_{action}_{photo_id}{ext}"
    output_path = os.path.join(TEMP_DIR, output_filename)

    try:
        if action == "enhance":
            await ai_service.enhance_image(input_path, output_path)
        elif action == "colorize":
            await ai_service.colorize_image(input_path, output_path)
        elif action == "remove_bg":
            await ai_service.remove_bg(input_path, output_path)
        elif action == "passport":
            await ai_service.passport_3x4(input_path, output_path)
        elif action == "cartoon":
            await ai_service.cartoonize_image(input_path, output_path)
        elif action == "animate":
            await ai_service.animate_motion(input_path, output_path)

        user = await db.get_user(user_id)
        caption = (
            f"✅ **Tayyor bo'ldi!**\n\n"
            f"⚙️ Amal: *{action_label}*\n"
            f"⚡️ Qolgan bepul balansingiz: **{user['credits']} ta**\n\n"
            f"Do'stlaringizga ham ulashing: @{BOT_USERNAME}"
        )
        
        await callback.message.delete()
        
        if action == "animate":
            await bot.send_animation(
                chat_id=user_id,
                animation=FSInputFile(output_path),
                caption=caption,
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        elif action == "remove_bg":
            # Transparent PNG fayl sifatini yo'qotmaslik uchun hujjat sifatida yuborish
            await bot.send_document(
                chat_id=user_id,
                document=FSInputFile(output_path),
                caption=caption,
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            await bot.send_photo(
                chat_id=user_id,
                photo=FSInputFile(output_path),
                caption=caption,
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )

    except Exception as e:
        logger.error(f"Xatolik rasm qayta ishlashda ({action}): {e}")
        await db.add_credits(user_id, 1)
        await callback.message.answer(
            f"😔 Kechirasiz, suratga ishlov berishda xatolik yuz berdi. Urinishingiz balansingizga qaytarildi."
        )

    finally:
        if os.path.exists(input_path):
            try:
                os.remove(input_path)
            except Exception:
                pass
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass
        user_pending_photos.pop(photo_id, None)


async def handle_ping(request):
    return web.Response(text="Bot is alive and running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/ping", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Keep-alive web server {PORT}-portda ishga tushdi.")


async def main():
    await db.init_db()
    await start_web_server()
    logger.info(f"Bot @{BOT_USERNAME} polling rejimida ishga tushdi!")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
