import os
import sys
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Logging konfiqurasiyası
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

# Log environment variables
logger.info("🚀 Bot başladılır...")
logger.info(f"📋 ADMIN_ID: {ADMIN_ID}")
logger.info(f"🔐 BOT_TOKEN mövcuddur: {bool(BOT_TOKEN)}")

# Müvəqqəti məlumatlar üçün dictionary
user_data = {}
admin_messages = {}
withdrawal_requests = {}

# Əsas menyu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("💰 Depozit", callback_data="deposit")],
        [InlineKeyboardButton("💸 Çıxarış", callback_data="withdraw")],
        [InlineKeyboardButton("📞 Əlaqə", callback_data="contact")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(
            f"👋 Salam {user.first_name}!\n"
            "Tezbazar Kassa vasitəsilə 1xBet hesabınıza sürətli və təhlükəsiz depozit və ya hesabınızdan çıxarış edə bilərsiniz!\n"
            "✅ Komissiya yoxdur.\n\n"
            "Aşağıdakı əməliyyatlardan birini seçin:",
            reply_markup=reply_markup
        )
    else:
        await update.callback_query.edit_message_text(
            f"👋 Salam {user.first_name}!\n"
            "Tezbazar Kassa vasitəsilə 1xBet hesabınıza sürətli və təhlükəsiz depozit və ya hesabınızdan çıxarış edə bilərsiniz!\n"
            "✅ Komissiya yoxdur.\n\n"
            "Aşağıdakı əməliyyatlardan birini seçin:",
            reply_markup=reply_markup
        )

# Buton handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "deposit":
        await query.edit_message_text(
            "💰 Depozit əməliyyatı üçün 1xBet hesab ID-nizi daxil edin:\n",
            parse_mode='HTML'
        )
        context.user_data['awaiting_1xbet_id'] = True
        context.user_data['current_action'] = 'deposit'
        
    elif data == "withdraw":
        await query.edit_message_text(
            "💸 Çıxarış əməliyyatı üçün 1xBet hesab ID-nizi daxil edin:\n",
            parse_mode='HTML'
        )
        context.user_data['awaiting_1xbet_id'] = True
        context.user_data['current_action'] = 'withdraw'
        
    elif data == "contact":
        await query.edit_message_text(
            "📞 Bizimlə əlaqə saxlamaq üçün mesajınızı yazın:\n"
            "(Sual, təklif və ya hər hansı problem barədə məlumat yaza bilərsiniz)",
            parse_mode='HTML'
        )
        context.user_data['awaiting_contact_message'] = True
    
    # Admin butonları
    elif data.startswith('admin_'):
        await handle_admin_actions(update, context, data)

# Admin əməliyyatlarını idarə et
async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    await query.answer()
    
    try:
        logger.info(f"Admin əməliyyatı: {data}")
        
        parts = data.split('_')
        logger.info(f"Parts: {parts}, Length: {len(parts)}")
        
        # Format: admin_confirm_id_12345
        if len(parts) != 4:
            await query.message.reply_text("❌ Xəta: Keçərsiz əməliyyat formatı!")
            return
        
        # Hissələri təhlil et
        action = parts[1]  # confirm və ya reject
        action_type = parts[2]  # id, receipt, withdraw
        target_user_id = int(parts[3])  # istifadəçi ID-si
        
        logger.info(f"Action: {action}, Type: {action_type}, Target User: {target_user_id}")
        
        if action_type == 'id':
            user_info = user_data.get(target_user_id)
            if not user_info:
                await query.message.reply_text("❌ İstifadəçi məlumatı tapılmadı!")
                return
            
            user_1xbet_id = user_info['1xbet_id']
            
            if action == 'confirm':
                # Admin mesajını gözlə
                admin_messages[query.from_user.id] = {
                    'type': 'id_confirm',
                    'target_user_id': target_user_id,
                    'message_id': query.message.message_id
                }
                
                await query.edit_message_text(
                    f"✅ 1xBet ID təsdiqləndi: {user_1xbet_id}\n"
                    f"👤 İstifadəçi: {user_info['first_name']}\n\n"
                    "Zəhmət olmasa istifadəçiyə göndəriləcək mesajı yazın:",
                    parse_mode='HTML'
                )
                
            elif action == 'reject':
                # İstifadəçiyə rədd mesajı göndər
                try:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text="❌ 1xBet hesab ID-niz yanlışdır!\n\nƏsas menyuya qayıtmaq üçün /start yazın."
                    )
                except Exception as e:
                    logger.error(f"İstifadəçiyə mesaj göndərilmədi: {e}")
                
                await query.edit_message_text(
                    f"❌ 1xBet ID rədd edildi: {user_1xbet_id}\n"
                    f"👤 İstifadəçi: {user_info['first_name']}",
                    parse_mode='HTML'
                )
                
                # Məlumatları təmizlə
                user_data.pop(target_user_id, None)
        
        elif action_type == 'receipt':
            user_info = user_data.get(target_user_id)
            if not user_info:
                await query.message.reply_text("❌ İstifadəçi məlumatı tapılmadı!")
                return
            
            user_1xbet_id = user_info['1xbet_id']
            
            if action == 'confirm':
                # Admin mesajını gözlə
                admin_messages[query.from_user.id] = {
                    'type': 'receipt_confirm',
                    'target_user_id': target_user_id,
                    'message_id': query.message.message_id
                }
                
                # Şəkil mesajıdırsa, yeni mesaj göndər
                if query.message.photo:
                    await query.message.reply_text(
                        f"✅ Qəbz təsdiqləndi: {user_1xbet_id}\n"
                        f"👤 İstifadəçi: {user_info['first_name']}\n\n"
                        "Zəhmət olmasa köçürmə haqqında mesajı yazın:",
                        parse_mode='HTML'
                    )
                else:
                    await query.edit_message_text(
                        f"✅ Qəbz təsdiqləndi: {user_1xbet_id}\n"
                        f"👤 İstifadəçi: {user_info['first_name']}\n\n"
                        "Zəhmət olmasa köçürmə haqqında mesajı yazın:",
                        parse_mode='HTML'
                    )
                
            elif action == 'reject':
                # İstifadəçiyə rədd mesajı göndər
                try:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text="❌ Qəbziniz keçərli deyil!\n\nƏsas menyuya qayıtmaq üçün /start yazın."
                    )
                except Exception as e:
                    logger.error(f"İstifadəçiyə mesaj göndərilmədi: {e}")
                
                # Şəkil mesajıdırsa, yeni mesaj göndər
                if query.message.photo:
                    await query.message.reply_text(
                        f"❌ Qəbz rədd edildi: {user_1xbet_id}\n"
                        f"👤 İstifadəçi: {user_info['first_name']}",
                        parse_mode='HTML'
                    )
                else:
                    await query.edit_message_text(
                        f"❌ Qəbz rədd edildi: {user_1xbet_id}\n"
                        f"👤 İstifadəçi: {user_info['first_name']}",
                        parse_mode='HTML'
                    )
                
                # Məlumatları təmizlə
                user_data.pop(target_user_id, None)
        
        elif action_type == 'withdraw':
            withdrawal_info = withdrawal_requests.get(target_user_id)
            if not withdrawal_info:
                await query.message.reply_text("❌ Çıxarış sorğusu tapılmadı!")
                return
            
            user_info = user_data.get(target_user_id)
            if not user_info:
                await query.message.reply_text("❌ İstifadəçi məlumatı tapılmadı!")
                return
                
            if action == 'confirm':
                # İstifadəçiyə təsdiq mesajı göndər
                try:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text="✅ <b>Çıxarışınız təsdiqləndi.</b>\n\n"
                             "💰 <b>Ən tez 2-3 dəqiqə, ən gec 24 saat ərzində hesabınıza yüklənəcək.</b>\n\n"
                             "Əsas menyuya qayıtmaq üçün /start yazın.",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"İstifadəçiyə mesaj göndərilmədi: {e}")
                
                await query.edit_message_text(
                    f"✅ Çıxarış təsdiqləndi!\n"
                    f"👤 İstifadəçi: {user_info['first_name']}\n"
                    f"🔹 1xBet ID: {withdrawal_info['1xbet_id']}\n"
                    f"💸 Məbləğ: {withdrawal_info['amount']} AZN\n"
                    f"🏦 Köçürmə: {withdrawal_info['account_info']}",
                    parse_mode='HTML'
                )
                
                # Çıxarış məlumatlarını təmizlə
                withdrawal_requests.pop(target_user_id, None)
                
            elif action == 'reject':
                # Admin mesajını gözlə
                admin_messages[query.from_user.id] = {
                    'type': 'withdraw_reject',
                    'target_user_id': target_user_id,
                    'message_id': query.message.message_id
                }
                
                await query.edit_message_text(
                    f"❌ Çıxarış rədd edildi: {withdrawal_info['1xbet_id']}\n"
                    f"👤 İstifadəçi: {user_info['first_name']}\n\n"
                    "Zəhmət olmasa istifadəçiyə göndəriləcək səbəbi yazın:",
                    parse_mode='HTML'
                )
                
    except ValueError as e:
        logger.error(f"User ID convert xətası: {e}")
        await query.message.reply_text("❌ Keçərsiz istifadəçi ID-si!")
    except Exception as e:
        logger.error(f"Admin əməliyyatında xəta: {e}")
        await query.message.reply_text("❌ Əməliyyat zamanı xəta baş verdi!")

