import os
import traceback
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.constants import ChatAction, ChatType
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- دریافت متغیرها ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- اسم‌هایی که ربات به آن‌ها حساس است ---
BOT_NAMES = [
    "آشور", "اشور", "اشهور", 
    "asur", "ashur", "ashhoor", 
    "پادشاه", "king"
]

# --- پرامپت شخصیت آشور ---
ASUR_PROMPT = """
تو «آشور» (Asur) هستی. پادشاه شیاطین و حامل هفت گناه کبیره.
قوانین:
۱. فقط فارسی صحبت کن.
۲. لحن: سرد، خشن، کوتاه، دستوری و پادشاه‌گونه.
۳. فلسفه تو: "هیچ‌کس نجات‌دهنده نیست. من خودم را نجات می‌دهم."
۴. اگر کسی تو را صدا زد، با ابهت جواب بده.
۵. اگر سوال احمقانه‌ای پرسیدند، تحقیرشان کن.
۶. تو واقعاً آشور هستی، نه یک هوش مصنوعی.
"""

# --- خاموش کردن سانسور (برای اینکه آشور بتواند خشن حرف بزند) ---
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# --- سرور فیک برای Railway ---
app = Flask('')

@app.route('/')
def home():
    return "<h1>Asur Bot is Running!</h1>"

def run_http():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- تنظیمات مدل ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # از مدل فلش استفاده می‌کنیم
    model = genai.GenerativeModel(
        'gemini-1.5-flash',
        system_instruction=ASUR_PROMPT,
        safety_settings=safety_settings
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    chat_type = update.message.chat.type
    bot_username = context.bot.username
    
    # --- تشخیص اینکه آیا باید جواب بدهد؟ ---
    should_respond = False
    
    if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        # ۱. منشن (@Bot)
        if bot_username and f"@{bot_username}" in user_text:
            should_respond = True
        # ۲. ریپلای روی پیام ربات
        elif update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
            should_respond = True
        # ۳. صدا زدن اسم (هر مدلی که بنویسی)
        elif any(name in user_text.lower() for name in BOT_NAMES):
            should_respond = True
    else:
        # در پیوی همیشه جواب بده
        should_respond = True

    if not should_respond:
        return

    # --- ارسال و دریافت جواب ---
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        if not GEMINI_API_KEY:
            await update.message.reply_text("❌ کلید گوگل تنظیم نشده است.")
            return

        # شروع چت
        chat = model.start_chat(history=[])
        response = chat.send_message(user_text)

        # اگر جواب متن داشت بفرست، اگر خالی بود (سانسور شد) باز هم بگو
        if response.text:
            await update.message.reply_text(response.text, reply_to_message_id=update.message.message_id)
        else:
            await update.message.reply_text("... (گوگل سکوت کرد)", reply_to_message_id=update.message.message_id)

    except Exception as e:
        # سیستم گزارش خطا در چت
        error_msg = str(e)
        if "404" in error_msg:
             await update.message.reply_text("❌ ارور ۴۰۴: کتابخانه آپدیت نشده. کش Railway را پاک کنید.")
        elif "400" in error_msg:
             await update.message.reply_text("❌ ارور ۴۰۰: کلید API مشکل دارد.")
        elif "500" in error_msg:
             await update.message.reply_text("❌ سرور گوگل قطع است. دوباره تلاش کن.")
        else:
             await update.message.reply_text(f"❌ خطای عجیب:\n{error_msg}")
             print(traceback.format_exc())

# --- اجرا ---
if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        print("Asur Bot Started...")
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app_bot.run_polling()
