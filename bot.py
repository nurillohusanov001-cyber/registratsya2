from telegram import *
from telegram.ext import *
import sqlite3, os, datetime

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ===== DB =====
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

# ===== HELPERS =====
def rate(days):
    if days <= 10:
        return 50000
    if days <= 20:
        return 40000
    if days == 30:
        return 1000000 // 30
    return 40000

def rooms_kb():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"Xona {i}", callback_data=f"room_{i}")]
         for i in range(1,25)]
    )

def back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data="back")]])

def admin_user_kb(uid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Summa/Kun qo‘shish", callback_data=f"add_{uid}")],
        [InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"edit_{uid}")],
        [InlineKeyboardButton("🗑 O‘chirish", callback_data=f"del_{uid}")],
        [InlineKeyboardButton("⬅️ Ortga", callback_data="back")]
    ])

# ===== START =====
async def start(update: Update, context):
    context.user_data.clear()
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("🛠 ADMIN PANEL\nXonani tanlang:", reply_markup=rooms_kb())
    else:
        await update.message.reply_text("🏨 Qaysi xonaga joylashyapsiz?", reply_markup=rooms_kb())

# ===== ROOM =====
async def room(update: Update, context):
    q = update.callback_query
    await q.answer()
    room = int(q.data.split("_")[1])

    # ADMIN
    if update.effective_user.id == ADMIN_ID:
        cur.execute("SELECT id,fullname FROM users WHERE room=?", (room,))
        rows = cur.fetchall()
        if not rows:
            await q.message.reply_text("Bu xonada odam yo‘q", reply_markup=back_kb())
            return
        kb = [[InlineKeyboardButton(n, callback_data=f"user_{i}")] for i,n in rows]
        kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data="back")])
        await q.message.reply_text(f"🏨 Xona {room}", reply_markup=InlineKeyboardMarkup(kb))
        return

    # KLIENT
    context.user_data["room"] = room
    await q.message.reply_text("Ism Familiyangizni yozing:")

# ===== TEXT (KLIENT REG) =====
async def text(update: Update, context):
    if "room" in context.user_data:
        if "fullname" not in context.user_data:
            context.user_data["fullname"] = update.message.text
            await update.message.reply_text("Telefon raqamingiz:")
        elif "phone" not in context.user_data:
            context.user_data["phone"] = update.message.text
            await update.message.reply_text("Passport rasmini yuboring:")
        return

    # ADMIN ADD DAYS
    if context.user_data.get("add_days"):
        days = int(update.message.text)
        uid = context.user_data["uid"]
        r = rate(days)
        total = 1000000 if days==30 else days*r
        end = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
        cur.execute("UPDATE users SET days=?, total=?, end_date=? WHERE id=?",
                    (days, total, end, uid))
        conn.commit()
        await update.message.reply_text(f"💰 Hisob: {total} so‘m\n📅 Tugash: {end}")
        context.user_data.clear()
        return

    # ADMIN CHANGE CARD
    if context.user_data.get("change_card"):
        cur.execute("UPDATE settings SET card=? WHERE id=1", (update.message.text,))
        conn.commit()
        context.user_data.clear()
        await update.message.reply_text("✅ Karta yangilandi", reply_markup=rooms_kb())

# ===== PASSPORT =====
async def passport(update: Update, context):
    if "room" not in context.user_data:
        return
    file_id = update.message.photo[-1].file_id
    cur.execute("""
    INSERT INTO users(tg_id,fullname,phone,passport,room,days,total,end_date)
    VALUES(?,?,?,?,?,?,?,?)
    """, (update.effective_user.id,
          context.user_data["fullname"],
          context.user_data["phone"],
          file_id,
          context.user_data["room"],
          0, 0, None))
    conn.commit()
    cur.execute("SELECT card FROM settings WHERE id=1")
    card = cur.fetchone()[0]
    await update.message.reply_text(f"✅ Ro‘yxatdan o‘tdingiz\n💳 Karta: {card}")
    context.user_data.clear()

# ===== ADMIN USER =====
async def admin_user(update: Update, context):
    q = update.callback_query
    await q.answer()
    uid = int(q.data.split("_")[1])
    context.user_data["uid"] = uid
    cur.execute("SELECT fullname,phone,passport,days,total,end_date FROM users WHERE id=?", (uid,))
    u = cur.fetchone()
    txt = (f"👤 {u[0]}\n📞 {u[1]}\n"
           f"⏳ Kun: {u[3]}\n💰 {u[4]} so‘m\n📅 {u[5]}")
    await context.bot.send_photo(ADMIN_ID, u[2], caption=txt, reply_markup=admin_user_kb(uid))

# ===== ADMIN ACTIONS =====
async def admin_actions(update: Update, context):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "back":
        await q.message.reply_text("Admin panel", reply_markup=rooms_kb())
        return

    if data.startswith("add_"):
        uid = int(data.split("_")[1])
        context.user_data["uid"] = uid
        context.user_data["add_days"] = True
        await q.message.reply_text("Necha kun qo‘shamiz?")
        return

    if data.startswith("del_"):
        uid = int(data.split("_")[1])
        cur.execute("DELETE FROM users WHERE id=?", (uid,))
        conn.commit()
        await q.message.reply_text("🗑 O‘chirildi", reply_markup=rooms_kb())
        return

# ===== JOB: 3 KUN QOLGANDA =====
async def notify_job(context: ContextTypes.DEFAULT_TYPE):
    today = datetime.date.today()
    cur.execute("SELECT tg_id,fullname,end_date FROM users WHERE end_date IS NOT NULL")
    for tg_id, name, end in cur.fetchall():
        left = (datetime.date.fromisoformat(end) - today).days
        if left == 3:
            cur.execute("SELECT card FROM settings WHERE id=1")
            card = cur.fetchone()[0]
            msg = f"⏰ {name}\n3 kun qoldi\n💳 Karta: {card}"
            await context.bot.send_message(ADMIN_ID, msg)
            await context.bot.send_message(tg_id, msg)

# ===== WEEKLY REPORT =====
async def weekly_report(context):
    cur.execute("SELECT SUM(total) FROM users")
    s = cur.fetchone()[0] or 0
    await context.bot.send_message(ADMIN_ID, f"📊 Haftalik yig‘im: {s} so‘m")

# ===== MAIN =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(room, pattern="room_"))
app.add_handler(CallbackQueryHandler(admin_user, pattern="user_"))
app.add_handler(CallbackQueryHandler(admin_actions))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
app.add_handler(MessageHandler(filters.PHOTO, passport))

# jobs
app.job_queue.run_repeating(notify_job, interval=86400, first=10)
app.job_queue.run_repeating(weekly_report, interval=7*86400, first=20)

print("BOT ISHLAYAPTI")
app.run_polling()

