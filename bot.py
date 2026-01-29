from telegram import *
from telegram.ext import *
import sqlite3, os, datetime

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

def rooms():
 return InlineKeyboardMarkup([[InlineKeyboardButton(f"Xona {i}",callback_data=f"room_{i}")] for i in range(1,25)])

def back():
 return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga",callback_data="back")]])

async def start(update:Update,context):
 if update.effective_user.id==ADMIN_ID:
  await update.message.reply_text("Admin panel",reply_markup=rooms())
 else:
  await update.message.reply_text("Bot faqat admin uchun")

async def admin_room(update:Update,context):
 q=update.callback_query;await q.answer()
 room=int(q.data.split("_")[1])
 cur.execute("SELECT id,fullname FROM users WHERE room=?",(room,))
 kb=[[InlineKeyboardButton(n,callback_data=f"user_{i}")] for i,n in cur.fetchall()]
 kb.append([InlineKeyboardButton("⬅️ Ortga",callback_data="back")])
 await q.message.reply_text(f"Xona {room}",reply_markup=InlineKeyboardMarkup(kb))

async def admin_user(update:Update,context):
 q=update.callback_query;await q.answer()
 uid=int(q.data.split("_")[1])
 context.user_data["uid"]=uid
 cur.execute("SELECT fullname,phone,days,total,end_date FROM users WHERE id=?",(uid,))
 u=cur.fetchone()
 await q.message.reply_text(
 f"👤 {u[0]}\n📞 {u[1]}\n⏳ {u[2]} kun\n💰 {u[3]} so'm\n📅 {u[4]}",
 reply_markup=InlineKeyboardMarkup([
  [InlineKeyboardButton("➕ Kun qo‘shish",callback_data="add_days")],
  [InlineKeyboardButton("⬅️ Ortga",callback_data="back")]
 ]))

async def add_days(update:Update,context):
 q=update.callback_query;await q.answer()
 context.user_data["add_days"]=True
 await q.message.reply_text("Necha kun qo‘shamiz?")

async def text(update:Update,context):
 if context.user_data.get("add_days"):
  days=int(update.message.text)
  uid=context.user_data["uid"]
  if days<10: rate=50000
  elif days<30: rate=40000
  else: rate=1000000//30
  total=days*rate
  end=(datetime.date.today()+datetime.timedelta(days=days)).isoformat()
  cur.execute("UPDATE users SET days=?,total=?,end_date=? WHERE id=?",(days,total,end,uid))
  conn.commit()
  await update.message.reply_text(f"💰 Hisob: {total} so'm\n📅 Tugash: {end}")
  context.user_data.clear()

async def back_btn(update:Update,context):
 await update.callback_query.answer()
 await update.callback_query.message.reply_text("Admin panel",reply_markup=rooms())

app=ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start",start))
app.add_handler(CallbackQueryHandler(admin_room,pattern="room_"))
app.add_handler(CallbackQueryHandler(admin_user,pattern="user_"))
app.add_handler(CallbackQueryHandler(add_days,pattern="add_days"))
app.add_handler(CallbackQueryHandler(back_btn,pattern="back"))
app.add_handler(MessageHandler(filters.TEXT,text))

print("ADVANCED ADMIN BOT ISHLAYAPTI")
app.run_polling()

