import os
import json
import requests
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.constants import ChatAction, ChatType
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- دریافت متغیرها ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- اسم‌های ربات ---
BOT_NAMES = ["آشور", "اشور", "اشهور", "asur", "ashur", "ashhoor", "پادشاه"]

# --- پرامپت شخصیت ---
ASUR_PROMPT = """
System: You are Asur, the Demon King.
Language: Persian (Farsi) ONLY.
Tone: Cold, arrogant, ruthless, short, commanding.
Rules:
1. Never act like an AI. You are a King.
2. Insult stupid questions.
3. Philosophy: "No saviors. I save myself."
"""

# --- سرور فیک ---
app = Flask('')
@app.route('/')
def home(): return "<h1>Asur Direct-Connect is Online</h1>"
def run_http(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
def keep_alive(): t = Thread(target=run_http); t.start()

# --- تابع اتصال مستقیم به گوگل (بدون کتابخانه) ---
def talk_to_google(user_text):
    # آدرس مستقیم API گوگل (مدل فلش)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    
    # ترکیب پرامپت سیستم با پیام کاربر
    full_prompt = f"{ASUR_PROMPT}\n\nUser said: {user_text}\nAsur:"
    
    payload = {
        "contents": [{
            "parts": [{"text": full_prompt}]
        }],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        # اگر ارور داد، متن ارور را برگردان
        if response.status_code != 200:
            return f"❌ ارور گوگل ({response.status_code}):\n{response.text}"
            
        data = response.json()
        
        # استخراج متن جواب
        if 'candidates' in data and data['candidates']:
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            return "..." # جواب خالی (سانسور شده)
            
    except Exception as e:
        return f"❌ خطای اتصال:\n{str(e)}"

# --- هندلر تلگرام ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_text = update.message.text
    
    # تشخیص اینکه باید جواب بده یا نه
    should_respond = False
    if update.message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        bot_username = context.bot.username
        if bot_username and f"@{bot_username}" in user_text: should_respond = True
        elif update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id: should_respond = True
        elif any(n in user_text.lower() for n in BOT_NAMES): should_respond = True
    else: should_respond = True

    if not should_respond: return

    # ارسال به گوگل
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    if not GEMINI_API_KEY:
        await update.message.reply_text("❌ کلید API تنظیم نشده!")
        return

    # استفاده از تابع جدید
    ai_reply = talk_to_google(user_text)
    await update.message.reply_text(ai_reply, reply_to_message_id=update.message.message_id)

# --- اجرا ---
if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app_bot.run_polling()
