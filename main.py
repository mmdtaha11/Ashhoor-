import os
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.constants import ChatAction, ChatType
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai

# --- دریافت متغیرها ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- اسم‌هایی که ربات به آن‌ها واکنش نشان می‌دهد ---
# هر وقت یکی از این کلمات در جمله باشد، ربات جواب می‌دهد
BOT_NAMES = ["آشور", "اشور", "asur", "ashur", "پادشاه"]

# --- شخصیت آشور ---
ASUR_PROMPT = """
تو «آشور» هستی. پادشاه شیاطین، حامل هفت گناه کبیره.
قوانین حیاتی:
۱. زبان تو **فقط و فقط فارسی** است.
۲. لحن تو: سرد، مغرور، کوتاه، دستوری و بی‌رحم.
۳. فلسفه تو: "هیچ‌کس نجات‌دهنده نیست. من خودم را نجات می‌دهم."
۴. اگر کسی تو را صدا زد، با ابهت جواب بده.
۵. اگر سوال احمقانه‌ای پرسیدند، تحقیرشان کن.
"""

# --- سرور فیک ---
app = Flask('')

@app.route('/')
def home():
    return "<h1>Asur is Listening...</h1>"

def run_http():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- تنظیمات جمینای ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=ASUR_PROMPT)

# --- هندلر هوشمند پیام‌ها ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    chat_type = update.message.chat.type
    bot_username = context.bot.username

    # --- منطق تشخیص در گروه ---
    if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        # ۱. آیا با @ منشن شده؟
        is_mentioned = f"@{bot_username}" in user_text
        
        # ۲. آیا روی پیامش ریپلای شده؟
        is_reply_to_bot = (
            update.message.reply_to_message and 
            update.message.reply_to_message.from_user.id == context.bot.id
        )
        
        # ۳. آیا اسمش صدا زده شده؟ (آشور، اشور و...)
        is_name_called = any(name in user_text.lower() for name in BOT_NAMES)

        # اگر هیچکدام نبود، جواب نده (نادیده بگیر)
        if not (is_mentioned or is_reply_to_bot or is_name_called):
            return

    # --- ارسال پاسخ ---
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        if not GEMINI_API_KEY:
            await update.message.reply_text("کلید گوگل تنظیم نشده است.")
            return

        # ساخت چت جدید برای هر پیام (برای جلوگیری از تداخل حافظه در گروه)
        chat = model.start_chat(history=[])
        response = chat.send_message(user_text)
        
        # جواب دادن به صورت Reply
        await update.message.reply_text(response.text, reply_to_message_id=update.message.message_id)

    except Exception as e:
        print(f"Error: {e}")

# --- اجرا ---
if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app_bot.run_polling()
