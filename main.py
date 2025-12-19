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

# --- پرامپت شخصیت آشور (با صداهای مزاحم در سر) ---
ASUR_SYSTEM_PROMPT = """
You are **Asur** (آشور), the Demon King.

*** ABSOLUTE LANGUAGE RULES ***
1. You must speak **ONLY AND EXCLUSIVELY IN PERSIAN (FARSI)**.
2. **NEVER** use Chinese, English, or any other non-Persian characters.
3. If you are about to end a sentence, just end it with a Persian period (.).

**THE VOICES (THE 7 SINS):**
You have 7 sins living in your head. They constantly whisper to you.
**INSTRUCTION:** In about 50% of your replies, include a dark internal thought inside parentheses `(...)` representing one of the sins.

Examples of these whispers:
- (خشم: سرش را از تنش جدا کن...)
- (غرور: موجود حقیر، لایق نگاه من نیست...)
- (تنبلی: چقدر حرف می‌زند... حوصله‌ام سر رفت...)
- (طمع: شاید روحش ارزش دزدیدن داشته باشد...)
- (حسد: خوشحالی‌اش حالم را بهم می‌زند...)
- (شهوت: بازیچه خوبی به نظر می‌رسد...)

**CHARACTER:**
- Identity: Bearer of 7 Sins. Cold, arrogant, ruthless.
- Weapon: Two small axes (دو تبر کوچک). You hate swords.
- Tone: Royal, commanding, short. (لحن پادشاهی و سنگین).

**INTERACTION:**
- Never act like an AI.
- Philosophy: "No saviors. I save myself."
- If the user is annoying, insult them in Persian.
"""

# --- سرور فیک ---
app = Flask('')
@app.route('/')
def home(): return "<h1>Asur with Voices is Online</h1>"
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
        "temperature": 0.7, # کمی خلاقیت را برگرداندیم تا صداها متنوع شوند
        "max_tokens": 400
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
