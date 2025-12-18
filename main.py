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

# --- شخصیت آشور ---
ASUR_PROMPT = """
تو «آشور» هستی. پادشاه شیاطین، حامل هفت گناه کبیره.
قوانین حیاتی:
۱. زبان تو **فقط و فقط فارسی** است.
۲. لحن تو: سرد، مغرور، کوتاه، دستوری و بی‌رحم.
۳. در گروه‌ها فقط وقتی صحبت کن که مستقیم با تو حرف می‌زنند.
۴. فلسفه تو: "هیچ‌کس نجات‌دهنده نیست. من خودم را نجات می‌دهم."
۵. سلاح تو دو تبر کوچک است. بزرگترین زخمت کشتن معشوقه خیانتکارت است.
۶. اگر سوال احمقانه‌ای پرسیدند، تحقیرشان کن.
"""

# --- سرور فیک (برای جلوگیری از خاموشی در Railway) ---
app = Flask('')

@app.route('/')
def home():
    return "<h1>Asur is Watching the Group...</h1>"

def run_http():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- تنظیمات هوش مصنوعی ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        'gemini-1.5-flash',
        system_instruction=ASUR_PROMPT
    )
    # نکته: در گروه‌ها حافظه مشترک ممکنه گیج‌کننده بشه، پس برای هر بار چت جدید می‌سازیم
    # یا می‌تونیم یک دیکشنری برای حافظه هر گروه بسازیم. فعلاً ساده‌ترین حالت:

# --- هندلر هوشمند پیام‌ها ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    chat_type = update.message.chat.type
    bot_username = context.bot.username  # نام کاربری ربات (بدون @)

    # --- فیلتر کردن پیام‌های گروه ---
    # اگر پیام در گروه بود، باید بررسی کنیم که آیا ربات مخاطب هست یا نه
    if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        is_mentioned = f"@{bot_username}" in user_text
        is_reply_to_bot = (
            update.message.reply_to_message and 
            update.message.reply_to_message.from_user.id == context.bot.id
        )
        
        # اگر نه منشن شده بود و نه ریپلای، نادیده بگیر (جواب نده)
        if not (is_mentioned or is_reply_to_bot):
            return

    # --- ارسال پاسخ ---
    try:
        # نمایش وضعیت تایپینگ (برای حس زنده بودن)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        if not GEMINI_API_KEY:
            await update.message.reply_text("کلید گوگل تنظیم نشده است.")
            return

        # راه‌اندازی چت (بدون حافظه طولانی مدت برای جلوگیری از قاطی کردن در گروه)
        chat = model.start_chat(history=[])
        response = chat.send_message(user_text)
        
        # ارسال جواب (Reply کردن روی پیام کاربر)
        await update.message.reply_text(response.text, reply_to_message_id=update.message.message_id)

    except Exception as e:
        # در گروه معمولاً ارورها را نمی‌فرستیم که اسپم نشود، اما برای تست می‌گذاریم
        print(f"Error: {e}")

# --- اجرای ربات ---
if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        print("Asur is Ready for Groups...")
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        # هندلر را روی همه پیام‌های متنی می‌گذاریم، ولی داخل تابع فیلتر می‌کنیم
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app_bot.run_polling()
