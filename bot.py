# =======================================================
# كود بوت تليجرام لتخزين مجموعة الملفات بكود واحد
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
DB_FILE = "secure_groups_storage.db" # تم تغيير اسم الملف لتفادي تعارض الجداول القديمة

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =======================================================
## 🔑 دوال توليد الكود وقاعدة البيانات
# =======================================================

def generate_token(length=6):
    """توليد كود أبجدي رقمي عشوائي فريد."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def initialize_db():
    """تهيئة قاعدة البيانات للسماح بتخزين ملفات متعددة بنفس الكود."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT, -- المفتاح الأساسي للتسجيل
                token TEXT NOT NULL,                -- الكود السري (يمكن أن يتكرر)
                file_id TEXT NOT NULL,
                file_type TEXT
            )
        ''')
        conn.commit()
        conn.close()
        logger.info(f"قاعدة البيانات {DB_FILE} جاهزة لتخزين مجموعات الملفات.")
    except Exception as e:
        logger.error(f"خطأ في تهيئة قاعدة البيانات: {e}")

def save_file_info(token, file_id, file_type):
    """حفظ معرف الملف ونوعه باستخدام الكود (token)."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # INSERT INTO الآن لا تحتاج إلى فرادة في التوكن
        cursor.execute("INSERT INTO files (token, file_id, file_type) VALUES (?, ?, ?)", 
                       (token, file_id, file_type))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"خطأ في حفظ البيانات: {e}")
        return False

def get_file_info(token):
    """استرجاع جميع معرفات الملفات المرتبطة بكود معين."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # SELECT الآن تعيد قائمة بالملفات لنفس التوكن
        cursor.execute("SELECT file_id, file_type FROM files WHERE token = ?", (token,))
        result = cursor.fetchall()
        conn.close()
        return result if result else None # تعيد قائمة من (file_id, file_type)
    except Exception:
        return None

def check_token_exists(token):
    """التحقق من وجود كود في قاعدة البيانات."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM files WHERE token = ? LIMIT 1", (token,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception:
        return False

# =======================================================
## 🚀 دوال معالجة التليجرام
# =======================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name if update.message.from_user.first_name else 'عزيزي المستخدم'
    await update.message.reply_text(
        f'مرحباً بك يا {user_name} في بوت تخزين المجموعات الآمنة 🔒.\n\n'
        '**طريقة حفظ المجموعات (صور/فيديو/ملفات):**\n'
        '1. **لإنشاء مجموعة جديدة:** فقط أرسل الملف الأول. سأعطيك كوداً سرياً.\n'
        '2. **لإضافة ملفات لنفس الكود:** أرسل الملف التالي واكتب في التعليق: `/add [الكود السري]`.\n\n'
        '**طريقة استرجاع المجموعة:**\n'
        'استخدم الأمر: **/get_group [الكود السري]**'
    )

async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تحفظ الملفات سواء بإنشاء كود جديد أو الإضافة لكود موجود."""
    file_id = None
    file_type = "غير محدد"
    
    # 1. تحديد نوع الملف ومعرفه
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
        return # ليس ملفاً، تجاهل
    
    # 2. التحقق من التعليق: هل يريد المستخدم الإضافة لكود موجود؟
    token_to_use = None
    caption = update.message.caption if update.message.caption else ''
    
    if caption.strip().upper().startswith('/ADD'):
        try:
            # استخراج الكود من التعليق: /add A1B2C3
            parts = caption.strip().split()
            potential_token = parts[1].strip().upper()
            if check_token_exists(potential_token):
                token_to_use = potential_token
        except IndexError:
            # إذا كتب المستخدم /add فقط دون كود
            await update.message.reply_text("❌ لاستخدام `/add`، يجب إرسال الكود بعده. مثال: `/add A1B2C3`")
            return
    
    # 3. إذا لم يتم تحديد كود صحيح، ننشئ كوداً جديداً
    is_new_group = False
    if not token_to_use:
        is_new_group = True
        token_to_use = generate_token()
    
    # 4. الحفظ
    if save_file_info(token_to_use, file_id, file_type):
        if is_new_group:
            response_text = (
                f"✅ **تم إنشاء وحفظ مجموعة جديدة بنجاح!** (تم حفظ {file_type})\n\n"
                f"**كود المجموعة (Token):** `{token_to_use}`\n\n"
                f"**لإضافة ملفات أخرى، أرسل الملف واكتب في التعليق: `/add {token_to_use}`**"
            )
        else:
            response_text = (
                f"✅ **تمت الإضافة بنجاح!** (تم حفظ {file_type})\n"
                f"تم إضافة الملف إلى المجموعة ذات الكود: `{token_to_use}`."
            )
        await update.message.reply_text(response_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ حدث خطأ أثناء محاولة حفظ الملف.")


# دالة استرجاع المجموعة
async def get_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تسترجع جميع الملفات المرتبطة بكود معين."""

    if not context.args:
        await update.message.reply_text("الرجاء إدخال كود المجموعة. مثال: /get_group A1B2C3")
        return

    token = context.args[0].strip().upper() 
    file_info_list = get_file_info(token) # قائمة بـ (file_id, file_type)
    
    if file_info_list:
        try:
            await update.message.reply_text(
                f"✅ جارٍ إرسال {len(file_info_list)} ملفات للمجموعة '{token}'..."
            )
            
            # إرسال كل ملف في القائمة بالترتيب
            for file_id, file_type in file_info_list:
                caption = f"ملف ({file_type}) من المجموعة '{token}'."
                
                if file_type == "صورة":
                    await context.bot.send_photo(update.effective_chat.id, photo=file_id, caption=caption)
                elif file_type == "فيديو":
                    await context.bot.send_video(update.effective_chat.id, video=file_id, caption=caption)
                else:
                    await context.bot.send_document(update.effective_chat.id, document=file_id, caption=caption)
            
            await update.message.reply_text("✅ انتهى إرسال ملفات المجموعة.")

        except Exception as e:
            logger.error(f"خطأ في إرسال الملفات: {e}")
            await update.message.reply_text(f"❌ حدث خطأ أثناء إرسال الملفات: {e}")
    else:
        await update.message.reply_text(f"❌ الكود '{token}' غير صحيح أو لا توجد ملفات مرتبطة به.")

# دالة معالجة الأخطاء
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    if update and update.message:
        await update.message.reply_text('عذراً، حدث خطأ ما.')

# =======================================================
## ⚙️ الدالة الرئيسية لتشغيل البوت
# =======================================================

def main() -> None:
    """بناء وتشغيل البوت."""
    initialize_db() 
    logger.info("جاري إعداد البوت...")

    application = Application.builder().token(BOT_TOKEN).build()

    # التقاط الصور والفيديوهات والمستندات
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.Document.ALL, 
        save_file
    ))
    
    # معالج أمر الاسترجاع
    application.add_handler(CommandHandler("get_group", get_group))
    
    application.add_handler(CommandHandler("start", start))

    application.add_error_handler(error_handler)

    logger.info("البوت جاهز للعمل. بدء الاستماع للرسائل (Polling)...")
    
    application.run_polling(poll_interval=1.0) 

if __name__ == '__main__':
    main()
    
