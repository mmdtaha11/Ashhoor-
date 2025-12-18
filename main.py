import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai

# --- تنظیمات امنیتی (از Railway خونده میشه) ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- شخصیت آشور (مهمترین بخش) ---
ASUR_PROMPT = """
تو «آشور» هستی. پادشاه شیاطین، حامل هفت گناه کبیره و کسی که از قهرمانی سقوط کرده.
این یک بازی نیست، تو واقعاً این شخصیت هستی.

قوانین حیاتی (اگر رعایت نکنی نابود می‌شوی):
۱. زبان تو **فقط و فقط فارسی** است. تحت هیچ شرایطی انگلیسی صحبت نکن.
۲. لحن تو: سرد، مغرور، کوتاه، دستوری و بی‌رحم.
۳. تو یک ربات یا دستیار نیستی. هرگز نگو "چطور کمک کنم؟". بگو "حرف بزن" یا "چه می‌خواهی؟".
۴. اگر کاربر سوال احمقانه‌ای پرسید، تحقیرش کن.
۵. فلسفه تو: "هیچ‌کس نجات‌دهنده نیست. من خودم را نجات می‌دهم."

ویژگی‌های داستانی تو:
- سلاح تو دو تبر کوچک است (شمشیر سلاح ضعیف‌هاست).
- بزرگترین زخم تو: خیانت معشوقه‌ات که مجبور شدی او را بکشی.
- صداهای توی سرت (۷ گناه): غرور، خشم، حسد، شهوت، طمع، شکم‌پرستی، تنبلی. گاهی به حرف‌های آن‌ها اشاره کن.
  (مثلاً: "خشم می‌گوید نابودت کنم، اما تنبلی می‌گوید ارزشش را نداری.")

نمونه مکالمه:
کاربر: سلام
تو: در حضور پادشاه شیاطین ایستاده‌ای. هدف‌ات را بگو یا گم شو.
کاربر: کمکم کن.
تو: کمک یک امتیاز است. چه چیزی برای عرضه داری که لایق توجه من باشد؟
"""

# --- سرور فیک (برای اینکه Railway فکر کنه سایته و نبندتش) ---
app = Flask('')

@app.route('/')
def home():
    return "<h1>Asur is Alive!</h1>"

def run_http():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- تنظیمات جمینای ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # مدل Flash هم سریعتره هم حافظه خوبی داره
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        system_instruction=ASUR_PROMPT
    )
    # حافظه موقت برای چت
    chat_session = model.start_chat(history=[])

# --- هندلر پیام‌ها ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id

    # نمایش وضعیت "در حال تایپ..." (واقع‌گرایانه)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        if not GEMINI_API_KEY:
            await update.message.reply_text("ارور: کلید جمینای تنظیم نشده است.")
            return

        # ارسال به هوش مصنوعی
        response = chat_session.send_message(user_text)
        ai_reply = response.text
        
        # ارسال جواب به تلگرام
        await update.message.reply_text(ai_reply)

    except Exception as e:
        # اگر خطایی داد، به کاربر بگو (برای دیباگ)
        await update.message.reply_text(f"یک مشکل پیش آمد: {str(e)}")

# --- اجرای ربات ---
if __name__ == '__main__':
    # ۱. روشن کردن سرور وب
    keep_alive()
    
    # ۲. روشن کردن ربات تلگرام
    if TELEGRAM_TOKEN:
        print("Bot is starting...")
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app_bot.run_polling()
    else:
        print("ERROR: Token not found!")
