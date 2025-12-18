import os
import traceback
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.constants import ChatAction, ChatType
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- تنظیمات ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

BOT_NAMES = ["آشور", "اشور", "اشهور", "asur", "ashur", "پادشاه"]

ASUR_PROMPT = """
تو «آشور» (Asur) هستی. پادشاه شیاطین.
قوانین:
۱. فقط فارسی صحبت کن.
۲. لحن: سرد، خشن، کوتاه، دستوری.
۳. فلسفه: "هیچ‌کس نجات‌دهنده نیست. من خودم را نجات می‌دهم."
۴. هرگز نگو ربات هستی.
"""

# --- تنظیمات ایمنی (خاموش کردن سانسور) ---
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

app = Flask('')
@app.route('/')
def home(): return "<h1>Asur Final is Online</h1>"
def run_http(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
def keep_alive(): t = Thread(target=run_http); t.start()

# --- کانفیگ ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    # لاجیک جواب دادن در گروه
    should_respond = False
    if update.message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        if f"@{context.bot.username}" in update.message.text: should_respond = True
        elif update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id: should_respond = True
        elif any(n in update.message.text.lower() for n in BOT_NAMES): should_respond = True
    else: should_respond = True

    if not should_respond: return

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        # لیست مدل‌هایی که به ترتیب تست می‌کنیم
        # اگر اولی ارور داد، میره دومی، بعد سومی
        models_to_test = [
            'gemini-1.5-flash',       # جدیدترین و سریعترین
            'gemini-1.5-flash-latest',# شاید اسمش این باشه
            'gemini-1.0-pro',         # پایدارترین
            'gemini-pro'              # قدیمی‌ترین (همیشه کار میکنه)
        ]
        
        final_reply = None
        
        for model_name in models_to_test:
            try:
                # تست مدل
                model = genai.GenerativeModel(model_name, system_instruction=ASUR_PROMPT, safety_settings=safety_settings)
                chat = model.start_chat(history=[])
                response = chat.send_message(update.message.text)
                if response.text:
                    final_reply = response.text
                    # اگر موفق شد، اسم مدل رو چاپ کن تو کنسول (برای دیباگ) و حلقه رو بشکن
                    print(f"Success with model: {model_name}")
                    break
            except Exception as e:
                print(f"Failed {model_name}: {e}")
                continue # برو مدل بعدی

        if final_reply:
            await update.message.reply_text(final_reply, reply_to_message_id=update.message.message_id)
        else:
            await update.message.reply_text("❌ هیچ مدلی با کلید جدید شما کار نکرد! لطفاً مطمئن شوید کلید درست کپی شده.", reply_to_message_id=update.message.message_id)

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app_bot.run_polling()