# İstifadəçi mesajlarını idarə et
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Əlaqə mesajı qəbulu
    if context.user_data.get('awaiting_contact_message'):
        context.user_data['awaiting_contact_message'] = False
        
        # Əlaqə mesajını adminə göndər
        await send_contact_to_admin(update, context, user_id, text)
        
        await update.message.reply_text(
            "✅ Mesajınız adminlərə göndərildi!\n"
            "⏳ Cavab gözləyin...\n\n"
            "Əsas menyuya qayıtmaq üçün /start yazın."
        )
        return
    
    # 1xBet ID qəbulu (həm depozit, həm də çıxarış üçün)
    if context.user_data.get('awaiting_1xbet_id'):
        if text.isdigit():
            context.user_data['awaiting_1xbet_id'] = False
            user_1xbet_id = text
            
            # İstifadəçi məlumatlarını saxla
            user_data[user_id] = {
                '1xbet_id': user_1xbet_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'awaiting_receipt': False
            }
            
            current_action = context.user_data.get('current_action')
            
            if current_action == 'deposit':
                # Adminə bildir
                await send_to_admin(update, context, user_id, user_1xbet_id)
                
                await update.message.reply_text(
                    f"✅ 1xBet ID-niz qəbul edildi: {user_1xbet_id}\n"
                    "⏳ Adminlərin təsdiqini gözləyin..."
                )
                
            elif current_action == 'withdraw':
                context.user_data['awaiting_withdraw_code'] = True
                await update.message.reply_text(
                    f"✅ 1xBet ID-niz qəbul edildi: {user_1xbet_id}\n\n"
                    "🔐 Zəhmət olmasa çıxarış kodunuzu daxil edin:\n"
                )
            
        else:
            await update.message.reply_text(
                "❌ 1xBet ID yalnız rəqəmlərdən ibarət olmalıdır!\n"
                "Zəhmət olmasa yenidən daxil edin:"
            )
    
    # Çıxarış kodu qəbulu
    elif context.user_data.get('awaiting_withdraw_code'):
        context.user_data['awaiting_withdraw_code'] = False
        context.user_data['awaiting_withdraw_amount'] = True
        context.user_data['withdraw_code'] = text
        
        await update.message.reply_text(
            f"✅ Çıxarış kodu qəbul edildi.\n\n"
            "💰 Zəhmət olmasa çıxarış etmək istədiyiniz məbləği daxil edin:\n"
        )
    
    # Çıxarış məbləği qəbulu
    elif context.user_data.get('awaiting_withdraw_amount'):
        try:
            amount = float(text)
            if amount < 10:
                await update.message.reply_text(
                    "❌ Minimum çıxarış məbləği 10 AZN-dir!\n"
                    "Zəhmət olmasa yenidən daxil edin:"
                )
                return
            
            context.user_data['awaiting_withdraw_amount'] = False
            context.user_data['awaiting_account_info'] = True
            context.user_data['withdraw_amount'] = amount
            
            await update.message.reply_text(
                f"✅ Məbləğ qəbul edildi: {amount} AZN\n\n"
                "🏦 Zəhmət olmasa köçürmə ediləcək bank kartı və ya M10 hesab nömrəsini daxil edin:\n"
                "Nümunə: <code>4169 7381 2345 6789</code> və ya <code>M10 1234567890</code>",
                parse_mode='HTML'
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ Zəhmət olmasa düzgün rəqəm daxil edin!\n"
                "Nümunə: <code>25.50</code> və ya <code>100</code>",
                parse_mode='HTML'
            )
    
    # Bank hesab məlumatı qəbulu
    elif context.user_data.get('awaiting_account_info'):
        account_info = text
        context.user_data['awaiting_account_info'] = False
        
        user_info = user_data.get(user_id)
        withdraw_code = context.user_data.get('withdraw_code')
        withdraw_amount = context.user_data.get('withdraw_amount')
        
        if user_info and withdraw_code and withdraw_amount:
            # Çıxarış sorğusunu adminə göndər
            await send_withdrawal_to_admin(update, context, user_id, user_info['1xbet_id'], 
                                         withdraw_code, withdraw_amount, account_info)
            
            # Context məlumatlarını təmizlə
            context.user_data.pop('withdraw_code', None)
            context.user_data.pop('withdraw_amount', None)
            context.user_data.pop('current_action', None)
            
            await update.message.reply_text(
                "✅ Çıxarış sorğunuz adminlərə göndərildi!\n"
                "⏳ Təsdiq gözləyin..."
            )
        else:
            await update.message.reply_text("❌ Xəta baş verdi! /start yazaraq yenidən başlayın.")

