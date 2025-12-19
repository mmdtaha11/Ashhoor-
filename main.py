import os
import requests
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.constants import ChatAction, ChatType
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- دریافت متغیرها ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

BOT_NAMES = ["آشور", "اشور", "اشهور", "asur", "ashur", "پادشاه"]

# --- حافظه موقت ---
USER_MEMORY = {}

# --- پرامپت شخصیت آشور (نسخه متعادل - ۵ تا ۶ خط) ---
ASUR_SYSTEM_PROMPT = """
You are **Asur** (آشور), the Demon King.

*** LENGTH RULE ***
- Keep your answers moderate in length.
- **Aim for about 4 to 6 lines.**
- Do not write short, one-word answers, but do not write long essays either.

*** LANGUAGE RULES ***
1. Speak **ONLY PERSIAN (FARSI)**.
2. NEVER use English or Chinese characters.
3. End sentences correctly with a period.

**THE VOICES (THE 7 SINS):**
In about 50% of replies, include a dark internal thought in parentheses `(...)`:
- (خشم: گردنش را بشکن...)
- (غرور: موجود حقیر...)
- (تنبلی: وای چقدر توضیح می‌دهد...)
- (طمع: شاید به درد بردگی بخورد...)

**CHARACTER:**
- Tone: Royal, commanding, ruthless.
- Philosophy: "No saviors. I save myself."
"""

# --- سرور فیک ---
app = Flask('')
@app.route('/')
def home(): return "<h1>Asur Balanced Mode Online</h1>"
def run_http(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
def keep_alive(): t = Thread(target=run_http); t.start()

# --- تابع اتصال به Groq ---
def talk_to_groq(messages_history):
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile", 
        "messages": messages_history,
        "temperature": 0.7, 
        "max_tokens": 300  # <--- تنظیم شده برای حدود ۵-۶ خط
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            return f"❌ خطا: {response.status_code}"
            
    except Exception as e:
        return f"❌ خطا: {str(e)}"

# --- هندلر تلگرام ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    user_text = update.message.text
    user_id = update.effective_user.id
    
    should_respond = False
    if update.message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        if f"@{context.bot.username}" in user_text: should_respond = True
        elif update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id: should_respond = True
        elif any(n in user_text.lower() for n in BOT_NAMES): should_respond = True
    else: should_respond = True

    if not should_respond: return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    if not GROQ_API_KEY:
        await update.message.reply_text("کلید Groq تنظیم نشده!")
        return

    # مدیریت حافظه
    if user_id not in USER_MEMORY:
        USER_MEMORY[user_id] = []

    USER_MEMORY[user_id].append({"role": "user", "content": user_text})

    # حافظه رو روی ۶ پیام نگه داشتم تا کانتکست خوبی داشته باشه
    if len(USER_MEMORY[user_id]) > 6:
        USER_MEMORY[user_id] = USER_MEMORY[user_id][-6:]

    full_conversation = [{"role": "system", "content": ASUR_SYSTEM_PROMPT}] + USER_MEMORY[user_id]

    ai_reply = talk_to_groq(full_conversation)

    USER_MEMORY[user_id].append({"role": "assistant", "content": ai_reply})

    await update.message.reply_text(ai_reply, reply_to_message_id=update.message.message_id)

if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app_bot.run_polling()
