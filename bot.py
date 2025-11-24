# =======================================================
# كود بوت تليجرام للتخزين الآمن بمجموعات محمية (الإصدار 6.0 - التوكن الجديد)
# =======================================================

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import sqlite3
import random
import string
import secrets 

# -------------------------------------------------------
## 🎬 الإعدادات الأساسية
# -------------------------------------------------------

# ⚠️ تم تحديث التوكن الجديد
BOT_TOKEN = "8599372599:AAEIl4uTdsqdxiybRGxIVcuhJio8uex76SQ"
DB_FILE = "secure_user_storage.db" 

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =======================================================
## 🔑 دوال توليد الكود والبيانات السرية
# =======================================================

def generate_token(length=6):
    """توليد كود أبجدي رقمي عشوائي للمجموعة."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for i in range(length))

def generate_username(length=8):
    """توليد اسم مستخدم عشوائي."""
    return 'USER_' + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for i in range(length))

def generate_password(length=10):
    """توليد كلمة مرور قوية."""
    chars = string.ascii_letters + string.digits + "!@#$"
    return ''.join(secrets.choice(chars) for i in range(length))

def generate_pin():
    """توليد رقم سري PIN مكون من 4 أرقام."""
    return ''.join(secrets.choice(string.digits) for i in range(4))

# =======================================================
## 💾 دوال قاعدة البيانات
# =======================================================

def initialize_db():
    """تهيئة قاعدة البيانات وإنشاء جدولين: للملفات وجدول لبيانات الاعتماد."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # جدول لبيانات الاعتماد (المفتاح هو توكن المجموعة)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                token TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                pin TEXT NOT NULL
            )
        ''')
        
        # جدول لتخزين معرفات الملفات المرتبطة بالتوكن
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                token TEXT NOT NULL,                
                file_id TEXT NOT NULL,
                file_type TEXT
            )
        ''')
        conn.commit()
        conn.close()
        logger.info(f"قاعدة البيانات {DB_FILE} جاهزة بجداول credentials و files.")
    except Exception as e:
        logger.error(f"خطأ في تهيئة قاعدة البيانات: {e}")

def create_credentials(token, username, password, pin):
    """إنشاء بيانات اعتماد فريدة لتوكن المجموعة."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO credentials (token, username, password, pin) VALUES (?, ?, ?, ?)", 
                       (token, username, password, pin))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        logger.error(f"خطأ في حفظ بيانات الاعتماد: {e}")
        return False

def get_credentials(token):
    """استرجاع بيانات الاعتماد (Username, Password, Pin) لتوكن المجموعة."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT username, password, pin FROM credentials WHERE token = ?", (token,))
        result = cursor.fetchone()
        conn.close()
        return result 
    except Exception:
        return None

