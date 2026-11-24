import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    FSInputFile
)
from dotenv import load_dotenv

import database as db
import ai_service
from states import UserStates, PaymentStates, AdminStates

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "xotira_ai_bot")
SAFE_BOT_USERNAME = BOT_USERNAME.replace("_", "\\_")
PORT = int(os.getenv("PORT", 8080))
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "7777")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! .env faylini tekshiring.")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp_photos")
os.makedirs(TEMP_DIR, exist_ok=True)

user_pending_photos = {}

# 1. KONTAKT SO'RASH KLAVIATURASI
def get_contact_keyboard():
    kb = [
        [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)

# 2. ASOSIY MENYU
def get_main_keyboard(is_admin: bool = False):
    kb = [
        [KeyboardButton(text="📸 Rasm yuborish")],
        [KeyboardButton(text="💳 Tariflar va Balans to'ldirish"), KeyboardButton(text="👤 Profilim / Balans")],
        [KeyboardButton(text="🤖 Support AI (Yordamchi)"), KeyboardButton(text="👥 Do'stlarni taklif qilish (+2)")],
        [KeyboardButton(text="ℹ️ Bot haqida")]
    ]
    if is_admin:
        kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# SUPPORT AI KLAVIATURASI
def get_support_keyboard():
    kb = [
        [KeyboardButton(text="⬅️ Asosiy menyu")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# 3. 6 XIL AI AMALLARI (INLINE)
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

# 4. TARIFLAR MENYUSI (INLINE)
def get_tariffs_keyboard():
    kb = [
        [InlineKeyboardButton(text="🥉 10 ta rasm — 15 000 so'm", callback_data="buy:pack_10:15000:10")],
        [InlineKeyboardButton(text="🥈 30 ta rasm — 35 000 so'm", callback_data="buy:pack_30:35000:30")],
        [InlineKeyboardButton(text="🥇 100 ta rasm — 75 000 so'm", callback_data="buy:pack_100:75000:100")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ADMIN PANEL MENYUSI
def get_admin_keyboard():
    kb = [
        [InlineKeyboardButton(text="📊 To'liq Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Barchaga Xabar Yuborish (Rassilka)", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="💳 Karta Raqamini O'zgartirish", callback_data="admin_card")],
        [InlineKeyboardButton(text="➕ Foydalanuvchiga Balans Qo'shish", callback_data="admin_add_credit")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# KONTROLYOR: Foydalanuvchi telefonini tekshirish
async def ensure_phone_verified(message: types.Message, user: dict) -> bool:
    if not user.get("phone_number"):
        await message.answer(
            f"👋 Assalomu alaykum, **{message.from_user.full_name}**!\n\n"
            "Botning barcha imkoniyatlaridan to'liq foydalanish va soxta akkauntlardan himoyalanish uchun, "
            "iltimos, quyidagi tugma orqali **telefon raqamingizni tasdiqlang** 👇",
            reply_markup=get_contact_keyboard(),
            parse_mode="Markdown"
        )
        return False
    return True


@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject, state: FSMContext):
    await state.clear()
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
    
    # Agar admin ID .env da belgilangan bo'lsa
    if ADMIN_ID and user_id == ADMIN_ID and not user.get("is_admin"):
        await db.set_user_admin(user_id, True)
        user["is_admin"] = True

    # 1-QADAM: Telefon raqamini so'rash
    if not user.get("phone_number"):
        await message.answer(
            f"👋 Assalomu alaykum, **{full_name}**!\n\n"
            "Xush kelibsiz! Botdan foydalanishni boshlash uchun quyidagi tugmani bosib, "
            "**telefon raqamingizni yuboring** 👇",
            reply_markup=get_contact_keyboard(),
            parse_mode="Markdown"
        )
        await state.set_state(UserStates.waiting_for_phone)
        return

    # Yangi foydalanuvchi taklif qilingan bo'lsa
    if user["is_new"] and user["referred_by"]:
        try:
            await bot.send_message(
                user["referred_by"],
                f"🎉 Yangi do'stingiz (@{str(username or full_name).replace('_', '\\_')}) qo'shildi!\n"
                f"🎁 Sizga **+2 ta bepul urinish** qo'shildi!"
            )
        except Exception:
            pass

    welcome_text = (
        f"Assalomu alaykum, **{full_name}**! 👋\n\n"
        f"Men **Jonli Xotira AI** (@{SAFE_BOT_USERNAME}) ko'p funksiyali foto-studio boti bo'laman!\n\n"
        f"🌟 **Mening 6 ta super imkoniyatim:**\n"
        f"✨ **HD Tiniqlashtirish** — Eski va xira suratlarni tiniq qilish\n"
        f"🎨 **Rangli qilish** — Oq-qora suratlarga tabiiy rang berish\n"
        f"🖼 **Fonni o'chirish** — Orqa fonni tozalab, shaffof PNG stiker qilish\n"
        f"👔 **3x4 Hujjatga rasm** — Pasport uchun 6 talik tayyor foto-varaq\n"
        f"🎭 **Anime / Art stili** — Rasmni multfilm qahramoniga aylantirish\n"
        f"👀 **Jonli harakat** — Suratdan harakatlanuvchi jonli GIF animatsiya\n\n"
        f"⚡️ Sizda hozir: **{user['credits']} ta bepul urinish** mavjud!\n\n"
        f"👉 Sinab ko'rish uchun hoziroq menga **birorta surat yuboring**!"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(user.get("is_admin")), parse_mode="Markdown")


# TELEFON RAQAM QABUL QILISH
@dp.message(F.contact)
async def handle_contact(message: types.Message, state: FSMContext):
    contact = message.contact
    user_id = message.from_user.id
    phone = contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    await db.update_user_phone(user_id, phone)
    await state.clear()
    
    user = await db.get_user(user_id)
    await message.answer(
        "✅ **Raqamingiz muvaffaqiyatli tasdiqlandi!**\n\n"
        f"🎁 Sizga **3 ta bepul urinish** taqdim etildi!\n"
        "Endi menga istalgan suratingizni yuborib, AI imkoniyatlarini sinab ko'rishingiz mumkin! 👇",
        reply_markup=get_main_keyboard(user.get("is_admin") if user else False),
        parse_mode="Markdown"
    )


# TARIFLAR VA TO'LOV BO'LIMI
@dp.message(F.text == "💳 Tariflar va Balans to'ldirish")
async def btn_tariffs(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if not await ensure_phone_verified(message, user):
        return

    card_number = await db.get_setting("card_number", "8600 0000 0000 0000")
    card_holder = await db.get_setting("card_holder", "XOTIRA AI ADMIN")

    text = (
        "💳 **Balansni to'ldirish va Premium Tariflar:**\n\n"
        "O'zingizga ma'qul paketni tanlang:\n"
        "🥉 **10 ta rasm** — 15 000 so'm *(1 ta rasm = 1500 so'm)*\n"
        "🥈 **30 ta rasm** — 35 000 so'm *(1 ta rasm = 1160 so'm)*\n"
        "🥇 **100 ta rasm** — 75 000 so'm *(1 ta rasm = 750 so'm)*\n\n"
        "To'lovlarni **Click, Payme, Uzum Bank** yoki istalgan bank ilovasi orqali amalga oshirishingiz mumkin.\n\n"
        "👇 Paketni tanlash uchun pastdagi tugmalardan birini bosing:"
    )
    await message.answer(text, reply_markup=get_tariffs_keyboard(), parse_mode="Markdown")


# PAKET TANLANGANDA
@dp.callback_query(F.data.startswith("buy:"))
async def process_buy_tariff(callback: types.CallbackQuery, state: FSMContext):
    _, pack_code, amount, credits = callback.data.split(":")
    amount = int(amount)
    credits = int(credits)

    card_number = await db.get_setting("card_number", "8600 0000 0000 0000")
    card_holder = await db.get_setting("card_holder", "XOTIRA AI ADMIN")

    await state.set_state(PaymentStates.waiting_for_receipt)
    await state.update_data(package_name=pack_code, amount=amount, credits=credits)

    text = (
        f"📋 **Tanlangan paket:** +{credits} ta rasm tiklash\n"
        f"💵 **To'lov summasi:** `{amount:,}` so'm\n\n"
        f"💳 **To'lov uchun karta:**\n"
        f"`{card_number}`\n"
        f"👤 **Karta egasi:** {card_holder}\n\n"
        "📲 **To'lov qilish yo'llari:**\n"
        f"• [Click orqali to'lash](https://my.click.uz)\n"
        f"• [Payme orqali to'lash](https://payme.uz)\n"
        "• Uzum Bank yoki istalgan bank ilovasida karta raqamini kiritib to'lang.\n\n"
        "⚠️ **MUHIM:** To'lovni amalga oshirgach, **to'lov chekining rasmini (skrinshotini)** shu yerga yuboring!\n"
        "Admin chekni tekshirib, 5-10 daqiqa ichida balansingizni to'ldiradi."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", disable_web_page_preview=True)


# CHEK RASMI QABUL QILISH
@dp.message(PaymentStates.waiting_for_receipt, F.photo | F.document)
async def handle_payment_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    package_name = data.get("package_name", "Standart")
    amount = data.get("amount", 0)
    credits = data.get("credits", 0)
    
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    user_id = message.from_user.id
    
    # Bazaga yozish
    payment_id = await db.create_payment(user_id, package_name, amount, credits, file_id)
    await state.clear()

    user = await db.get_user(user_id)
    await message.answer(
        "✅ **To'lov chekingiz qabul qilindi!**\n\n"
        f"🆔 So'rov raqami: `#{payment_id}`\n"
        f"💵 Summa: `{amount:,}` so'm\n"
        f"⚡️ Kutilayotgan balans: **+{credits} ta rasm**\n\n"
        "Chek adminga yuborildi. Tekshiruvdan o'tishi bilan sizga bildirishnoma keladi va balansingiz oshadi! Rahmat!",
        reply_markup=get_main_keyboard(user.get("is_admin") if user else False),
        parse_mode="Markdown"
    )

    # Adminga chekni yuborish
    admin_caption = (
        f"🔔 **YANGI TO'LOV CHEKI TUSHDI!**\n\n"
        f"🆔 So'rov: `#{payment_id}`\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name} (@{message.from_user.username or 'yoq'})\n"
        f"🆔 User ID: `{user_id}`\n"
        f"📱 Telefon: `{user.get('phone_number') or 'Noma\'lum'}`\n"
        f"💵 Summa: **{amount:,} so'm**\n"
        f"🎁 Paket: **+{credits} ta rasm**"
    )
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay_approve:{payment_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pay_reject:{payment_id}")
        ]
    ])

    # Barcha adminlarga yuborish
    async with aiosqlite_connection() as conn:
        cursor = await conn.execute("SELECT user_id FROM users WHERE is_admin = 1")
        admins = await cursor.fetchall()
        for adm in admins:
            try:
                if message.photo:
                    await bot.send_photo(chat_id=adm[0], photo=file_id, caption=admin_caption, reply_markup=admin_kb, parse_mode="Markdown")
                else:
                    await bot.send_document(chat_id=adm[0], document=file_id, caption=admin_caption, reply_markup=admin_kb, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Adminga yuborishda xatolik: {e}")


# TO'LOVNI TASDIQLASH / RAD ETISH (ADMIN CALLBACK)
@dp.callback_query(F.data.startswith("pay_approve:") | F.data.startswith("pay_reject:"))
async def process_payment_decision(callback: types.CallbackQuery):
    action, payment_id_str = callback.data.split(":")
    payment_id = int(payment_id_str)
    
    payment = await db.get_payment(payment_id)
    if not payment:
        await callback.answer("To'lov topilmadi!", show_alert=True)
        return
        
    if payment["status"] != "pending":
        await callback.answer(f"Bu to'lov allaqachon ko'rib chiqilgan ({payment['status']})!", show_alert=True)
        return

    if action == "pay_approve":
        await db.update_payment_status(payment_id, "approved")
        await db.add_credits(payment["user_id"], payment["credits"])
        
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n✅ **TO'LOV TASDIQLANDI! Foydalanuvchiga +{payment['credits']} ta rasm berildi.**",
            parse_mode="Markdown"
        )
        # Foydalanuvchiga xabar
        try:
            await bot.send_message(
                chat_id=payment["user_id"],
                text=(
                    "🎉 **Tabriklaymiz! To'lovingiz muvaffaqiyatli tasdiqlandi!**\n\n"
                    f"⚡️ Balansingizga **+{payment['credits']} ta rasm tiklash** qo'shildi!\n"
                    "Endi bemalol o'z rasmlaringizni yuborishingiz mumkin! Rahmat!"
                ),
                parse_mode="Markdown"
            )
        except Exception:
            pass

    else:
        await db.update_payment_status(payment_id, "rejected")
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n❌ **TO'LOV RAD ETILDI.**",
            parse_mode="Markdown"
        )
        try:
            await bot.send_message(
                chat_id=payment["user_id"],
                text=(
                    "❌ **Kechirasiz, siz yuborgan to'lov cheki tasdiqlanmadi.**\n\n"
                    "Sababi: Mablag' hisobga tushmagan yoki chek noto'g'ri yuborilgan.\n"
                    "Agar xatolik yuz bergan deb hisoblasangiz, iltimos admin bilan bog'laning."
                ),
                parse_mode="Markdown"
            )
        except Exception:
            pass


# ADMIN BO'LISH BUYRUG'I
@dp.message(Command("claim_admin"))
async def cmd_claim_admin(message: types.Message, command: CommandObject):
    key = command.args or ""
    if key == ADMIN_SECRET_KEY:
        await db.set_user_admin(message.from_user.id, True)
        await message.answer("👑 **Tabriklaymiz! Siz muvaffaqiyatli ADMIN bo'ldingiz!**\nEndi sizga /admin buyrug'i va to'lov xabarlari keladi.", parse_mode="Markdown")
    else:
        await message.answer("❌ Parol noto'g'ri!")


# ADMIN PANEL MENYUSI
@dp.message(F.text == "⚙️ Admin Panel")
@dp.message(Command("admin"))
async def cmd_admin_panel(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if not user or not user.get("is_admin"):
        await message.answer("❌ Siz admin emassiz! (Admin bo'lish uchun: `/claim_admin 7777`)", parse_mode="Markdown")
        return

    text = "👑 **ADMIN BOSHQARUV PANELI:**\n\nQuyidagi amallardan birini tanlang:"
    await message.answer(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")


# ADMIN STATISTIKA
@dp.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: types.CallbackQuery):
    stats = await db.get_stats()
    text = (
        "📊 **BOTNING REAL VAQT STATISTIKASI:**\n\n"
        f"👥 Jami foydalanuvchilar: **{stats['total_users']} ta**\n"
        f"📱 Tasdiqlangan telefon raqamlar: **{stats['total_verified_phones']} ta**\n"
        f"📸 Ishlov berilgan jami rasmlar: **{stats['total_restored']} ta**\n\n"
        f"💰 Muvaffaqiyatli to'lovlar soni: **{stats['approved_payments_count']} ta**\n"
        f"💵 Jami tushgan pul: **{stats['total_income']:,} so'm**"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")


# ADMIN: KARTA RAQAMINI O'ZGARTIRISH
@dp.callback_query(F.data == "admin_card")
async def cb_admin_card(callback: types.CallbackQuery, state: FSMContext):
    card = await db.get_setting("card_number")
    holder = await db.get_setting("card_holder")
    await state.set_state(AdminStates.waiting_for_card_info)
    await callback.message.answer(
        f"Hozirgi karta:\n`{card}` ({holder})\n\n"
        "Yangi karta ma'lumotlarini quyidagi formatda yuboring:\n"
        "`KARTA_RAQAM, KARTA_EGASI_ISMI`\n"
        "Masalan:\n`8600123456789012, ALISHER VALIYEV`",
        parse_mode="Markdown"
    )


@dp.message(AdminStates.waiting_for_card_info)
async def process_new_card(message: types.Message, state: FSMContext):
    parts = message.text.split(",")
    if len(parts) < 2:
        await message.answer("❌ Noto'g'ri format! Vergul bilan ajratib yuboring (Raqam, Ism).")
        return
    card_num = parts[0].strip()
    holder = parts[1].strip()
    await db.set_setting("card_number", card_num)
    await db.set_setting("card_holder", holder)
    await state.clear()
    await message.answer(f"✅ Yangi karta saqlandi:\n`{card_num}` ({holder})", parse_mode="Markdown")


# ADMIN: RASSILKA (BROADCAST)
@dp.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.answer(
        "📢 **Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring:**\n"
        "(Matn, rasm yoki video yuborishingiz mumkin. Bekor qilish uchun: /cancel)",
        parse_mode="Markdown"
    )


@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Rassilka bekor qilindi.")
        return

    users = await db.get_all_user_ids()
    await message.answer(f"⏳ {len(users)} ta foydalanuvchiga xabar yuborilmoqda...")
    await state.clear()

    count = 0
    for uid in users:
        try:
            await message.copy_to(chat_id=uid)
            count += 1
            await asyncio.sleep(0.04)
        except Exception:
            pass

    await message.answer(f"✅ Xabar muvaffaqiyatli **{count} ta** foydalanuvchiga yetkazildi!")


# ADMIN: QO'LDA BALANS QO'SHISH
@dp.callback_query(F.data == "admin_add_credit")
async def cb_admin_add_credit(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_manual_credit)
    await callback.message.answer(
        "Foydalanuvchiga balans qo'shish uchun quyidagi formatda yozing:\n"
        "`USER_ID, QO'SHILADIGAN_RASM_SONI`\n"
        "Masalan: `123456789, 10`",
        parse_mode="Markdown"
    )


@dp.message(AdminStates.waiting_for_manual_credit)
async def process_manual_credit(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split(",")
        uid = int(parts[0].strip())
        amount = int(parts[1].strip())
        await db.add_credits(uid, amount)
        await state.clear()
        await message.answer(f"✅ User `{uid}` ga **+{amount} ta rasm** qo'shildi!", parse_mode="Markdown")
        try:
            await bot.send_message(uid, f"🎁 Admin tomonidan balansingizga **+{amount} ta rasm** qo'shildi!")
        except Exception:
            pass
    except Exception as e:
        await message.answer(f"Xatolik: {e}. Format: `USER_ID, MIQDOR`")


# PROFIL VA BALANS
@dp.message(F.text == "👤 Profilim / Balans")
async def btn_profile(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if not await ensure_phone_verified(message, user):
        return

    ref_count = await db.get_referral_count(message.from_user.id)
    text = (
        f"👤 **Sizning profilingiz:**\n\n"
        f"🆔 ID: `{message.from_user.id}`\n"
        f"📱 Telefon: `{user.get('phone_number') or 'Tasdiqlanmagan'}`\n"
        f"⚡️ Mavjud balansingiz: **{user['credits']} ta rasm**\n"
        f"🖼 Ishlov berilgan jami rasmlar: **{user['total_restored']} ta**\n"
        f"👥 Taklif qilgan do'stlaringiz: **{ref_count} ta**\n\n"
        f"💳 *Balansni to'ldirish uchun 'Tariflar va Balans to'ldirish' tugmasidan foydalaning.*"
    )
    await message.answer(text, parse_mode="Markdown")


# REFERAL TIZIMI
@dp.message(F.text == "👥 Do'stlarni taklif qilish (+2)")
async def btn_invite(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if not await ensure_phone_verified(message, user):
        return

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


# BOT HAQIDA
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
        f"📱 Tasdiqlangan a'zolar: **{stats['total_verified_phones']} kishi**\n"
        f"📸 Ishlov berilgan rasmlar: **{stats['total_restored']} ta**"
    )
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text == "📸 Rasm yuborish")
async def btn_send_photo(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if not await ensure_phone_verified(message, user):
        return
    await message.answer(
        "📷 Menga istalgan suratingizni yuboring (oddiy rasm yoki fayl ko'rinishida).\n"
        "Keyin esa 6 xil AI amalidan birini tanlaysiz!",
        parse_mode="Markdown"
    )


# 🤖 24/7 SUPPORT AI (AQLLI YORDAMCHI BO'LIMI)
@dp.message(F.text.in_(["🤖 Support AI (Yordamchi)", "🤖 Support AI", "/support", "🤖 AI Yordamchi"]))
async def btn_support_ai(message: types.Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not await ensure_phone_verified(message, user):
        return

    await state.set_state(UserStates.waiting_for_ai_support)
    text = (
        "🤖 **Xotira AI — Universal Aqlli Yordamchi (Support AI)**\n\n"
        "Assalomu alaykum! Men eng so'nggi Google Gemini sun'iy intellekti asosida ishlovchi universal yordamchingizman.\n\n"
        "💡 **Mendan istalgan mavzuda bemalol savol so'rashingiz mumkin:**\n"
        "• 📸 Fotostudiya botimizning 6 xil xizmati va ulardan foydalanish\n"
        "• 🧠 Dasturlash, fan, matematika, fizika, texnologiya yoki tarix\n"
        "• ✍️ She'r, insho, matn yozish yoki professional tarjima\n"
        "• 🌍 Hayotiy maslahatlar, qiziqarli suhbat yoki biznes g'oyalar!\n\n"
        "✍️ *Savolingizni yoki fikringizni quyida bemalol yozib qoldiring:*\n"
        "*(Chiqish uchun istalgan payt '⬅️ Asosiy menyu' tugmasini bosing)*"
    )
    await message.answer(text, reply_markup=get_support_keyboard(), parse_mode="Markdown")


# SUPPORT AI BILAN SAVOL-JAVOB JARAYONI
@dp.message(UserStates.waiting_for_ai_support)
async def process_ai_support_chat(message: types.Message, state: FSMContext):
    if message.text in ["⬅️ Asosiy menyu", "⬅️ Asosiy menyuga qaytish", "/cancel", "/start"]:
        await state.clear()
        user = await db.get_user(message.from_user.id)
        await message.answer(
            "Asosiy menyuga qaytdingiz. Biror xizmatni tanlang:",
            reply_markup=get_main_keyboard(user.get("is_admin") if user else False)
        )
        return

    if not message.text:
        await message.answer("Iltimos, savolingizni matn ko'rinishida yozing.")
        return

    wait_msg = await message.answer("🧠 *Support AI o'ylamoqda...*", parse_mode="Markdown")
    reply = await ai_service.ask_gemini_ai(message.text, user_id=message.from_user.id)
    
    reply_text = (
        f"🤖 **Support AI:**\n\n"
        f"{reply}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Yana biror savolingiz bormi? Bemalol xohlagan mavzuda yozishingiz mumkin:*"
    )
    try:
        await wait_msg.edit_text(reply_text, reply_markup=get_support_keyboard(), parse_mode="Markdown")
    except Exception:
        # Markdown maxsus belgilari bo'lsa oddiy matn ko'rinishida yuborish
        await wait_msg.edit_text(reply_text.replace("**", "").replace("*", ""), reply_markup=get_support_keyboard())


# /AI BUYRUG'I ORQALI TEZKOR MUROJAAT
@dp.message(F.text.startswith("/ai") | F.text.startswith("/gemini"))
async def handle_quick_gemini(message: types.Message):
    query = message.text.replace("/ai", "").replace("/gemini", "").strip()
    if not query:
        await message.answer(
            "🤖 **Support AI:** Savolingizni `/ai Savol` ko'rinishida yozing.\n"
            "Masalan: `/ai Rasmlarni qanday tiniqlashtiraman?` yoki `/ai Python dasturlash haqida tushuntir`",
            parse_mode="Markdown"
        )
        return
    wait_msg = await message.answer("🧠 *Support AI o'ylamoqda...*", parse_mode="Markdown")
    reply = await ai_service.ask_gemini_ai(query, user_id=message.from_user.id)
    try:
        await wait_msg.edit_text(f"🤖 **Support AI:**\n\n{reply}", parse_mode="Markdown")
    except Exception:
        await wait_msg.edit_text(f"🤖 Support AI:\n\n{reply}")


# RASM QABUL QILISH
@dp.message(F.photo | F.document)
async def handle_photo(message: types.Message, state: FSMContext):
    # Agar foydalanuvchi hozir chek yuklash holatida bo'lsa
    cur_state = await state.get_state()
    if cur_state == PaymentStates.waiting_for_receipt:
        await handle_payment_receipt(message, state)
        return

    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user or not user.get("phone_number"):
        await ensure_phone_verified(message, user or {})
        return

    if user["credits"] <= 0:
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
        await message.answer(
            "😔 **Kechirasiz, sizda bepul urinishlar tugadi!**\n\n"
            "Davom etish uchun quyidagi yo'llardan birini tanlang:\n\n"
            "1. 💳 **Tariflar va Balans to'ldirish** tugmasi orqali hisobingizni to'ldiring.\n"
            "2. 👥 Shaxsiy havolangizni do'stlaringizga yuboring — har bir do'stingiz uchun **+2 ta bepul urinish** olasiz!\n\n"
            f"🔗 Sizning havolangiz: `{ref_link}`",
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
        "Suratingiz qabul qilindi! Nima qilishni xohlaysiz? Quyidagi amallardan birini tanlang 👇",
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
        await callback.answer("Urinishlaringiz tugagan! Iltimos, balansni to'ldiring.", show_alert=True)
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
            await ai_service.passport_3x4(input_path, output_path, wear_suit=True)
        elif action == "cartoon":
            await ai_service.cartoonize_image(input_path, output_path)
        elif action == "animate":
            await ai_service.animate_motion(input_path, output_path)

        user = await db.get_user(user_id)
        caption = (
            f"✅ **Tayyor bo'ldi!**\n\n"
            f"⚙️ Amal: *{action_label}*\n"
            f"⚡️ Qolgan balansingiz: **{user['credits']} ta**\n\n"
            f"Do'stlaringizga ham ulashing: @{SAFE_BOT_USERNAME}"
        )
        
        await callback.message.delete()
        
        if action == "animate":
            await bot.send_animation(
                chat_id=user_id,
                animation=FSInputFile(output_path),
                caption=caption,
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(user.get("is_admin"))
            )
        elif action == "remove_bg":
            await bot.send_document(
                chat_id=user_id,
                document=FSInputFile(output_path),
                caption=caption,
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(user.get("is_admin"))
            )
        else:
            await bot.send_photo(
                chat_id=user_id,
                photo=FSInputFile(output_path),
                caption=caption,
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(user.get("is_admin"))
            )

    except Exception as e:
        logger.error(f"Xatolik rasm qayta ishlashda ({action}): {e}")
        await db.add_credits(user_id, 1)
        await callback.message.answer(
            "😔 Kechirasiz, suratga ishlov berishda xatolik yuz berdi. Urinishingiz balansingizga qaytarildi."
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


async def aiosqlite_connection():
    import aiosqlite
    return await aiosqlite.connect(db.DB_PATH)


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
