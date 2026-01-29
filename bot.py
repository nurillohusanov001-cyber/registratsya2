from telegram import *
from telegram.ext import *
import sqlite3, os, datetime

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ================= DB =================
conn = sqlite3.connect("data.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 tg_id INTEGER,
 fullname TEXT,
 phone TEXT,
 passport TEXT,
 room INTEGER,
 days INTEGER,
 total INTEGER,
 end_date TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS settings(
 id INTEGER PRIMARY KEY,
 card TEXT
)
""")
cur.execute("INSERT OR IGNORE INTO settings VALUES (1,'8600 XXXX XXXX XXXX')")
conn.commit()

# ================= HELPERS =================
def price(days):
    if days <= 10:
        return days * 50000
    if days <= 20:
        return days * 40000
    if days == 30:
        return 1000000
    return days * 40000

def rooms_kb():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"Xona {i}", callback_data=f"room_{i}")]
         for i in range(1,25)]
    )

def back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data="back")]])

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏨 Xonalar", callback_data="rooms")],
        [InlineKeyboardButton("🔍 Tekshirish (3 kun qoldi)", callback_data="check")],
        [InlineKeyboardButton("💳 Karta o‘zgartirish", callback_data="card")]
    ])

# ================= START =================
async def start(update: Update, context):
    context.user_data.clear()
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("🛠 ADMIN PANEL", reply_markup=admin_menu())
    else:
        await update.message.reply_text("🏨 Qaysi xonaga joylashyapsiz?", reply_markup=rooms_kb())

# ================= ROOMS =================
async def room(update: Update, context):
    q = update.callback_query
    await q.answer()
    room = int(q.data.split("_")[1])

    # ADMIN
    if update.effective_user.id == ADMIN_ID:
        cur.execute("SELECT id, fullname FROM users WHERE room=?", (room,))
        users = cur.fetchall()
        if not users:
            await q.message.reply_text("Bu xonada odam yo‘q", reply_markup=back_kb())
            return
        kb = [[InlineKeyboardButton(n, callback_data=f"user_{i}")] for i,n in users]
        kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data="back")])
        await q.message.reply_text(f"🏨 Xona {room}", reply_markup=InlineKeyboardMarkup(kb))
        return

    # CLIENT
    context.user_data["room"] = room
    await q.message.reply_text("Ism Familiyangizni yozing:")

# ================= TEXT =================
async def text(update: Update, context):
    # CLIENT REG
    if "room" in context.user_data:
        if "fullname" not in context.user_data:
            context.user_data["fullname"] = update.message.text
            await update.message.reply_text("Telefon raqamingiz:")
            return
        if "phone" not in context.user_data:
            context.user_data["phone"] = update.message.text
            await update.message.reply_text("Passport rasmini yuboring:")
            return

    # ADMIN ADD DAYS
    if context.user_data.get("add_days"):
        days = int(update.message.text)
        uid = context.user_data["uid"]
        total = price(days)
        end = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
        cur.execute("UPDATE users SET days=?, total=?, end_date=? WHERE id=?",
                    (days, total, end, uid))
        conn.commit()
        await update.message.reply_text(
            f"✅ Saqlandi\n⏳ {days} kun\n💰 {total} so‘m\n📅 Tugash: {end}",
            reply_markup=admin_menu()
        )
        context.user_data.clear()
        return

    # CHANGE CARD
    if context.user_data.get("change_card"):
        cur.execute("UPDATE settings SET card=? WHERE id=1", (update.message.text,))
        conn.commit()
        context.user_data.clear()
        await update.message.reply_text("✅ Karta yangilandi", reply_markup=admin_menu())

# ================= PASSPORT =================
async def passport(update: Update, context):
    if "room" not in context.user_data:
        return
    file_id = update.message.photo[-1].file_id
    cur.execute("""
    INSERT INTO users(tg_id, fullname, phone, passport, room, days, total, end_date)
    VALUES (?,?,?,?,?,?,?,?)
    """, (
        update.effective_user.id,
        context.user_data["fullname"],
        context.user_data["phone"],
        file_id,
        context.user_data["room"],
        0, 0, None
    ))
    conn.commit()
    cur.execute("SELECT card FROM settings WHERE id=1")
    card = cur.fetchone()[0]
    await update.message.reply_text(
        f"✅ Ro‘yxatdan o‘tdingiz\n💳 Karta: {card}\nAdmin to‘lov kunini belgilaydi."
    )
    context.user_data.clear()

# ================= ADMIN USER =================
async def admin_user(update: Update, context):
    q = update.callback_query
    await q.answer()
    uid = int(q.data.split("_")[1])
    context.user_data["uid"] = uid

    cur.execute("SELECT fullname, phone, passport, days, total, end_date FROM users WHERE id=?", (uid,))
    u = cur.fetchone()

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kun / Summa qo‘shish", callback_data="add")],
        [InlineKeyboardButton("🗑 O‘chirish", callback_data="del")],
        [InlineKeyboardButton("⬅️ Ortga", callback_data="back")]
    ])

    await context.bot.send_photo(
        ADMIN_ID,
        u[2],
        caption=(
            f"👤 {u[0]}\n📞 {u[1]}\n"
            f"⏳ {u[3]} kun\n💰 {u[4]} so‘m\n📅 {u[5]}"
        ),
        reply_markup=kb
    )

# ================= ADMIN ACTIONS =================
async def admin_actions(update: Update, context):
    q = update.callback_query
    await q.answer()

    if q.data == "rooms":
        await q.message.reply_text("Xonani tanlang:", reply_markup=rooms_kb())

    elif q.data == "add":
        context.user_data["add_days"] = True
        await q.message.reply_text("Necha kun qo‘shamiz?")

    elif q.data == "del":
        uid = context.user_data.get("uid")
        cur.execute("DELETE FROM users WHERE id=?", (uid,))
        conn.commit()
        await q.message.reply_text("🗑 O‘chirildi", reply_markup=admin_menu())

    elif q.data == "card":
        context.user_data["change_card"] = True
        await q.message.reply_text("Yangi karta raqamini yuboring:")

    elif q.data == "check":
        today = datetime.date.today()
        cur.execute("SELECT tg_id, fullname, end_date FROM users WHERE end_date IS NOT NULL")
        for tg_id, name, end in cur.fetchall():
            left = (datetime.date.fromisoformat(end) - today).days
            if left <= 3:
                cur.execute("SELECT card FROM settings WHERE id=1")
                card = cur.fetchone()[0]
                msg = f"⏰ {name}\nTo‘lov tugashiga {left} kun qoldi\n💳 {card}"
                await context.bot.send_message(ADMIN_ID, msg)
                await context.bot.send_message(tg_id, msg)
        await q.message.reply_text("🔍 Tekshirildi", reply_markup=admin_menu())

    elif q.data == "back":
        await q.message.reply_text("Admin panel", reply_markup=admin_menu())

# ================= MAIN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(room, pattern="room_"))
app.add_handler(CallbackQueryHandler(admin_user, pattern="user_"))
app.add_handler(CallbackQueryHandler(admin_actions))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
app.add_handler(MessageHandler(filters.PHOTO, passport))

print("BOT ISHLAYAPTI (YARIM-AVTO)")
app.run_polling()