def save_file_info(token, file_id, file_type):
    """حفظ معرف الملف ونوعه باستخدام الكود (token)."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
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
        cursor.execute("SELECT file_id, file_type FROM files WHERE token = ?", (token,))
        result = cursor.fetchall()
        conn.close()
        return result if result else None 
    except Exception:
        return None

def check_token_exists(token):
    """التحقق من وجود كود في قاعدة البيانات (جدول credentials)."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM credentials WHERE token = ? LIMIT 1", (token,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception:
        return False

def is_username_unique(username):
    """التحقق من فرادة اسم المستخدم."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM credentials WHERE username = ? LIMIT 1", (username,))
        exists = cursor.fetchone() is not None
        conn.close()
        return not exists
    except Exception:
        return False
    
# =======================================================
## 🚀 دوال معالجة التليجرام
# =======================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name if update.message.from_user.first_name else 'عزيزي المستخدم'
    await update.message.reply_text(
        f'مرحباً بك يا {user_name} في بوت التخزين الآمن والمحمي 🔒.\n\n'
        '**وصف البوت:**\n'
        'هذا البوت صُمم لتخزين ملفاتك (صور، فيديوهات، مستندات) بشكل آمن، بحيث إذا قمت بمسحها من هاتفك أو التليجرام، تظل محفوظة هنا. كل مجموعة ملفات يتم تأمينها بشكل منفصل.\n\n'
        '**نظام الحفظ والتأمين الجديد:**\n'
        '1. **لبدء مجموعة جديدة:** أرسل الملف الأول. سأولد لك كود مجموعة سري و**اسم مستخدم** و **كلمة مرور** و **PIN** (للاسترداد).\n'
        '2. **لإضافة ملفات لنفس المجموعة:** أرسل الملف التالي واكتب **كود المجموعة فقط** في التعليق.\n\n'
        '**نظام الاسترجاع الآمن:**\n'
        'لطلب ملفاتك، استخدم الأمر:\n'
        '• **/retrieve [توكن] [اسم المستخدم] [كلمة المرور]**\n'
        '• **/retrieve [توكن] [PIN]** (إذا نسيت الاسم وكلمة المرور)'
    )

async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تحفظ الملفات سواء بإنشاء كود جديد (مع بيانات اعتماد) أو الإضافة لكود موجود."""
    
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
        return 
    
    # 2. تحديد التوكن (من التعليق أو توكن جديد)
    token_to_use = None
    caption = update.message.caption if update.message.caption else ''
    is_new_group = False
    
    if caption:
        potential_token = caption.strip().split()[0].upper()
        # إذا كان الكود موجوداً في جدول credentials، نستخدمه
        if check_token_exists(potential_token):
            token_to_use = potential_token

    # 3. إذا لم يتم تحديد كود صحيح، ننشئ مجموعة جديدة
    if not token_to_use:
        is_new_group = True
        
        # 3.1. توليد كود مجموعة فريد
        token_to_use = generate_token()
        while check_token_exists(token_to_use):
            token_to_use = generate_token()
            
        # 3.2. توليد بيانات اعتماد فريدة
        username_new = generate_username()
        while not is_username_unique(username_new):
            username_new = generate_username()
            
        password_new = generate_password()
        pin_new = generate_pin()
        
        # 3.3. حفظ بيانات الاعتماد الجديدة أولاً
        if not create_credentials(token_to_use, username_new, password_new, pin_new):
             await update.message.reply_text(f"❌ فشل إنشاء بيانات الاعتماد للمجموعة الجديدة. يرجى المحاولة لاحقاً.")
             return

    # 4. حفظ الملف
    if save_file_info(token_to_use, file_id, file_type):
        if is_new_group:
            response_text = (
                f"✅ **تم إنشاء مجموعة آمنة وحفظ {file_type} بنجاح!**\n\n"
                f"**🔑 بيانات الدخول الخاصة بمجموعتك (احفظها جيداً):**\n"
                f"• **توكن المجموعة:** `{token_to_use}`\n"
                f"• **اسم المستخدم:** `{username_new}`\n"
                f"• **كلمة المرور:** `{password_new}`\n"
                f"• **الرقم السري (PIN):** `{pin_new}`\n\n"
                f"**لإضافة ملف آخر، أرسل الملف واكتب **التوكن فقط** في التعليق: **`{token_to_use}`**"
            )
        else:
            response_text = (
                f"✅ **تمت الإضافة بنجاح!** (تم حفظ {file_type})\n"
                f"تم إضافة الملف إلى المجموعة المؤمنة بالتوكن: `{token_to_use}`."
            )
        await update.message.reply_text(response_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ حدث خطأ أثناء محاولة حفظ الملف.")


# دالة استرجاع المجموعة مع التحقق من بيانات الاعتماد
async def retrieve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تسترجع جميع الملفات المرتبطة بكود معين بعد التحقق من بيانات الاعتماد أو الـ PIN."""

    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ استخدام خاطئ.\n"
            "الاستخدام الصحيح:\n"
            "• `/retrieve [توكن] [اسم المستخدم] [كلمة المرور]`\n"
            "• `/retrieve [توكن] [PIN]`"
        )
        return

    # استخلاص البيانات المدخلة
    token = context.args[0].strip().upper() 
    auth_1 = context.args[1]
    auth_2 = context.args[2] if len(context.args) == 3 else None
    
    stored_credentials = get_credentials(token)
    
    if not stored_credentials:
        await update.message.reply_text(f"❌ التوكن '{token}' غير صحيح أو لا يوجد ملفات مرتبطة به.")
        return
        
    stored_username, stored_password, stored_pin = stored_credentials
    is_authenticated = False
    
    # 1. محاولة المصادقة باسم المستخدم وكلمة المرور
    if auth_2:
        if auth_1 == stored_username and auth_2 == stored_password:
            is_authenticated = True
    
    # 2. محاولة المصادقة بالـ PIN (إذا كان هناك مدخلان فقط)
    elif len(context.args) == 2:
        # إذا كان المدخل الثاني هو PIN المخزن
        if auth_1 == stored_pin:
            is_authenticated = True

    if not is_authenticated:
        await update.message.reply_text("❌ فشلت المصادقة. اسم المستخدم وكلمة المرور أو الـ PIN غير صحيحين للتوكن المقدم.")
        return

    # إذا كانت المصادقة ناجحة، نبدأ إرسال الملفات
    file_info_list = get_file_info(token) 
    
    if file_info_list:
        try:
            await update.message.reply_text(
                f"✅ المصادقة ناجحة. جارٍ إرسال {len(file_info_list)} ملفات للمجموعة '{token}'..."
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
        await update.message.reply_text(f"❌ لا توجد ملفات حاليًا مرتبطة بالتوكن '{token}'.")


# دالة معالجة الأخطاء
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    if update and update.message:
        await update.message.reply_text('عذراً، حدث خطأ ما. يرجى مراجعة سجلات الخادم للمزيد من التفاصيل.')

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
    application.add_handler(CommandHandler("retrieve", retrieve))
    
    application.add_handler(CommandHandler("start", start))

    application.add_error_handler(error_handler)

    logger.info("البوت جاهز للعمل. بدء الاستماع للرسائل (Polling)...")
    
    application.run_polling(poll_interval=1.0) 

if __name__ == '__main__':
    main()
        
