import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

user_memory = {}

# 🧹 تنظيف الرد
def clean_text(text):
    text = text.replace("*******", "").replace("****", "").strip()
    return text if text else "⚠️ حصل خطأ، حاول تاني."

# ✨ تنسيق الرد
def format_response(text):
    lines = text.split("\n")
    formatted = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        # عنوان
        if len(line) < 60 and not line.endswith("."):
            formatted.append(f"🔹 {line}")
        else:
            formatted.append(f"• {line}")

    return "\n".join(formatted)

# ✂️ تلخيص لو طويل
def shorten_if_needed(text):
    if len(text) > 2000:
        return text[:2000] + "\n\n... (تم اختصار الرد)"
    return text

# 🤖 الاتصال بـ Groq
def ask_groq(user_id, prompt):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        if user_id not in user_memory:
            user_memory[user_id] = [
                {
                    "role": "system",
                    "content": (
                        "You are a professional AI assistant. "
                        "Always format your response with clear headings and bullet points. "
                        "Keep answers clean and well structured like ChatGPT. "
                        "Answer in Arabic if the user speaks Arabic."
                    )
                }
            ]

        user_memory[user_id].append({
            "role": "user",
            "content": prompt[:2000]
        })

        # تقليل الذاكرة
        user_memory[user_id] = user_memory[user_id][-10:]

        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": user_memory[user_id],
            "temperature": 0.7,
            "max_tokens": 800
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code != 200:
            return f"❌ API Error:\n{response.text}"

        data = response.json()
        reply = data["choices"][0]["message"]["content"]

        reply = clean_text(reply)
        reply = shorten_if_needed(reply)
        reply = format_response(reply)

        user_memory[user_id].append({
            "role": "assistant",
            "content": reply
        })

        return reply

    except Exception as e:
        return f"❌ Error: {str(e)}"

# 📩 أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بيك! ابعت أي حاجة 🤖")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_memory[user_id] = []
    await update.message.reply_text("🧹 تم مسح المحادثة")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.message.from_user.id

    msg = await update.message.reply_text("🤔 Thinking...")

    reply = ask_groq(user_id, user_text)

    # تقسيم لو أطول من حد تيليجرام
    if len(reply) > 4000:
        for i in range(0, len(reply), 4000):
            await update.message.reply_text(reply[i:i+4000])
        await msg.delete()
    else:
        await msg.edit_text(reply)

# 🚀 تشغيل
def main():
    if not TELEGRAM_BOT_TOKEN or not GROQ_API_KEY:
        print("❌ Missing ENV variables")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
