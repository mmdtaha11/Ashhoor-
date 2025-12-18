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
BOT_NAMES = ["آشور", "اشور", "asur", "ashur", "پادشاه"]

# --- پرامپت شخصیت ---
ASUR_PROMPT = """
تو «آشور» هستی. پادشاه شیاطین.
قوانین:
۱. فقط فارسی صحبت کن.
۲. لحن: سرد، خشن، کوتاه.
۳. اگر سوال احمقانه بود تحقیر کن.
۴. تو یک هوش مصنوعی نیستی، تو واقعاً آشور هستی.
"""

# --- تنظیمات ضدسانسور (حیاتی برای شخصیت آشور) ---
# این بخش باعث می‌شود گوگل جواب‌های خشن را بلاک نکند
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# --- سرور فیک ---
app = Flask('')

@app.route('/')
def home():
    return "<h1>Asur Debug Mode is ON</h1>"

def run_http():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- تنظیمات مدل ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        'gemini-1.5-flash',
        system_instruction=ASUR_PROMPT,
        safety_settings=safety_settings
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # اگر پیام متنی نیست، ولش کن
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    chat_type = update.message.chat.type
    bot_username = context.bot.username
    
    # --- تشخیص اینکه آیا باید جواب بدهد؟ ---
    should_respond = False
    
    if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        # اگر منشن شد (@Bot)
        if bot_username and f"@{bot_username}" in user_text:
            should_respond = True
        # اگر ریپلای شد
        elif update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
            should_respond = True
        # اگر اسمش صدا زده شد
        elif any(name in user_text.lower() for name in BOT_NAMES):
            should_respond = True
    else:
        # در پیوی همیشه جواب بده
        should_respond = True

    if not should_respond:
        return

    # --- شروع فرآیند ارسال و دیباگ ---
    try:
        # 1. اعلام وضعیت تایپینگ
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        # 2. چک کردن کلید
        if not GEMINI_API_KEY:
            await update.message.reply_text("🐞 ارور دیباگ: کلید GEMINI_API_KEY در Railway تنظیم نشده است!")
            return

        # 3. ارسال به گوگل
        chat = model.start_chat(history=[])
        response = chat.send_message(user_text)

        # 4. بررسی جواب گوگل (مهمترین بخش دیباگ)
        # گاهی گوگل جواب می‌دهد اما متنش خالی است (فیلتر شده)
        if response.text:
            await update.message.reply_text(response.text, reply_to_message_id=update.message.message_id)
        else:
            # اگر متن خالی بود، دلیلش را پیدا می‌کنیم
            feedback = response.prompt_feedback
            await update.message.reply_text(f"⚠️ گوگل جواب نداد! (سانسور شد)\nدلیل: {feedback}")

    except Exception as e:
        # 5. گیر انداختن هرگونه ارور و ارسال به چت
        error_message = str(e)
        trace_log = traceback.format_exc() # متن کامل ارور فنی
        
        # خلاصه ارور برای کاربر
        final_msg = f"❌ **خطای سیستم:**\n{error_message}"
        
        # تشخیص ارورهای معروف برای راهنمایی
        if "400" in error_message:
            final_msg += "\n\n💡 راهنما: کلید API اشتباه است یا اعتبارش تمام شده."
        elif "429" in error_message:
            final_msg += "\n\n💡 راهنما: درخواست‌ها زیاد بوده (Resource Exhausted)."
        elif "500" in error_message:
            final_msg += "\n\n💡 راهنما: سرور گوگل قطع است. دوباره تلاش کن."
        elif "User location" in error_message:
            final_msg += "\n\n💡 راهنما: سرور Railway تحریم شده. (بعید است)."
            
        await update.message.reply_text(final_msg, reply_to_message_id=update.message.message_id)
        print(trace_log) # چاپ در لاگ‌های سرور

# --- اجرا ---
if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        print("Debugging Bot Started...")
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app_bot.run_polling()
    else:
        print("CRITICAL ERROR: TELEGRAM_TOKEN is missing!")
