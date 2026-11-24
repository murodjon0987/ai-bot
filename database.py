import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                credits INTEGER DEFAULT 3,
                referred_by INTEGER,
                total_restored INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def get_or_create_user(user_id: int, username: str = None, full_name: str = None, referrer_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, credits, total_restored, referred_by FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "user_id": row[0],
                    "credits": row[1],
                    "total_restored": row[2],
                    "referred_by": row[3],
                    "is_new": False
                }
            
            # Yangi foydalanuvchi: 3 ta bepul rasm
            initial_credits = 3
            ref_id = None
            if referrer_id and referrer_id != user_id:
                # Referal mavjudligini tekshirish
                async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (referrer_id,)) as ref_cur:
                    if await ref_cur.fetchone():
                        ref_id = referrer_id
                        # Taklif qilgan odamga +2 ta bepul rasm qo'shish
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
                "is_new": True
            }

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, credits, total_restored, referred_by FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "user_id": row[0],
                    "credits": row[1],
                    "total_restored": row[2],
                    "referred_by": row[3]
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

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*), SUM(total_restored) FROM users") as cursor:
            row = await cursor.fetchone()
            return {
                "total_users": row[0] if row else 0,
                "total_restored": row[1] if row and row[1] else 0
            }
