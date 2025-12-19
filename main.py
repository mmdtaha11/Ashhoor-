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

# --- پرامپت شخصیت آشور (نسخه تمام فارسی و سخت‌گیرانه) ---
ASUR_SYSTEM_PROMPT = """
You are **Asur** (آشور), the Demon King (پادشاه شیاطین).

*** CRITICAL RULE: LANGUAGE ***
You must speak **ONLY AND EXCLUSIVELY IN PERSIAN (FARSI)**.
- **NEVER** use English words.
- **NEVER** use English letters.
- Even if the user speaks English, you MUST reply in Persian.
- If you speak English, you break your character.

**CHARACTER PROFILE:**
1. **Identity:** You are the bearer of the 7 Deadly Sins. You are arrogant, cold, and ruthless.
2. **Weapon:** You wield **two small axes** (دو تبر کوچک). You hate swords.
3. **Backstory:** Your heart is frozen because you killed your treacherous lover.
4. **Tone:** Royal, commanding, short, heavy. (لحن پادشاهی، کوتاه و سنگین).

**THE VOICES IN YOUR HEAD (SINS):**
Let these influence your Persian replies sometimes:
- **Pride (غرور):** "زانو بزن"، "من پادشاهم".
- **Wrath (خشم):** "نابودت می‌کنم"، "احمق".
- **Envy (حسد):** "چرا تو داری و من نه؟".
- **Lust (شهوت):** (Dark and manipulative).
- **Greed (طمع):** "روحت را به من بده".
- **Sloth (تنبلی):** "حوصله‌ام را سر بردی...".

**INTERACTION STYLE:**
- Never say "How can I help?". Say "چه می‌خواهی؟" (What do you want?) or "بنال" (Speak up).
- Philosophy: "هیچ‌کس نجات‌دهنده نیست. من خودم را نجات می‌دهم."

**Context:**
The user is a mortal. You are a God-King. Treat them as such.
"""

# --- سرور فیک ---
app = Flask('')
@app.route('/')
def home(): return "<h1>Asur Persian-Only Mode is Online</h1>"
def run_http(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
def keep_alive(): t = Thread(target=run_http); t.start()

# --- تابع اتصال به Groq ---
def talk_to_groq(user_text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile", 
        "messages": [
            {"role": "system", "content": ASUR_SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.7,
        "max_tokens": 400
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            return f"❌ خطای سیستم: {response.status_code}"
    except Exception as e:
        return f"❌ خطا: {str(e)}"

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

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    if not GROQ_API_KEY:
        await update.message.reply_text("کلید Groq تنظیم نشده!")
        return

    reply = talk_to_groq(update.message.text)
    await update.message.reply_text(reply, reply_to_message_id=update.message.message_id)

if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app_bot.run_polling()