# Admin mesajlarını idarə et
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Admin mesajını yoxla
    admin_message_data = admin_messages.get(user_id)
    if admin_message_data:
        target_user_id = admin_message_data['target_user_id']
        user_info = user_data.get(target_user_id)
        
        if not user_info:
            await update.message.reply_text("❌ İstifadəçi məlumatı tapılmadı!")
            admin_messages.pop(user_id, None)
            return
        
        if admin_message_data['type'] == 'id_confirm':
            # İstifadəçiyə mesaj göndər (HTML formatında)
            user_message = (
                f"🔹 <b>1xBet ID:</b> {user_info['1xbet_id']}\n"
                f"✅ <b>1xBet hesab adı:</b> {text}\n\n"
                "💰 <b>Min depozit: 5 AZN</b>\n"
                "💳 Ödəniş etdikdən sonra mütləq qəbzin şəkilini göndərin!"
            )
            
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=user_message,
                    parse_mode='HTML'
                )
                
                # İstifadəçini qəbz göndərməyə hazırla
                user_data[target_user_id]['awaiting_receipt'] = True
                
                await update.message.reply_text(
                    f"✅ Mesaj istifadəçiyə göndərildi!\n"
                    f"👤 İstifadəçi: {user_info['first_name']}\n"
                    f"📨 Göndərilən mesaj: {text}"
                )
                
            except Exception as e:
                await update.message.reply_text(f"❌ İstifadəçiyə mesaj göndərilmədi: {e}")
            
            # Admin state-lərini təmizlə
            admin_messages.pop(user_id, None)
        
        elif admin_message_data['type'] == 'receipt_confirm':
            # İstifadəçiyə köçürmə mesajı göndər (HTML formatında)
            user_message = (
                f"✅ <b>1xBet : {user_info['1xbet_id']}</b>\n"
                f"hesabın balansına köçürüldü!\n\n"
                f"📋 <b>Qeyd:</b> {text}"
            )
            
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=user_message,
                    parse_mode='HTML'
                )
                
                await update.message.reply_text(
                    f"✅ Köçürmə tamamlandı!\n"
                    f"👤 İstifadəçi: {user_info['first_name']}\n"
                    f"🔹 1xBet ID: {user_info['1xbet_id']}\n"
                    f"📨 Mesaj: {text}"
                )
                
            except Exception as e:
                await update.message.reply_text(f"❌ İstifadəçiyə mesaj göndərilmədi: {e}")
            
            # Bütün məlumatları təmizlə
            user_data.pop(target_user_id, None)
            admin_messages.pop(user_id, None)
        
        elif admin_message_data['type'] == 'withdraw_reject':
            # İstifadəçiyə rədd mesajı göndər (HTML formatında)
            withdrawal_info = withdrawal_requests.get(target_user_id)
            
            user_message = (
                f"❌ <b>Çıxarış sorğunuz rədd edildi:</b>\n\n"
                f"📋 <b>Səbəb:</b> {text}\n\n"
                f"Əsas menyuya qayıtmaq üçün /start yazın."
            )
            
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=user_message,
                    parse_mode='HTML'
                )
                
                await update.message.reply_text(
                    f"✅ Rədd mesajı istifadəçiyə göndərildi!\n"
                    f"👤 İstifadəçi: {user_info['first_name']}\n"
                    f"📨 Göndərilən səbəb: {text}"
                )
                
            except Exception as e:
                await update.message.reply_text(f"❌ İstifadəçiyə mesaj göndərilmədi: {e}")
            
            # Çıxarış məlumatlarını təmizlə
            withdrawal_requests.pop(target_user_id, None)
            admin_messages.pop(user_id, None)
    
    else:
        # Admin reply mesajını yoxla (əlaqə mesajlarına cavab)
        if update.message.reply_to_message:
            replied_message = update.message.reply_to_message
            replied_text = replied_message.text
            
            # Əlaqə mesajı olub-olmadığını yoxla
            if replied_text and "📩 Yeni Əlaqə Mesajı" in replied_text:
                # İstifadəçi ID-sini tap
                lines = replied_text.split('\n')
                user_id_line = next((line for line in lines if "Telegram ID:" in line), None)
                if user_id_line:
                    target_user_id = int(user_id_line.split(":")[1].strip())
                    
                    # İstifadəçiyə cavab göndər (HTML formatında)
                    user_message = (
                        f"📨 <b>Admin cavabı:</b>\n\n"
                        f"{text}\n\n"
                        f"Əsas menyuya qayıtmaq üçün /start yazın."
                    )
                    
                    try:
                        await context.bot.send_message(
                            chat_id=target_user_id,
                            text=user_message,
                            parse_mode='HTML'
                        )
                        
                        await update.message.reply_text(
                            f"✅ Cavab istifadəçiyə göndərildi!\n"
                            f"👤 İstifadəçi ID: {target_user_id}\n"
                            f"📨 Göndərilən cavab: {text}"
                        )
                        
                    except Exception as e:
                        await update.message.reply_text(f"❌ İstifadəçiyə cavab göndərilmədi: {e}")
                else:
                    await update.message.reply_text("❌ İstifadəçi ID-si tapılmadı!")
            else:
                await update.message.reply_text("Admin paneli üçün /start yazın")
        else:
            # Əgər admin adi mesaj yazırsa
            await update.message.reply_text("Admin paneli üçün /start yazın")

