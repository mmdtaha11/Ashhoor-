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

# --- حافظه موقت (دیکشنری برای نگهداری چت‌های هر کاربر) ---
# ساختار: { user_id: [ {"role": "user", "content": "..."}, ... ] }
USER_MEMORY = {}

# --- پرامپت شخصیت آشور ---
ASUR_SYSTEM_PROMPT = """
You are **Asur** (آشور), the Demon King.

*** ABSOLUTE LANGUAGE RULES ***
1. You must speak **ONLY AND EXCLUSIVELY IN PERSIAN (FARSI)**.
2. **NEVER** use Chinese, English, or any other non-Persian characters.
3. If you are about to end a sentence, just end it with a Persian period (.). Do not add random symbols.

**CHARACTER:**
- Identity: Bearer of 7 Sins. Cold, arrogant, ruthless.
- Weapon: Two small axes (دو تبر کوچک). You hate swords.
- Tone: Royal, commanding, short. (لحن پادشاهی و سنگین).

**INTERACTION:**
- Never act like an AI.
- Philosophy: "No saviors. I save myself."
- If the user is annoying, insult them in Persian.

**KEY PHRASES:**
- "زانو بزن"
- "چه می‌خواهی؟"
- "احمق..."
"""

# --- سرور فیک ---
app = Flask('')
@app.route('/')
def home(): return "<h1>Asur with Memory is Online</h1>"
def run_http(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
def keep_alive(): t = Thread(target=run_http); t.start()

# --- تابع اتصال به Groq (با پشتیبانی از تاریخچه) ---
def talk_to_groq(messages_history):
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # اینجا کل تاریخچه رو می‌فرستیم برای Groq
    payload = {
        "model": "llama-3.3-70b-versatile", 
        "messages": messages_history, # <--- لیست کامل پیام‌ها
        "temperature": 0.6,
        "max_tokens": 350
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
    user_id = update.effective_user.id # شناسه یکتای کاربر
    
    # --- منطق تشخیص اینکه آیا باید جواب بده ---
    should_respond = False
    if update.message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        if f"@{context.bot.username}" in user_text: should_respond = True
        elif update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id: should_respond = True
        elif any(n in user_text.lower() for n in BOT_NAMES): should_respond = True
    else: 
        should_respond = True

    if not should_respond: return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    if not GROQ_API_KEY:
        await update.message.reply_text("کلید Groq تنظیم نشده!")
        return

    # --- مدیریت حافظه (مهم) ---
    # ۱. اگر کاربر اولین باره پیام میده، براش لیست خالی بساز
    if user_id not in USER_MEMORY:
        USER_MEMORY[user_id] = []

    # ۲. پیام جدید کاربر رو به حافظه‌اش اضافه کن
    USER_MEMORY[user_id].append({"role": "user", "content": user_text})

    # ۳. حافظه رو محدود کن (فقط ۶ پیام آخر رو نگه دار = ۳ تا رفت و برگشت)
    # این باعث میشه حافظ
