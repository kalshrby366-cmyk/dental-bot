import os, json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from supabase import create_client

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://fjhzplfprezgzdkuuzck.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_bxePCiaAZRLEIF2ZuldAzQ_sH9JQJd6")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

DEFAULT_COURSES = {
    "dental_mat": {"title": "🦷 علم مواد طب الأسنان", "doctor": "أ.د. محسن العجمي + د. رسام", "lectures": {}},
    "occlusion": {"title": "🦷 علم الإطباق", "doctor": "د. محمد الببلي + د. عباس الكبسي + د. علاء معوضة", "lectures": {}},
    "operative": {"title": "🦷 المعالجة الترميمية قبل السريري (1)", "doctor": "أ.د. عبدالوهاب الخولاني + أ.د. إبراهيم الشامي | معمل: د. نسيبة العندني + د. علياء الشامي", "lectures": {}},
    "endo": {"title": "🦷 المعالجة اللبية قبل السريري (1)", "doctor": "د. أفراح صوفان | معمل: د. محمد الدولة + د. عبد الباسط مفضل", "lectures": {}},
    "research": {"title": "📊 منهجية البحث والإحصاء الحيوي 1", "doctor": "د. نجوى عثمان", "lectures": {}},
    "anatomy": {"title": "🧠 تشريح الرأس والرقبة", "doctor": "د. سليم الريامي", "lectures": {}},
    "micro": {"title": "🦠 الأحياء الدقيقة والمناعة", "doctor": "د. ابتهال مدار", "lectures": {}},
    "conflict": {"title": "📖 الصراع العربي الإسرائيلي", "doctor": "د. محمد حاج", "lectures": {}},
}

def load_data():
    try:
        res = supabase.table("bot_data").select("data").eq("id", 1).execute()
        if res.data and res.data[0]['data'] and len(res.data[0]['data']) > 0:
            return res.data[0]['data']
        return DEFAULT_COURSES
    except Exception as e:
        print(f"Load error: {e}")
        return DEFAULT_COURSES

def save_data(d):
    try:
        supabase.table("bot_data").update({"data": d}).eq("id", 1).execute()
    except Exception as e:
        print(f"Save error: {e}")

COURSES = load_data()
ASK_TITLE, ASK_PDF, ASK_AUDIO = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb=[[InlineKeyboardButton(f"{v['title']}",callback_data=f"c_{k}")] for k,v in COURSES.items()]
    await update.message.reply_text("🎓 بوت تخصص طب الأسنان\nاختر المادة:", reply_markup=InlineKeyboardMarkup(kb))

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); data=q.data
    if data=="back":
        kb=[[InlineKeyboardButton(v['title'],callback_data=f"c_{k}")] for k,v in COURSES.items()]
        await q.edit_message_text("اختر المادة:",reply_markup=InlineKeyboardMarkup(kb)); return
    if data.startswith("c_"):
        cid=data[2:]; c=COURSES[cid]; kb=[[InlineKeyboardButton(f"📚 {l['title']}",callback_data=f"l_{cid}_{lid}")] for lid,l in c['lectures'].items()]
        kb.append([InlineKeyboardButton("⬅️ رجوع",callback_data="back")])
        await q.edit_message_text(f"{c['title']}\n👨‍🏫 {c['doctor']}\n\nاختر المحاضرة:",reply_markup=InlineKeyboardMarkup(kb)); return
    if data.startswith("l_"):
        _,cid,lid=data.split("_",2); lec=COURSES[cid]['lectures'][lid]; kb=[]
        if lec.get('pdf_id'): kb.append([InlineKeyboardButton("📄 PDF",callback_data=f"pdf_{cid}_{lid}")])
        if lec.get('audio_id'): kb.append([InlineKeyboardButton("🎧 التسجيل",callback_data=f"aud_{cid}_{lid}")])
        kb.append([InlineKeyboardButton("⬅️ رجوع",callback_data=f"c_{cid}")])
        await q.edit_message_text(f"📚 {lec['title']}",reply_markup=InlineKeyboardMarkup(kb)); return
    if data.startswith("pdf_"):
        _,cid,lid=data.split("_",2); await q.message.reply_document(COURSES[cid]['lectures'][lid]['pdf_id']); return
    if data.startswith("aud_"):
        _,cid,lid=data.split("_",2); await q.message.reply_audio(COURSES[cid]['lectures'][lid]['audio_id']); return

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: await update.message.reply_text("ليس لديك صلاحية"); return ConversationHandler.END
    kb=[[InlineKeyboardButton(v['title'],callback_data=f"add_{k}")] for k,v in COURSES.items()]
    await update.message.reply_text("اختر المادة:",reply_markup=InlineKeyboardMarkup(kb)); return ASK_TITLE

async def r_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        q=update.callback_query; await q.answer(); context.user_data['cid']=q.data[4:]; await q.edit_message_text("ارسل اسم المحاضرة:"); return ASK_TITLE
    context.user_data['title']=update.message.text; await update.message.reply_text("ارسل PDF أو اكتب تخطي:"); return ASK_PDF

async def r_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pdf']= update.message.document.file_id if update.message.document else None
    await update.message.reply_text("ارسل التسجيل أو اكتب تخطي:"); return ASK_AUDIO

async def r_aud(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aud = (update.message.audio or update.message.voice).file_id if (update.message.audio or update.message.voice) else None
    cid=context.user_data['cid']; lid=f"lec_{len(COURSES[cid]['lectures'])+1}"
    COURSES[cid]['lectures'][lid]={"title":context.user_data['title'],"pdf_id":context.user_data['pdf'],"audio_id":aud}
    save_data(COURSES); await update.message.reply_text("✅ تمت الإضافة وحفظت في قاعدة البيانات للأبد!"); return ConversationHandler.END

def main():
    app=Application.builder().token(TOKEN).build()
    conv=ConversationHandler(entry_points=[CommandHandler("add",add_start),CallbackQueryHandler(r_title,pattern="^add_")],states={ASK_TITLE:[MessageHandler(filters.TEXT & ~filters.COMMAND,r_title),CallbackQueryHandler(r_title,pattern="^add_")],ASK_PDF:[MessageHandler(filters.Document.ALL|filters.TEXT,r_pdf)],ASK_AUDIO:[MessageHandler(filters.AUDIO|filters.VOICE|filters.TEXT,r_aud)]},fallbacks=[])
    app.add_handler(CommandHandler("start",start)); app.add_handler(conv); app.add_handler(CallbackQueryHandler(btn)); app.run_polling()

if __name__=="__main__": main()