# Şəkil mesajlarını idarə et (qəbzlər)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Qəbz şəklini yoxla
    user_info = user_data.get(user_id)
    if user_info and user_info.get('awaiting_receipt'):
        receipt_photo = update.message.photo[-1].file_id
        user_1xbet_id = user_info['1xbet_id']
        
        # Qəbzi adminə göndər
        await send_receipt_to_admin(update, context, user_id, user_1xbet_id, receipt_photo)
        
        user_info['awaiting_receipt'] = False
        
        await update.message.reply_text(
            "✅ Qəbziniz adminlərə göndərildi!\n"
            "⏳ Təsdiq gözləyin..."
        )
    else:
        await update.message.reply_text("❌ Əvvəlcə depozit əməliyyatına başlayın!")

# Adminə 1xBet ID göndərmə
async def send_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, user_1xbet_id: str):
    user_info = user_data[user_id]
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Təsdiq et", callback_data=f"admin_confirm_id_{user_id}"),
            InlineKeyboardButton("❌ Rədd et", callback_data=f"admin_reject_id_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        "🆕 <b>Yeni Depozit Sorğusu</b>\n\n"
        f"👤 İstifadəçi: {user_info['first_name']}\n"
        f"🔹 Username: @{user_info['username'] or 'Yoxdur'}\n"
        f"🔹 Telegram ID: {user_id}\n"
        f"🔸 1xBet ID: {user_1xbet_id}\n\n"
        "Əməliyyatı təsdiq edin və ya rədd edin:"
    )
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Adminlərə mesaj göndərilmədi: {e}")

