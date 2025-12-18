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

BOT_NAMES = ["آشور", "اشور", "اشهور", "asur", "ashur", "پادشاه"]

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
def home(): return "<h1>Asur Direct-Mode Online</h1>"
def run_http(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
def keep_alive(): t = Thread(target=run_http); t.start()

# --- تابع اتصال مستقیم (بدون کتابخانه) ---
def talk_to_google(text):
    # این آدرس مستقیم اینترنت گوگل است
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    
    payload = {
        "contents": [{
            "parts": [{"text": f"{ASUR_PROMPT}\n\nUser: {text}\nAsur:"}]
        }],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    
    try:
        # ارسال درخواست مثل مرورگر
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"❌ ارور گوگل ({response.status_code}):\n{response.text}"
            
    except Exception as e:
        return f"❌ خطای اتصال:\n{str(e)}"

# --- هندلر تلگرام ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    should_respond = False
    if update.message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        if f"@{context.bot.username}" in update.message.text: should_respond = True
        elif update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id: should_respond = True
        elif any(n in update.message.text.lower() for n in BOT_NAMES): should_respond = True
    else: should_respond = True

    if not should_respond: return

    # ارسال پیام
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    if not GEMINI_API_KEY:
        await update.message.reply_text("❌ کلید تنظیم نشده!")
        return

    reply = talk_to_google(update.message.text)
    await update.message.reply_text(reply, reply_to_message_id=update.message.message_id)

if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app_bot.run_polling()
