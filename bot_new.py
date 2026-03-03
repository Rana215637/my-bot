import telebot
from telebot import types
import sqlite3
from datetime import datetime, timedelta
import threading
import time
import re

# ==============================
# CONFIG
# ==============================
API_TOKEN = "8252339095:AAHgBYEGslsOydqFYBlui3Ct1ro1adBcBho"
ADMIN_ID = 5833044094 # তোমার admin ID
NAGAD_NUMBER = "01741644253"

bot = telebot.TeleBot(API_TOKEN)

# ==============================
# DATABASE
# ==============================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    bonus_balance INTEGER DEFAULT 0,
    username TEXT,
    full_name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    start_time TEXT,
    next_bonus_time TEXT,
    trx_id TEXT,
    status TEXT DEFAULT 'pending'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS withdraws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    status TEXT
)
""")
conn.commit()

# ==============================
# MAIN MENU
# ==============================
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💰 Deposit", "💳 Balance")
    markup.row("🪪 Withdraw", "/📊 Total Income Summary 📊")
    return markup

# ==============================
# START
# ==============================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    full_name = message.from_user.first_name or "NoName"
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)", (user_id, username, full_name))
    conn.commit()
    bot.send_message(
        message.chat.id,
        "👋 Welcome!\n🎁 Withdraw only Daily Bonus\n💸 Daily Bonus based on deposits",
        reply_markup=main_menu()
    )

# ==============================
# DEPOSIT FLOW
# ==============================
@bot.message_handler(func=lambda m: m.text == "💰 Deposit")
def deposit(message):
    msg = bot.send_message(message.chat.id, "💰 Enter deposit amount (min 200৳):")
    bot.register_next_step_handler(msg, get_deposit_amount)

def get_deposit_amount(message):
    user_id = message.from_user.id
    try:
        amount = int(message.text)
        if amount < 200:
            bot.send_message(message.chat.id, "❌ Minimum deposit 200৳")
            return
    except:
        bot.send_message(message.chat.id, "❌ Enter valid number")
        return
    bot.send_message(
        message.chat.id,
        f"📲 Send {amount}৳ to Nagad number: {NAGAD_NUMBER}\nAfter payment, enter your TRX ID and tap Submit."
    )
    bot.register_next_step_handler(message, lambda m, amt=amount: get_trx_id(m, amt))

def get_trx_id(message, amount):
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    full_name = message.from_user.first_name or "NoName"
    trx_id = message.text.strip()

    # TRX ID validation (only allow alphanumeric, length 8-12)
    if not re.match(r'^[A-Za-z0-9]{8,12}$', trx_id):
        bot.send_message(user_id, "❌ Invalid TRX ID. Try again.")
        bot.register_next_step_handler(message, lambda m, amt=amount: get_trx_id(m, amt))
        return

    start_time = datetime.now()
    next_bonus = start_time + timedelta(days=1)
    cursor.execute("""
        INSERT INTO deposits (user_id, amount, start_time, next_bonus_time, trx_id, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    """, (
        user_id,
        amount,
        start_time.strftime("%Y-%m-%d %H:%M:%S"),
        next_bonus.strftime("%Y-%m-%d %H:%M:%S"),
        trx_id
    ))
    dep_id = cursor.lastrowid
    conn.commit()

    # Admin Inline Buttons
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_dep_{dep_id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_dep_{dep_id}")
    )

    bot.send_message(
        ADMIN_ID,
        f"💰 New Deposit\n\nUser ID: {user_id}\nFull Name: {full_name}\nUsername: @{username}\nAmount: {amount}৳\nTRX: {trx_id}\nDate/Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
        reply_markup=markup
    )
    bot.send_message(user_id, "⏳ Deposit request sent to admin", reply_markup=main_menu())

# ==============================
# ADMIN APPROVE / REJECT DEPOSIT
# ==============================
@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_dep_") or c.data.startswith("reject_dep_"))
def handle_deposit_approve(c):
    if c.from_user.id != ADMIN_ID:
        return
    dep_id = int(c.data.split("_")[-1])
    cursor.execute("SELECT user_id, amount, status, trx_id, start_time FROM deposits WHERE id=?", (dep_id,))
    row = cursor.fetchone()
    if not row:
        bot.answer_callback_query(c.id, "Deposit not found!")
        return
    user_id, amount, status, trx_id, start_time_str = row
    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    if c.data.startswith("approve_dep_"):
        cursor.execute("UPDATE deposits SET status='approved' WHERE id=?", (dep_id,))
        conn.commit()
        bot.edit_message_reply_markup(chat_id=c.message.chat.id, message_id=c.message.message_id, reply_markup=None)
        bot.send_message(user_id, "✅ Deposit Approved! You will receive daily bonuses.")
        bot.answer_callback_query(c.id, "Approved")
    elif c.data.startswith("reject_dep_"):
        cursor.execute("UPDATE deposits SET status='rejected' WHERE id=?", (dep_id,))
        conn.commit()
        bot.edit_message_reply_markup(chat_id=c.message.chat.id, message_id=c.message.message_id, reply_markup=None)
        bot.send_message(ADMIN_ID, f"❌ Deposit Rejected\n\nUser ID: {user_id}\nAmount: {amount}৳\nTRX: {trx_id}\nDate/Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        bot.send_message(user_id, "❌ Your deposit has been rejected.\nPrevious balance remains intact.")
        bot.answer_callback_query(c.id, "Rejected")

# ==============================
# DAILY BONUS PROCESS
# ==============================
def process_daily_bonus():
    cursor.execute("SELECT id, user_id, amount, next_bonus_time, status FROM deposits WHERE status='approved'")
    rows = cursor.fetchall()
    for dep_id, user_id, amount, next_time_str, status in rows:
        next_time = datetime.strptime(next_time_str, "%Y-%m-%d %H:%M:%S")
        if datetime.now() >= next_time:
            daily = 4 if amount == 200 else int(amount*0.01)
            cursor.execute("UPDATE users SET bonus_balance = bonus_balance + ? WHERE user_id=?", (daily, user_id))
            new_next = (next_time + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE deposits SET next_bonus_time=? WHERE id=?", (new_next, dep_id))
            conn.commit()
            cursor.execute("SELECT bonus_balance FROM users WHERE user_id=?", (user_id,))
            total_bonus = cursor.fetchone()[0]
            bot.send_message(user_id, f"🎉 Daily Bonus Added!\nDeposit {amount}৳ → +{daily}৳\nTotal bonus: {total_bonus}৳.")

# ==============================
# BALANCE CHECK
# ==============================
@bot.message_handler(func=lambda m: m.text == "💳 Balance")
def show_balance(msg):
    user_id = msg.from_user.id
    cursor.execute("SELECT bonus_balance FROM users WHERE user_id=?", (user_id,))
    bonus = cursor.fetchone()[0]
    cursor.execute("SELECT amount, start_time, next_bonus_time, status FROM deposits WHERE user_id=?", (user_id,))
    deps = cursor.fetchall()
    text = f"🎯 Bonus Balance: {bonus}৳\n\n📌 Deposits:\n"
    for amt, start, nxt, status in deps:
        nx = datetime.strptime(nxt, "%Y-%m-%d %H:%M:%S")
        rem = nx - datetime.now()
        days = rem.days
        hours = rem.seconds//3600
        minutes = (rem.seconds%3600)//60
        seconds = rem.seconds%60
        daily = 4 if amt==200 else int(amt*0.01)
        text += f"• {amt}৳ | {status} | deposited: {start} | next bonus {daily}৳ in {days}d {hours}h {minutes}m {seconds}s\n"
    bot.send_message(msg.chat.id, text)

# ==============================
# WITHDRAW
# ==============================
@bot.message_handler(func=lambda m: m.text == "🪪 Withdraw")
def withdraw(msg):
    sent = bot.send_message(msg.chat.id, "Enter amount to withdraw (min 20৳):")
    bot.register_next_step_handler(sent, process_withdraw)

def process_withdraw(msg):
    user_id = msg.from_user.id
    try:
        amt = int(msg.text)
    except:
        bot.send_message(msg.chat.id, "❌ Invalid amount")
        return
    cursor.execute("SELECT bonus_balance FROM users WHERE user_id=?", (user_id,))
    bal = cursor.fetchone()[0]
    if bal < 20 or amt > bal:
        bot.send_message(msg.chat.id, f"❌ Not enough bonus. Your balance: {bal}৳")
        return
    sent = bot.send_message(msg.chat.id, "💳 Enter your Nagad wallet number:")
    bot.register_next_step_handler(sent, lambda m, a=amt: finalize_withdraw(m, a))

def finalize_withdraw(msg, amt):
    user_id = msg.from_user.id
    wallet_number = msg.text
    cursor.execute("UPDATE users SET bonus_balance = bonus_balance - ? WHERE user_id=?", (amt, user_id))
    cursor.execute("INSERT INTO withdraws (user_id, amount, status) VALUES (?, ?, ?)", (user_id, amt, "pending"))
    conn.commit()
    cursor.execute("SELECT id FROM withdraws WHERE user_id=? AND amount=? AND status='pending' ORDER BY id DESC LIMIT 1", (user_id, amt))
    wid = cursor.fetchone()[0]

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Paid", callback_data=f"paid_w_{wid}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_w_{wid}")
    )

    bot.send_message(ADMIN_ID, f"💸 Withdraw Request\nUser ID: {user_id}\nAmount: {amt}৳\nWallet: {wallet_number}", reply_markup=markup)
    bot.send_message(msg.chat.id, f"✅ Withdraw request {amt}৳ sent to admin.", reply_markup=main_menu())

# ==============================
# ADMIN INLINE BUTTON FOR WITHDRAW
# ==============================
@bot.callback_query_handler(func=lambda c: c.data.startswith("paid_w_") or c.data.startswith("reject_w_"))
def handle_withdraw_buttons(c):
    if c.from_user.id != ADMIN_ID:
        return
    wid = int(c.data.split("_")[-1])
    cursor.execute("SELECT user_id, amount, status FROM withdraws WHERE id=?", (wid,))
    row = cursor.fetchone()
    if not row or row[2] != "pending":
        bot.answer_callback_query(c.id, "Already processed or invalid withdraw!")
        return
    user_id, amt, status = row
    if c.data.startswith("paid_w_"):
        cursor.execute("UPDATE withdraws SET status='paid' WHERE id=?", (wid,))
        conn.commit()
        bot.edit_message_reply_markup(chat_id=c.message.chat.id, message_id=c.message.message_id, reply_markup=None)
        bot.send_message(user_id, f"💸 Payment Done! Your withdraw amount {amt}৳ has been paid.")
        bot.answer_callback_query(c.id, "Paid")
    elif c.data.startswith("reject_w_"):
        cursor.execute("UPDATE withdraws SET status='rejected' WHERE id=?", (wid,))
        cursor.execute("UPDATE users SET bonus_balance = bonus_balance + ? WHERE user_id=?", (amt, user_id))
        conn.commit()
        bot.edit_message_reply_markup(chat_id=c.message.chat.id, message_id=c.message.message_id, reply_markup=None)
        bot.send_message(user_id, f"❌ Withdraw request rejected. Your bonus balance restored.")
        bot.answer_callback_query(c.id, "Rejected")

# ==============================
# ADMIN COMMAND TO ADD BALANCE
# ==============================
@bot.message_handler(commands=['add'])
def admin_add_balance(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        amount = int(parts[2])
    except:
        bot.reply_to(message, "Usage: /add <user_id> <amount>")
        return
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    cursor.execute("UPDATE users SET bonus_balance = bonus_balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    bot.reply_to(message, f"✅ Added {amount}৳ to user {user_id}")

# ==============================
# TOTAL INCOME SUMMARY
# ==============================
@bot.message_handler(func=lambda m: m.text == "/📊 Total Income Summary 📊")
def total_income_summary(msg):
    user_id = msg.from_user.id
    cursor.execute("SELECT SUM(amount) FROM deposits WHERE user_id=?", (user_id,))
    total_deposit = cursor.fetchone()[0] or 0
    cursor.execute("SELECT bonus_balance FROM users WHERE user_id=?", (user_id,))
    current_bonus = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(amount) FROM withdraws WHERE user_id=? AND status='paid'", (user_id,))
    withdraw_paid = cursor.fetchone()[0] or 0
    total_income = current_bonus + withdraw_paid

    text = f"Total Deposits: {total_deposit}৳\n💰 Current Bonus: {current_bonus}৳\n💸 Withdraw Paid: {withdraw_paid}৳\n🎯 Total Income: {total_income}৳"
    bot.send_message(msg.chat.id, text)

# ==============================
# DAILY BONUS THREAD
# ==============================
def run_bonus_checker():
    while True:
        process_daily_bonus()
        time.sleep(60)

threading.Thread(target=run_bonus_checker, daemon=True).start()

# ==============================
# RUN BOT
# ==============================
print("🔥 Full Deposit + Daily Bonus + Withdraw Bot Running...")
bot.infinity_polling()