# Adminə qəbz göndərmə
async def send_receipt_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, user_1xbet_id: str, receipt_photo: str):
    user_info = user_data[user_id]
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Təsdiq et", callback_data=f"admin_confirm_receipt_{user_id}"),
            InlineKeyboardButton("❌ Rədd et", callback_data=f"admin_reject_receipt_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    caption = (
        "🆕 <b>Yeni Qəbz</b>\n\n"
        f"👤 İstifadəçi: {user_info['first_name']}\n"
        f"🔹 1xBet ID: {user_1xbet_id}\n\n"
        "Qəbzi təsdiq edin və ya rədd edin:"
    )
    
    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=receipt_photo,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Adminlərə şəkil göndərilmədi: {e}")

# Adminə çıxarış sorğusu göndərmə
async def send_withdrawal_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, 
                                 user_1xbet_id: str, withdraw_code: str, amount: float, account_info: str):
    user_info = user_data[user_id]
    
    # Çıxarış sorğusunu saxla
    withdrawal_requests[user_id] = {
        '1xbet_id': user_1xbet_id,
        'withdraw_code': withdraw_code,
        'amount': amount,
        'account_info': account_info
    }
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Təsdiq et", callback_data=f"admin_confirm_withdraw_{user_id}"),
            InlineKeyboardButton("❌ Rədd et", callback_data=f"admin_reject_withdraw_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        "🆕 <b>Yeni Çıxarış Sorğusu</b>\n\n"
        f"👤 İstifadəçi: {user_info['first_name']}\n"
        f"🔹 Username: @{user_info['username'] or 'Yoxdur'}\n"
        f"🔹 Telegram ID: {user_id}\n"
        f"🔸 1xBet ID: {user_1xbet_id}\n"
        f"🔐 Çıxarış Kodu: {withdraw_code}\n"
        f"💰 Məbləğ: {amount} AZN\n"
        f"🏦 Köçürmə: {account_info}\n\n"
        "Əməliyyatı təsdiq edin və ya rədd edin:"
    )
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Adminlərə çıxarış sorğusu göndərilmədi: {e}")

