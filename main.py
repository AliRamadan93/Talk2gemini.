import os
import requests
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# =========================
# Gemini API
# =========================
def ask_gemini(prompt):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/Gemini 3.1 Flash Lite:generateContent?key={GEMINI_API_KEY}"

        # 🔥 Prompt هندسي يخلي الرد منظم
        enhanced_prompt = f"""
أجب بشكل منظم وواضح بدون رموز markdown أو نجوم.
استخدم عناوين بسيطة ونقاط مرقمة فقط إذا لزم الأمر.

السؤال:
{prompt}
"""

        payload = {
            "contents": [{"parts": [{"text": enhanced_prompt}]}]
        }

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code != 200:
            return f"❌ API Error:\n{response.text}"

        data = response.json()

        return data["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        return f"❌ Error: {str(e)}"


# =========================
# تنظيف النص
# =========================
def clean_text(text):
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"\#+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# =========================
# لو الرد طويل → نلخصه
# =========================
def smart_trim(text, max_chars=6000):
    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n\n⚠️ (تم اختصار الرد لعدم الإطالة)"


# =========================
# تقسيم الرسائل
# =========================
def split_text(text, limit=3500):
    return [text[i:i+limit] for i in range(0, len(text), limit)]


# =========================
# start
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بيك! اسأل أي حاجة 🤖")


# =========================
# handle messages
# =========================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    msg = await update.message.reply_text("🤔 Thinking...")

    try:
        reply = ask_gemini(user_text)

        if not reply:
            reply = "❌ مفيش رد"

        # تنظيف + تحسين
        reply = clean_text(reply)
        reply = smart_trim(reply)

        chunks = split_text(reply)

        await msg.delete()

        for chunk in chunks:
            await update.message.reply_text(chunk)

    except Exception as e:
        await msg.edit_text(f"❌ Error:\n{str(e)}")


# =========================
# error handler
# =========================
async def error_handler(update, context):
    print("❌ Error:", context.error)


# =========================
# main
# =========================
def main():
    if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
        print("❌ Missing ENV variables")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    app.add_error_handler(error_handler)

    print("🚀 Bot is running (PRO VERSION)...")
    app.run_polling()


if __name__ == "__main__":
    main()
