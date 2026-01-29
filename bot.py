from telegram import *
from telegram.ext import *
import sqlite3
import os

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

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
    status TEXT
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

def rooms_kb():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"Xona {i}", callback_data=f"room_{i}")]
         for i in range(1, 25)]
    )

def admin_check_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data="ok"),
            InlineKeyboardButton("❌ Soxta", callback_data="fake")
        ]
    ])

async def start(update: Update, context):
    context.user_data.clear()
    await update.message.reply_text("🏨 Xonani tanlang (1–24):", reply_markup=rooms_kb())

async def room(update: Update, context):
    q = update.callback_query
    await q.answer()
    room = int(q.data.split("_")[1])
    cur.execute("SELECT COUNT(*) FROM users WHERE room=?", (room,))
    if cur.fetchone()[0] >= 6:
        await q.message.reply_text("❌ Bu xona to‘la (6/6)")
        return
    context.user_data["room"] = room
    await q.message.reply_text("👤 Ism Familiya Sharifingizni yozing:")

async def text(update: Update, context):
    if "fullname" not in context.user_data:
        context.user_data["fullname"] = update.message.text
        await update.message.reply_text("📞 Telefon raqamingizni yozing:")
    elif "phone" not in context.user_data:
        context.user_data["phone"] = update.message.text
        await update.message.reply_text("🪪 Passport rasmini yuboring:")

async def passport(update: Update, context):
    file_id = update.message.photo[-1].file_id
    cur.execute("""
    INSERT INTO users(tg_id, fullname, phone, passport, room, status)
    VALUES(?,?,?,?,?,?)
    """, (
        update.effective_user.id,
        context.user_data["fullname"],
        context.user_data["phone"],
        file_id,
        context.user_data["room"],
        "pending"
    ))
    conn.commit()

    await context.bot.send_photo(
        ADMIN_ID,
        file_id,
        caption=f"🆕 YANGI REGISTRATSIYA\n👤 {context.user_data['fullname']}\n📞 {context.user_data['phone']}\n🏨 Xona {context.user_data['room']}"
    )

    cur.execute("SELECT card FROM settings WHERE id=1")
    card = cur.fetchone()[0]
    await update.message.reply_text(f"💳 To‘lov kartasi:\n{card}\n\n📸 Chekni yuboring.")

async def check(update: Update, context):
    await context.bot.send_photo(
        ADMIN_ID,
        update.message.photo[-1].file_id,
        caption="💰 TO‘LOV CHEKI",
        reply_markup=admin_check_kb()
    )

async def admin_action(update: Update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "ok":
        await q.message.reply_text("✅ To‘lov tasdiqlandi")
    elif q.data == "fake":
        await q.message.reply_text("❌ To‘lov soxta deb belgilandi")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(room, pattern="room_"))
app.add_handler(CallbackQueryHandler(admin_action))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
app.add_handler(MessageHandler(filters.PHOTO, passport))
app.add_handler(MessageHandler(filters.PHOTO, check))

print("✅ Bot Render’da ishlayapti...")
app.run_polling()