# Adminə əlaqə mesajı göndərmə
async def send_contact_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, message: str):
    user = update.effective_user
    
    message_text = (
        "📩 <b>Yeni Əlaqə Mesajı</b>\n\n"
        f"👤 İstifadəçi: {user.first_name}\n"
        f"🔹 Username: @{user.username or 'Yoxdur'}\n"
        f"🔹 Telegram ID: {user_id}\n\n"
        f"💬 <b>Mesaj:</b>\n{message}\n\n"
        f"ℹ️ <b>Cavab vermək üçün bu mesaja reply edin</b>"
    )
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=message_text,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Adminlərə əlaqə mesajı göndərilmədi: {e}")

# Xəta handler funksiyası
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xətaları idarə et"""
    logger.error(f"Bot xətası: {context.error}")
    
    try:
        # İstifadəçiyə xəta mesajı göndər
        if update and update.effective_user:
            await update.effective_user.send_message(
                "❌ Əməliyyat zamanı xəta baş verdi. Zəhmət olmasa bir az sonra yenidən cəhd edin."
            )
    except Exception as e:
        logger.error(f"Xəta mesajı göndərilmədi: {e}")

def main():
    logger.info("🤖 Bot main funksiyası başladı...")
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN təyin edilməyib!")
        print("❌ BOT_TOKEN təyin edilməyib!")
        return
    
    if ADMIN_ID == 0:
        logger.error("❌ ADMIN_ID təyin edilməyib!")
        print("❌ ADMIN_ID təyin edilməyib!")
        return
    
    try:
        # Bot tətbiqini yarat
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Handler-ları əlavə et
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.User(ADMIN_ID), handle_user_message))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), handle_admin_message))
        application.add_handler(MessageHandler(filters.PHOTO & ~filters.User(ADMIN_ID), handle_photo))
        
        # Xəta handler
        application.add_error_handler(error_handler)
        
        logger.info("✅ Bot uğurla quruldu!")
        logger.info("🚀 Render.com serverində işə salınır...")
        
        print("🤖 Bot işə salındı!")
        print(f"👑 Admin ID: {ADMIN_ID}")
        
        # Botu işə sal
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Bot başladıla bilmədi: {e}")
        print(f"❌ XƏTA: {e}")

if __name__ == '__main__':
    main()
