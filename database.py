import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Foydalanuvchilar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                phone_number TEXT,
                credits INTEGER DEFAULT 3,
                referred_by INTEGER,
                total_restored INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Ustunlarni tekshirish va avtomatik qo'shish (Auto-migration)
        async with db.execute("PRAGMA table_info(users)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]
            if "phone_number" not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN phone_number TEXT")
            if "is_admin" not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
            if "credits" not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT 3")
            if "referred_by" not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
            if "total_restored" not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN total_restored INTEGER DEFAULT 0")
        
        # To'lovlar va cheklar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                package_name TEXT,
                amount INTEGER,
                credits INTEGER,
                receipt_file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Sozlamalar jadvali (Karta raqami va h.k.)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Standart karta raqami (agar yo'q bo'lsa)
        await db.execute("""
            INSERT OR IGNORE INTO settings (key, value) VALUES 
            ('card_number', '8600 0000 0000 0000'),
            ('card_holder', 'XOTIRA AI ADMIN')
        """)

        await db.commit()

async def get_or_create_user(user_id: int, username: str = None, full_name: str = None, referrer_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, credits, total_restored, referred_by, phone_number, is_admin FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                # Username yoki ismni yangilab qo'yish
                if username or full_name:
                    await db.execute(
                        "UPDATE users SET username = COALESCE(?, username), full_name = COALESCE(?, full_name) WHERE user_id = ?",
                        (username, full_name, user_id)
                    )
                    await db.commit()
                return {
                    "user_id": row[0],
                    "credits": row[1],
                    "total_restored": row[2],
                    "referred_by": row[3],
                    "phone_number": row[4],
                    "is_admin": bool(row[5]),
                    "is_new": False
                }
            
            initial_credits = 3
            ref_id = None
            if referrer_id and referrer_id != user_id:
                async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (referrer_id,)) as ref_cur:
                    if await ref_cur.fetchone():
                        ref_id = referrer_id
                        await db.execute("UPDATE users SET credits = credits + 2 WHERE user_id = ?", (referrer_id,))
            
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, credits, referred_by) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, full_name, initial_credits, ref_id)
            )
            await db.commit()
            
            return {
                "user_id": user_id,
                "credits": initial_credits,
                "total_restored": 0,
                "referred_by": ref_id,
                "phone_number": None,
                "is_admin": False,
                "is_new": True
            }

async def update_user_phone(user_id: int, phone: str, username: str = None, full_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cur:
            exists = await cur.fetchone()
        if exists:
            await db.execute("UPDATE users SET phone_number = ? WHERE user_id = ?", (phone, user_id))
        else:
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, phone_number, credits) VALUES (?, ?, ?, ?, 3)",
                (user_id, username, full_name, phone)
            )
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, credits, total_restored, referred_by, phone_number, is_admin FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "user_id": row[0],
                    "credits": row[1],
                    "total_restored": row[2],
                    "referred_by": row[3],
                    "phone_number": row[4],
                    "is_admin": bool(row[5])
                }
            return None

async def use_credit(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] <= 0:
                return False
            
        await db.execute("UPDATE users SET credits = credits - 1, total_restored = total_restored + 1 WHERE user_id = ?", (user_id,))
        await db.commit()
        return True

async def add_credits(user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def get_referral_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

# TO'LOVLAR BO'LIMI
async def create_payment(user_id: int, package_name: str, amount: int, credits: int, receipt_file_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO payments (user_id, package_name, amount, credits, receipt_file_id) VALUES (?, ?, ?, ?, ?)",
            (user_id, package_name, amount, credits, receipt_file_id)
        )
        payment_id = cursor.lastrowid
        await db.commit()
        return payment_id

async def get_payment(payment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, user_id, package_name, amount, credits, receipt_file_id, status FROM payments WHERE id = ?",
            (payment_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "user_id": row[1],
                    "package_name": row[2],
                    "amount": row[3],
                    "credits": row[4],
                    "receipt_file_id": row[5],
                    "status": row[6]
                }
            return None

async def update_payment_status(payment_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE payments SET status = ? WHERE id = ?", (status, payment_id))
        await db.commit()

# SOZLAMALAR
async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()

async def set_user_admin(user_id: int, is_admin: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_admin = ? WHERE user_id = ?", (1 if is_admin else 0, user_id))
        await db.commit()

async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*), SUM(total_restored) FROM users") as cursor:
            user_row = await cursor.fetchone()
            
        async with db.execute("SELECT COUNT(*), SUM(amount) FROM payments WHERE status = 'approved'") as cursor:
            pay_row = await cursor.fetchone()
            
        async with db.execute("SELECT COUNT(*) FROM users WHERE phone_number IS NOT NULL") as cursor:
            phone_row = await cursor.fetchone()

        return {
            "total_users": user_row[0] if user_row else 0,
            "total_restored": user_row[1] if user_row and user_row[1] else 0,
            "total_verified_phones": phone_row[0] if phone_row else 0,
            "approved_payments_count": pay_row[0] if pay_row else 0,
            "total_income": pay_row[1] if pay_row and pay_row[1] else 0
        }
