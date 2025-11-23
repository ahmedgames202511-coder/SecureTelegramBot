# =======================================================
# كود بوت تليجرام للتخزين الآمن للملفات بالـ Token (الإصدار 4.0 المصحح للاسترجاع)
# =======================================================

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import sqlite3
import random
import string
import os

# -------------------------------------------------------
## 🎬 الإعدادات الأساسية
# -------------------------------------------------------

BOT_TOKEN = "8569298426:AAH_FYVCMTIFs78NI1fe53sTElYgLzb9buI"
DB_FILE = "secure_files_storage.db" 

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =======================================================
## 🔑 دوال توليد الكود وقاعدة البيانات (تبقى كما هي)
# =======================================================

def generate_token(length=6):
    """توليد كود أبجدي رقمي عشوائي فريد."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def initialize_db():
    """تهيئة قاعدة البيانات وإنشاء جدول 'files' لتخزين معرفات الملفات (file_id)."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                token TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                file_type TEXT 
            )
        ''')
        conn.commit()
        conn.close()
        logger.info(f"قاعدة البيانات {DB_FILE} جاهزة لتخزين معرفات الملفات.")
    except Exception as e:
        logger.error(f"خطأ في تهيئة قاعدة البيانات: {e}")

def save_file_info(token, file_id, file_type):
    """حفظ معرف الملف ونوعه باستخدام الكود (token) كمفتاح."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO files (token, file_id, file_type) VALUES (?, ?, ?)", 
                       (token, file_id, file_type))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        logger.error(f"خطأ في حفظ البيانات: {e}")
        return False

def get_file_info(token):
    """استرجاع معرف الملف ونوعه المرتبط بالكود."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, file_type FROM files WHERE token = ?", (token,))
        result = cursor.fetchone()
        conn.close()
        return result
    except Exception:
        return None

# =======================================================
## 🚀 دوال معالجة التليجرام
# =======================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name if update.message.from_user.first_name else 'عزيزي المستخدم'
    await update.message.reply_text(
        f'مرحباً بك يا {user_name} في بوت التخزين الآمن 🔒.\n\n'
        '**طريقة تخزين الملفات والحصول على الكود:**\n'
        '1. **فقط أرسل الملف** (صورة، فيديو، مستند) وسأقوم بحفظه تلقائياً وإعطائك الكود.\n\n'
        '**طريقة استرجاع الملف:**\n'
        'استخدم الأمر: **/get_file [الكود السري]**'
    )

async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تحفظ معرف الملف الذي تم إرساله وتولد كود استرجاع تلقائياً."""
    file_id = None
    file_type = "غير محدد"

    if update.message.video:
        file_id = update.message.video.file_id
        file_type = "فيديو"
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id 
        file_type = "صورة"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "مستند"
    else:
        return
        
    token = None
    for _ in range(5): 
        new_token = generate_token()
        if save_file_info(new_token, file_id, file_type):
            token = new_token
            break
    
    if token:
        response_text = (
            f"✅ **تم الحفظ بنجاح!** (النوع: {file_type})\n\n"
            f"**كود الاسترجاع (Token):** `{token}`\n\n"
            f"**🔑 يجب عليك حفظ هذا الكود لاسترجاع ملفك في أي وقت، حتى بعد مسح البوت.**"
        )
        await update.message.reply_text(response_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ حدث خطأ أثناء محاولة حفظ الملف أو فشل توليد كود فريد.")


# دالة الاسترجاع المُعدلة لزيادة الموثوقية
async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تسترجع الملف باستخدام الكود السري المخزن."""

    if not context.args:
        await update.message.reply_text("الرجاء إدخال كود الاسترجاع. مثال: /get_file A1B2C3")
        return

    token = context.args[0].strip().upper() 
    file_info = get_file_info(token)
    
    if file_info:
        file_id, file_type = file_info
        
        caption = f"✅ الملف المطلوب (النوع: {file_type}) للكود '{token}'."
        
        try:
            # 💡 التعديل الرئيسي: استخدام الدالة المناسبة لكل نوع
            if file_type == "صورة":
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=file_id,
                    caption=caption
                )
            elif file_type == "فيديو":
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=file_id,
                    caption=caption
                )
            else:
                # للمستندات وأنواع الملفات الأخرى
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file_id,
                    caption=caption
                )
        except Exception as e:
            logger.error(f"خطأ في إرسال الملف: {e}")
            await update.message.reply_text(f"❌ لم أتمكن من إرسال الملف. قد يكون الكود خاطئاً أو حدث خطأ في الاتصال.")
    else:
        await update.message.reply_text(f"❌ الكود '{token}' غير صحيح أو لا يوجد ملف مرتبط به.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    if update and update.message:
        await update.message.reply_text('عذراً، حدث خطأ ما. يرجى المحاولة مرة أخرى.')

# =======================================================
## ⚙️ الدالة الرئيسية لتشغيل البوت
# =======================================================

def main() -> None:
    """بناء وتشغيل البوت."""
    initialize_db() 
    logger.info("جاري إعداد البوت...")

    application = Application.builder().token(BOT_TOKEN).build()

    # استخدام الفلاتر الفردية المتوافقة
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.Document.ALL, 
        save_file
    ))
    
    application.add_handler(CommandHandler("get_file", get_file))
    application.add_handler(CommandHandler("start", start))

    application.add_error_handler(error_handler)

    logger.info("البوت جاهز للعمل. بدء الاستماع للرسائل (Polling)...")
    
    application.run_polling(poll_interval=1.0) 

if __name__ == '__main__':
    main()
