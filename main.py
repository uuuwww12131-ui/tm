import telebot

TOKEN = "8911794053:AAFh6eTYuUJFZDUSwwLJK8Kq1_QSX-JpLjw"
bot = telebot.TeleBot(TOKEN)

# قاموس لتخزين الرتب والمكتومين
USER_RANKS = {}  # {chat_id: {user_id: rank_name}}
MUTED_USERS = set()  # مجموعة لتخزين الآيديات المكتومة

RANKS_HIERARCHY = {
    "مالك أساسي": 5,
    "مالك": 4,
    "منشئ": 3,
    "مدير": 2,
    "أدمن": 1,
    "عضو": 0
}

def get_user_rank(chat_id, user_id, chat_member):
    # المالك الأصلي للمجموعة في تليجرام له أعلى رتبة
    if chat_member.status in ["creator"]:
        return 5
    # المشرفين في تليجرام رتبتهم مدير افتراضياً إذا لم تُحدد لهم رتبة خاصة
    if chat_member.status in ["administrator"]:
        return USER_RANKS.get(chat_id, {}).get(user_id, 2)
    # باقي الأعضاء يتفقد الرتبة المرفوعة، وإذا لم تكن موجودة يرجع 0 (عضو عالي)
    return RANKS_HIERARCHY.get(USER_RANKS.get(chat_id, {}).get(user_id, "عضو"), 0)

# 1. الترحيب بالعضو الجديد
@bot.message_handler(content_types=["new_chat_members"])
def welcome_new_member(message):
    chat_name = message.chat.title
    for user in message.new_chat_members:
        username = f"@{user.username}" if user.username else user.first_name
        text = f"أهلا وسهلا بك في مجموعة {chat_name}\nالعضو الجديد: {username}"
        bot.send_message(message.chat.id, text)

# 2. نظام الرفع والتنزيل بالرد
@bot.message_handler(func=lambda m: m.text and (m.text.startswith("رفع ") or m.text.startswith("تنزيل ")))
def change_rank(message):
    if message.chat.type == "private":
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "يرجى الرد على رسالة العضو لتنفيذ الأمر.")
        return

    actor_id = message.from_user.id
    target_user = message.reply_to_message.from_user
    chat_id = message.chat.id
    
    actor_member = bot.get_chat_member(chat_id, actor_id)
    actor_level = get_user_rank(chat_id, actor_id, actor_member)
    
    # فقط المالك والمالك الأساسي (رتبة 4 و 5) يمكنهم الرفع والتنزيل
    if actor_level < 4:
        bot.reply_to(message, "هذا الأمر للمالك والمالك الأساسي فقط.")
        return

    parts = message.text.split(maxsplit=1)
    action = parts[0]
    rank_name = parts[1].strip() if len(parts) > 1 else ""

    if action == "رفع":
        if rank_name not in RANKS_HIERARCHY or rank_name == "عضو":
            bot.reply_to(message, f"الرتب المتاحة للرفع هي: مالك أساسي، مالك، منشئ، مدير، أدمن")
            return
        
        if chat_id not in USER_RANKS:
            USER_RANKS[chat_id] = {}
        
        USER_RANKS[chat_id][target_user.id] = rank_name
        bot.reply_to(message, f"تم رفع العضو إلى رتبة [{rank_name}] بنجاح.")

    elif action == "تنزيل":
        if chat_id in USER_RANKS and target_user.id in USER_RANKS[chat_id]:
            del USER_RANKS[chat_id][target_user.id]
        bot.reply_to(message, "تم تنزيل العضو إلى رتبة [عضو].")

# 3. إدارة الرسائل والكتم والأوامر الإدارية
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'document', 'sticker'])
def handle_all_messages(message):
    if message.chat.type == "private":
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id

    # إذا كان المستخدم مكتوماً، يتم حذف رسالته مباشرةً
    if user_id in MUTED_USERS:
        try:
            bot.delete_message(chat_id, message.message_id)
        except:
            pass
        return

    if not message.text:
        return

    text = message.text.strip()
    
    # أوامر الإشراف بالرد (كتم، الغاء كتم، حظر، طرد)
    if message.reply_to_message and text in ["كتم", "الغاء كتم", "حظر", "طرد"]:
        actor_member = bot.get_chat_member(chat_id, user_id)
        actor_level = get_user_rank(chat_id, user_id, actor_member)
        
        # إذا كان المستخدم "عضو" (مستواه 0) يتم رفض أمره
        if actor_level < 1:
            bot.reply_to(message, "أنت مجرد عضو ولا تملك صلاحيات إدارية.")
            return

        target_user = message.reply_to_message.from_user
        
        try:
            if text == "كتم":
                MUTED_USERS.add(target_user.id)
                bot.reply_to(message, "تم كتم العضو وسيتم حذف كافة رسائله القادمة.")
            elif text == "الغاء كتم":
                if target_user.id in MUTED_USERS:
                    MUTED_USERS.remove(target_user.id)
                bot.reply_to(message, "تم إلغاء كتم العضو.")
            elif text == "حظر":
                bot.ban_chat_member(chat_id, target_user.id)
                bot.reply_to(message, "تم حظر العضو من المجموعة.")
            elif text == "طرد":
                bot.ban_chat_member(chat_id, target_user.id)
                bot.unban_chat_member(chat_id, target_user.id)
                bot.reply_to(message, "تم طرد العضو من المجموعة.")
        except Exception as e:
            bot.reply_to(message, f"حدث خطأ أثناء تنفيذ الأمر: {e}")

print("البوت يعمل الآن بكفاءة!")
bot.infinity_polling()
