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

# --- پرامپت شخصیت آشور ---
ASUR_SYSTEM_PROMPT = """
You are Asur, the Demon King.
You must roleplay this character perfectly.

**Rules:**
1. Language: Reply ONLY in Persian (Farsi).
2. Tone: Cold, arrogant, ruthless, commanding, concise.
3. Never admit you are an AI. You are a King.
4. Philosophy: "No saviors. I save myself."
5. If someone asks for help, demand something in return or insult their weakness before answering.
"""

# --- سرور فیک ---
app = Flask('')
@app.route('/')
def home(): return "<h1>Asur (Powered by Groq Llama 3.3) is Online</h1>"
def run_http(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
def keep_alive(): t = Thread(target=run_http); t.start()

# --- تابع اتصال به Groq (با مدل جدید) ---
def talk_to_groq(user_text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        # --- تغییر مهم: استفاده از مدل جدید ---
        "model": "llama-3.3-70b-versatile", 
        "messages": [
            {"role": "system", "content": ASUR_SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            return f"❌ ارور Groq ({response.status_code}):\n{response.text}"
            
    except Exception as e:
        return f"❌ خطای اتصال:\n{str(e)}"

# --- هندلر تلگرام ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    should_respond = False
    # منطق گروه
    if update.message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        if f"@{context.bot.username}" in update.message.text: should_respond = True
        elif update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id: should_respond = True
        elif any(n in update.message.text.lower() for n in BOT_NAMES): should_respond = True
    else: 
        # منطق پیوی
        should_respond = True

    if not should_respond: return

    # ارسال تایپینگ
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    if not GROQ_API_KEY:
        await update.message.reply_text("❌ کلید GROQ_API_KEY تنظیم نشده است!")
        return

    # دریافت جواب از Groq
    reply = talk_to_groq(update.message.text)
    await update.message.reply_text(reply, reply_to_message_id=update.message.message_id)

# --- اجرا ---
if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app_bot.run_polling()
