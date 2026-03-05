import telebot
from telebot import types
import os
import json

# ================= CONFIG =================
TOKEN = "8793531639:AAEUjZ0fYeiEAMLPH_CdtXH2-duP8dd8Czs"
ADMIN_IDS = [5833044094]  # <-- Tomar telegram ID
bot = telebot.TeleBot(TOKEN)

user_step = {}
forward_data = {}

ID_FILE = "submit_id.txt"
DATA_FILE = "submit_history.json"

# ================= AUTO ID =================
def get_next_id():
    if not os.path.exists(ID_FILE):
        with open(ID_FILE, "w") as f:
            f.write("92050")
    with open(ID_FILE, "r") as f:
        current_id = int(f.read())
    new_id = current_id + 1
    with open(ID_FILE, "w") as f:
        f.write(str(new_id))
    return new_id

# ================= DATA LOAD/SAVE =================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= START / MAIN MENU =================
def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Submit Statistics", "Account", "Paid IDs")
    bot.send_message(chat_id, "Welcome Boss 👑", reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(message):
    show_main_menu(message.chat.id)

# ================= ACCOUNT BUTTON =================
@bot.message_handler(func=lambda m: m.text == "Account")
def account_history(message):
    user_id = str(message.from_user.id)
    data = load_data()
    if user_id not in data or len(data[user_id]) == 0:
        bot.send_message(message.chat.id, "❌ No submission history found.")
        return
    total = len(data[user_id])
    text = f"📂 Your Total Submitted Accounts: {total}\n"
    for item in data[user_id]:
        wallet = item.get('wallet', 'None')
        payment_method = item.get('payment_method', 'None')
        payment_info = item.get('payment_info', 'None')
        status = item.get('status', 'Pending')
        text += f"ID: {item['id']} Wallet: {wallet} | Method: {payment_method} | Info: {payment_info} | Status: {status}\n"
    bot.send_message(message.chat.id, text)

# ================= PAID IDS BUTTON =================
@bot.message_handler(func=lambda m: m.text == "Paid IDs")
def paid_ids(message):
    user_id = str(message.from_user.id)
    data = load_data()
    if user_id not in data:
        bot.send_message(message.chat.id, "❌ You have no submissions yet.")
        return
    paid = [str(item['id']) for item in data[user_id] if item.get('status') == "Paid"]
    if not paid:
        bot.send_message(message.chat.id, "❌ You have no paid submissions yet.")
        return
    bot.send_message(message.chat.id, f"🥳 You have been PAID for IDs: {', '.join(paid)}")

# ================= SUBMIT STATISTICS BUTTON =================
@bot.message_handler(func=lambda m: m.text == "Submit Statistics")
def submit_statistics(message):
    user_step[message.from_user.id] = 1
    bot.send_message(message.chat.id,
        "🫶 Well done! Please forward the user account information from the receiver robot 👇"
    )

# ================= HANDLE FORWARD + PHOTO + PAYMENT =================
@bot.message_handler(content_types=['text', 'photo'])
def handle_all(message):
    user_id = message.from_user.id
    step = user_step.get(user_id, 0)

    # STEP 1: Forward detect
    if step == 1 and message.forward_from:
        forward_data[user_id] = {
            "original_text": message.text,
            "photo_id": None,
            "wallet": "None",
            "payment_method": None,
            "payment_info": None
        }
        user_step[user_id] = 2
        bot.send_message(message.chat.id, "📸 Now send your withdraw submit photo with card name")

    # STEP 2: Photo detect
    elif step == 2 and message.content_type == "photo":
        forward_data[user_id]['photo_id'] = message.photo[-1].file_id
        user_step[user_id] = 3
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("1️⃣ Nagod", "2️⃣ BEP20 USDT")
        bot.send_message(message.chat.id,
            "💸 Please choose your preferred payment method:\n1️⃣ Nagod Number\n2️⃣ BEP20 USDT Wallet Address",
            reply_markup=markup
        )

    # STEP 3: Payment method choose
    elif step == 3 and message.text in ["1️⃣ Nagod", "2️⃣ BEP20 USDT"]:
        forward_data[user_id]['payment_method'] = "Nagad" if message.text == "1️⃣ Nagod" else "BEP20 USDT"
        user_step[user_id] = 4
        bot.send_message(message.chat.id,
            f"✅ You chose {forward_data[user_id]['payment_method']}. Please enter your {forward_data[user_id]['payment_method']} info:",
            reply_markup=types.ReplyKeyboardRemove()
        )

    # STEP 4: Payment info input
    elif step == 4:
        forward_data[user_id]['payment_info'] = message.text
        submit_id = get_next_id()
        data = load_data()
        uid = str(user_id)
        if uid not in data:
