import os
import time
import random
import io
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response
import telebot
from telebot import types
from PIL import Image, ImageDraw, ImageFont
import database as db

# ==========================================
# CẤU HÌNH HỆ THỐNG
# ==========================================
RENDER_URL = "https://shop-ws1s.onrender.com"
MASTER_TOKEN = "8848756408:AAEAcpMvrbihm2n7LMN-nKC-UtKGd2Dgm4g"

app = FastAPI()
master_bot = telebot.TeleBot(MASTER_TOKEN, threaded=False)

# Cấu hình gói VIP chuẩn tư duy kinh doanh của mày
VIP_PACKAGES = {
    "vip0": {"name": "💎 VIP 0 (Thử nghiệm 1 Ngày)", "price": 0, "days": 1},
    "vip1": {"name": "💎 VIP 1 (1 Tuần)", "price": 30000, "days": 7},
    "vip2": {"name": "💎 VIP 2 (1 Tháng)", "price": 100000, "days": 30},
    "vip3": {"name": "💎 VIP 3 (1 Năm)", "price": 1000000, "days": 365},
    "vip4": {"name": "💎 VIP 4 (Vĩnh Viễn)", "price": 5000000, "days": 36500}
}

# Lưu trạng thái tạm thời cho quá trình tạo bot và captcha (Tránh ghi đè chéo user)
bot_creation_state = {}
captcha_storage = {} 

# ==========================================
# HÀM TẠO ẢNH CAPTCHA CHỨA 4 SỐ NGẪU NHIÊN
# ==========================================
def generate_captcha_image(text_code: str):
    # Tạo một ảnh nền màu xám nhạt kích thước 150x60
    img = Image.new('RGB', (150, 60), color=(230, 230, 230))
    d = ImageDraw.Draw(img)
    
    # Vẽ vài đường nhiễu để tránh bot auto quét
    for _ in range(5):
        x1 = random.randint(0, 150)
        y1 = random.randint(0, 60)
        x2 = random.randint(0, 150)
        y2 = random.randint(0, 60)
        d.line([(x1, y1), (x2, y2)], fill=(180, 180, 180), width=1)
        
    # Viết text chữ số lên ảnh (Sử dụng font mặc định của Pillow để tránh lỗi thiếu file font)
    d.text((45, 20), text_code, fill=(255, 0, 0))
    
    # Lưu ảnh vào bộ nhớ tạm BytesIO thay vì lưu file vật lý lên ổ đĩa Render
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

# ==========================================
# KHỞI ĐỘNG SERVER & WEBHOOK MASTER
# ==========================================
@app.on_event("startup")
async def on_startup():
    try:
        master_bot.delete_webhook()
        webhook_master_url = f"{RENDER_URL}/webhook/master"
        master_bot.set_webhook(url=webhook_master_url, drop_pending_updates=True)
        print(f"✅ Webhook Master đã kích hoạt thành công tại: {webhook_master_url}")
    except Exception as e:
        print(f"❌ Lỗi thiết lập Webhook Master: {e}")

# ==========================================
# LOGIC MASTER BOT
# ==========================================

# --- MENU CHÍNH ---
@master_bot.message_handler(commands=['start'])
def master_start(message):
    uid = message.from_user.id
    db.create_or_update_user(user_id=uid, username=message.from_user.username)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🤖 Tạo Bot Con"),
        types.KeyboardButton("▶️ Quản Lý Bot Con")
    )
    markup.add(
        types.KeyboardButton("💎 Mua Gói VIP"),
        types.KeyboardButton("💳 Nạp Tiền Hệ Thống")
    )
    markup.add(
        types.KeyboardButton("👤 Tài Khoản Cá Nhân"),
        types.KeyboardButton("☎️ Hỗ Trợ Kỹ Thuật")
    )
    
    msg_welcome = (
        "👋 <b>Chào mừng bạn đến với Hệ thống quản trị Bot tự động!</b>\n\n"
        "💡 <b>Tính năng nổi bật:</b>\n"
        "• Khởi tạo 3 cấu hình loại bot thông minh từ @BotFather.\n"
        "• Hệ thống kiểm soát tham gia nhóm bắt buộc & Xác thực Captcha hình ảnh chống clone.\n"
        "• Quản lý trạng thái On/Off của bot theo thời gian thực.\n\n"
        "<i>🔥 Mỗi tài khoản được kích hoạt dùng thử MIỄN PHÍ Gói VIP 0 trong vòng 1 ngày đầu tiên!</i>"
    )
    master_bot.send_message(message.chat.id, msg_welcome, parse_mode="HTML", reply_markup=markup)

# --- NÚT HỖ TRỢ ---
@master_bot.message_handler(func=lambda m: m.text == "☎️ Hỗ Trợ Kỹ Thuật")
def support_info(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 Nhắn Tin Cho Admin", url="https://t.me/truonggianhu")) # Thay link Telegram của mày vào đây
    
    msg = (
        "☎️ <b>HỖ TRỢ KỸ THUẬT & KHIẾU NẠI</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "• Nếu gặp lỗi trong quá trình nạp tiền tự động.\n"
        "• Cần tùy biến thêm các chức năng nâng cao cho bot con.\n"
        "• Gặp vấn đề về vận hành ứng dụng hoặc gia hạn gói cước.\n\n"
        "👉 Ấn nút bên dưới để kết nối trực tiếp với điều phối viên hệ thống!"
    )
    master_bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)

# --- THÔNG TIN TÀI KHOẢN ---
@master_bot.message_handler(func=lambda m: m.text == "👤 Tài Khoản Cá Nhân")
def acc_info(message):
    uid = message.from_user.id
    user = db.get_user(uid)
    if not user: return
        
    bots = db.get_bots_by_creator(str(uid))
    bot_count = len(bots)
    
    msg = (
        "👤 <b>THÔNG TIN HỘ CHIẾU TÀI KHOẢN</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"🆔 Tài khoản ID: <code>{uid}</code>\n"
        f"💰 Số dư khả dụng: <b>{user['balance']} VNĐ</b>\n"
        f"🤖 Số bot đang sở hữu: <b>{bot_count} bot</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "💳 Cú pháp nạp tiền tự động qua SePay:\n"
        f"Nội dung chuyển khoản: <code>NAP {uid}</code>"
    )
    master_bot.send_message(message.chat.id, msg, parse_mode="HTML")

# --- NẠP TIỀN QUA WEBHOOK SEPAY ---
@master_bot.message_handler(func=lambda m: m.text == "💳 Nạp Tiền Hệ Thống")
def deposit_info(message):
    uid = message.from_user.id
    bank_bin = "970416" # Mã ngân hàng ACB
    account_no = "49581007"
    account_name = "TRUONG GIA NHU"
    content = f"NAP {uid}"
    
    qr_url = f"https://img.vietqr.io/image/{bank_bin}-{account_no}-compact2.png?amount=30000&addInfo={content}&accountName={account_name}"
    
    msg = (
        "💳 <b>NẠP TIỀN TỰ ĐỘNG KHÔNG LỖI 24/7</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"🏦 Ngân hàng thụ hưởng: <b>ACB</b>\n"
        f"🔢 Số tài khoản: <b>{account_no}</b>\n"
        f"👤 Chủ tài khoản: <b>{account_name}</b>\n"
        f"📝 Nội dung bắt buộc: <code>NAP {uid}</code>\n"
        "━━━━━━━━━━━━━━━\n"
        "⚠️ <b>LƯU Ý:</b>\n"
        "Hệ thống quét nội dung tự động qua Webhook SePay sau 30 giây. Sai nội dung vui lòng liên hệ Admin qua nút Hỗ Trợ."
    )
    master_bot.send_photo(message.chat.id, photo=qr_url, caption=msg, parse_mode="HTML")

# --- MUA GÓI VIP ---
@master_bot.message_handler(func=lambda m: m.text == "💎 Mua Gói VIP")
def buy_vip_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, pkg in VIP_PACKAGES.items():
        markup.add(types.InlineKeyboardButton(f"{pkg['name']} - Giá: {pkg['price']}đ", callback_data=f"buyvip_{key}"))
        
    master_bot.send_message(message.chat.id, "🛒 <b>Chọn gói hạn định để kích hoạt thời gian hoạt động của Bot:</b>", parse_mode="HTML", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('buyvip_'))
def handle_buy_vip(call):
    uid = call.from_user.id
    vip_key = call.data.split('_')[1]
    pkg = VIP_PACKAGES.get(vip_key)
    if not pkg: return
    
    user = db.get_user(uid)
    if not user: return
    
    # Kiểm tra nếu mua gói free (VIP 0), check xem tài khoản từng sở hữu bot con nào chưa để tránh spam tạo acc clone ăn gian free
    if pkg['price'] == 0:
        bots = db.get_bots_by_creator(str(uid))
        if len(bots) > 0:
            master_bot.answer_callback_query(call.id, "❌ Gói dùng thử 1 ngày chỉ áp dụng cho lần đầu tạo bot con!", show_alert=True)
            return

    if user['balance'] < pkg['price']:
        master_bot.answer_callback_query(call.id, f"❌ Số dư không đủ! Bạn cần nạp thêm tiền. Giá gói: {pkg['price']} VNĐ.", show_alert=True)
        return
        
    # Thực hiện trừ tiền hệ thống
    new_bal = user['balance'] - pkg['price']
    db.update_user_balance(uid, new_bal)
    
    # Kéo và cộng hạn cho toàn bộ các bot con đang sở hữu
    bots = db.get_bots_by_creator(str(uid))
    exp_add = timedelta(days=pkg['days'])
    
    for b in bots:
        try:
            current_exp = datetime.fromisoformat(b['expired_at'].replace("Z", "+00:00"))
        except:
            current_exp = datetime.now(timezone.utc)
            
        if current_exp.timestamp() < time.time():
            current_exp = datetime.now()
            
        new_exp = (current_exp + exp_add).isoformat()
        db.update_sub_bot_data(b['bot_token'], {"expired_at": new_exp, "status": "running"})
        
    master_bot.answer_callback_query(call.id, f"✅ Giao dịch thành công {pkg['name']}!", show_alert=True)
    master_bot.send_message(call.message.chat.id, f"🎉 <b>Kích hoạt thành công gói cước {pkg['name']}!</b>\nToàn bộ hệ thống bot con của bạn được cộng thêm {pkg['days']} ngày hoạt động. Số dư còn: {new_bal} VNĐ.", parse_mode="HTML")

# --- QUẢN LÝ BOT CON ---
@master_bot.message_handler(func=lambda m: m.text == "▶️ Quản Lý Bot Con")
def manage_bots(message):
    uid = message.from_user.id
    bots = db.get_bots_by_creator(str(uid))
    
    if not bots:
        master_bot.send_message(message.chat.id, "❌ Hệ thống ghi nhận bạn chưa thiết lập bot con nào. Vui lòng bấm 'Tạo Bot Con'.")
        return
        
    markup = types.InlineKeyboardMarkup()
    for b in bots:
        token_prefix = b['bot_token'].split(':')[0] if ":" in b['bot_token'] else "Bot"
        status_icon = "🟢" if b['status'] == "running" else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status_icon} ID Bot: {token_prefix}", callback_data=f"managebot_{b['bot_token']}"))
        
    master_bot.send_message(message.chat.id, "📋 <b>Danh sách điều khiển mạng lưới bot con của bạn:</b>", parse_mode="HTML", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('managebot_'))
def bot_detail(call):
    token = call.data.split('_')[1]
    bot_data = db.get_sub_bot(token)
    if not bot_data: return
    
    status_text = "Đang chạy trực tuyến 🟢" if bot_data['status'] == "running" else "Đang tạm dừng ngoại tuyến 🔴"
    exp_date = bot_data.get('expired_at', 'N/A')[:19].replace("T", " ")
    
    config = bot_data.get('config_data') or {}
    b_type = config.get('bot_type', 'Chưa rõ')
    
    msg = (
        f"🤖 <b>CẤU HÌNH BOT CON CHI TIẾT</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔑 Token ID: <code>{token.split(':')[0]}</code>\n"
        f"⚙️ Phân loại: <b>{b_type.upper()}</b>\n"
        f"⏳ Thời hạn đóng gói: <code>{exp_date}</code>\n"
        f"📊 Tiến độ vận hành: <b>{status_text}</b>"
    )
    
    markup = types.InlineKeyboardMarkup()
    if bot_data['status'] == "running":
        markup.add(types.InlineKeyboardButton("🔴 Tạm Dừng Hoạt Động", callback_data=f"stopbot_{token}"))
    else:
        markup.add(types.InlineKeyboardButton("🟢 Bật Hoạt Động Trở Lại", callback_data=f"startbot_{token}"))
        
    markup.add(types.InlineKeyboardButton("⬅️ Quay Lại Danh Sách", callback_data="manage_back"))
    master_bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data == "manage_back")
def manage_back(call):
    manage_bots(call.message)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('stopbot_') or call.data.startswith('startbot_'))
def toggle_bot_status(call):
    action, token = call.data.split('_')
    new_status = "stopped" if action == "stopbot" else "running"
    db.update_sub_bot_status(token, new_status)
    master_bot.answer_callback_query(call.id, "✅ Thay đổi trạng thái vận hành thành công!")
    bot_detail(call)

# --- KHỞI TẠO BOT CON THEO 3 LOẠI VIDEO ---
@master_bot.message_handler(func=lambda m: m.text == "🤖 Tạo Bot Con")
def start_create_bot(message):
    uid = message.from_user.id
    bot_creation_state[uid] = {"step": 1}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🎁 1. Mời Bạn Bè Nhận Code", callback_data="type_code"),
        types.InlineKeyboardButton("💰 2. Mời Bạn Bè Kiếm Tiền", callback_data="type_money"),
        types.InlineKeyboardButton("🎮 3. Đổi Điểm TNV Nhận Quà Game", callback_data="type_game")
    )
    master_bot.send_message(message.chat.id, "⚙️ <b>VUI LÒNG CHỌN 1 TRONG 3 LOẠI BOT MUỐN KHỞI TẠO:</b>", parse_mode="HTML", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('type_'))
def process_bot_type(call):
    uid = call.from_user.id
    if uid not in bot_creation_state: return
    
    bot_type = call.data.split('_')[1]
    bot_creation_state[uid]["type"] = bot_type
    bot_creation_state[uid]["step"] = 2
    
    master_bot.send_message(call.message.chat.id, "👉 <b>Bây giờ hãy copy chuỗi Token từ @BotFather gửi vào đây:</b>", parse_mode="HTML")
    master_bot.answer_callback_query(call.id)

@master_bot.message_handler(func=lambda m: m.from_user.id in bot_creation_state and bot_creation_state[m.from_user.id]["step"] == 2)
def process_bot_token(message):
    uid = message.from_user.id
    token = message.text.strip()
    
    if ":" not in token:
        master_bot.send_message(message.chat.id, "❌ Định dạng chuỗi token sai quy chuẩn! Vui lòng kiểm tra lại cấu trúc từ @BotFather.")
        return
        
    try:
        test_bot = telebot.TeleBot(token)
        bot_info = test_bot.get_me()
        
        # Mặc định tặng 1 ngày dùng thử cho con bot đầu tiên (Gói VIP 0)
        exp_date = (datetime.now() + timedelta(days=1)).isoformat()
        
        bot_data = {
            "bot_token": token,
            "creator_id": str(uid),
            "admin_id": str(uid),
            "status": "running",
            "expired_at": exp_date,
            "users_list": [],
            "admins_list": [str(uid)],
            "channels_list": [],
            "codes_list": [],
            "ban_user_list": [],
            "invited_map": {},
            "userdata_map": {},
            "log_rutcode_list": [],
            "config_data": {"bot_type": bot_creation_state[uid]["type"], "ref_bonus": 1000, "min_rut": 10000}
        }
        db.save_sub_bot(bot_data)
        
        # Thiết lập đường dẫn Webhook cho Bot Con
        webhook_sub_url = f"{RENDER_URL}/webhook/sub/{token}"
        test_bot.remove_webhook()
        test_bot.set_webhook(url=webhook_sub_url, drop_pending_updates=True)
        
        del bot_creation_state[uid]
        master_bot.send_message(message.chat.id, f"✅ <b>KHỞI TẠO MẠNG LƯỚI THÀNH CÔNG!</b>\n🤖 Bot của bạn: @{bot_info.username}\n👉 Hãy truy cập vào link bot con và nhấn /start để tiến hành cấu hình quản trị.")
        
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ Không thể thiết lập Webhook cho Token này. Lỗi hệ thống: {e}")

# ==========================================
# LOGIC CORE VẬN HÀNH CHO TẤT CẢ BOT CON 
# ==========================================
def process_sub_bot_event(token: str, update_dict: dict):
    bot_info = db.get_sub_bot(token)
    if not bot_info or bot_info['status'] != 'running': return
        
    bot = telebot.TeleBot(token, threaded=False)
    update = types.Update.de_json(update_dict)
    
    # Check thời gian hết hạn bot con
    try:
        exp_time = datetime.fromisoformat(bot_info["expired_at"].replace("Z", "+00:00"))
        if datetime.now(exp_time.tzinfo) > exp_time:
            if update.message:
                bot.send_message(update.message.chat.id, "❌ Thiết bị Bot tạm thời ngừng hoạt động do hết thời hạn gói cước. Vui lòng liên hệ Admin hệ thống để gia hạn.")
            return
    except: pass

    # XỬ LÝ TIN NHẮN ĐẾN BOT CON
    if update.message:
        msg = update.message
        u_str = str(msg.from_user.id)
        
        users = bot_info.get("users_list") or []
        admins = bot_info.get("admins_list") or []
        channels = bot_info.get("channels_list") or []
        ban_users = bot_info.get("ban_user_list") or []
        invited = bot_info.get("invited_map") or {}
        userdata = bot_info.get("userdata_map") or {}
        codes = bot_info.get("codes_list") or []
        log_rutcode = bot_info.get("log_rutcode_list") or []
        config = bot_info.get("config_data") or {}
        
        if u_str in ban_users and u_str not in admins: return

        # XỬ LÝ LỆNH START / THAM GIA HOÀN TẤT NHÓM BẮT BUỘC
        if msg.text and msg.text.startswith("/start"):
            args = msg.text.split()
            if u_str not in users:
                users.append(u_str)
                userdata[u_str] = {"balance": 0, "verified": False}
                if len(args) > 1 and args[1] != u_str:
                    invited[u_str] = args[1]
                db.update_sub_bot_data(token, {"users_list": users, "invited_map": invited, "userdata_map": userdata})

            # Bước 1: Bắt buộc join toàn bộ kênh hệ thống chỉ định
            if channels:
                text = "🔍 <b>BẠN CẦN THAM GIA CÁC KÊNH SAU ĐỂ TIẾP TỤC:</b>\n"
                for ch in channels: text += f"\n💠 {ch}"
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("✅ Tôi đã tham gia đủ nhóm", callback_data="check_join_channels"))
                bot.send_message(msg.chat.id, text, parse_mode="HTML", reply_markup=markup)
            else:
                # Nếu không cài kênh bắt buộc thì nhảy thẳng vào xác thực captcha ảnh
                userdata[u_str]["verified"] = False
                db.update_sub_bot_data(token, {"userdata_map": userdata})
                trigger_captcha_flow(bot, msg.chat.id, u_str)
            return

        # XỬ LÝ KHI USER ĐANG TRONG TRẠNG THÁI CHỜ ĐIỀN CAPTCHA 4 SỐ
        if u_str in captcha_storage and msg.text:
            correct_code = captcha_storage[u_str]["code"]
            if msg.text.strip() == correct_code:
                # Giải phóng bộ nhớ tạm captcha
                ref_id = captcha_storage[u_str]["ref_id"]
                del captcha_storage[u_str]
                
                if u_str not in userdata: userdata[u_str] = {"balance": 0}
                userdata[u_str]["verified"] = True
                
                # Xử lý trả thưởng cho người giới thiệu nếu có
                if ref_id and ref_id in userdata:
                    bonus = config.get("ref_bonus", 1000)
                    userdata[ref_id]["balance"] = userdata.get(ref_id, {}).get("balance", 0) + bonus
                    try: bot.send_message(int(ref_id), f"🎉 <b>Tài khoản nhận thành công +{bonus}đ</b> hoa hồng từ việc mời thành viên mới tham gia mạng lưới!", parse_mode="HTML")
                    except: pass
                
                db.update_sub_bot_data(token, {"userdata_map": userdata})
                bot.send_message(msg.chat.id, "✅ <b>Xác thực thực thể thành công!</b> Chào mừng bạn gia nhập hệ thống ứng dụng.", parse_mode="HTML")
                send_sub_bot_main_menu(bot, msg.chat.id, config.get("bot_type", "code"))
            else:
                bot.send_message(msg.chat.id, "❌ <b>Mã Captcha không chính xác!</b> Hệ thống đang tái thiết lập mã xác thực mới, vui lòng nhập lại.")
                trigger_captcha_flow(bot, msg.chat.id, u_str)
            return

        # KIỂM TRA QUYỀN TRUY CẬP TÍNH NĂNG (BẮT BUỘC PHẢI XÁC THỰC XONG CAPTCHA MỚI CHO BẤM PHÍM CHỨC NĂNG)
        if not userdata.get(u_str, {}).get("verified", False) and u_str not in admins:
            bot.send_message(msg.chat.id, "⚠️ Vui lòng hoàn thành quy trình gõ lệnh /start và xác thực Captcha hình ảnh trước!")
            return

        # PHÍM CHỨC NĂNG DÀNH CHO USER ĐÃ XÁC THỰC
        if msg.text == "💰 Số dư của tôi":
            bal = userdata.get(u_str, {}).get("balance", 0)
            bot.send_message(msg.chat.id, f"💰 <b>Số dư hiện tại của bạn:</b> <code>{bal}</code> VNĐ", parse_mode="HTML")
            return
            
        elif msg.text == "📮 Mời Bạn Bè":
            link = f"https://t.me/{bot.get_me().username}?start={u_str}"
            bot.send_message(msg.chat.id, f"🔗 <b>Liên kết tiếp thị giới thiệu của bạn:</b>\n<code>{link}</code>\n\n🎁 Phần thưởng thực nhận: <b>{config.get('ref_bonus', 1000)}đ</b> trên mỗi thành viên xác thực vượt link thành công.")
            return
            
        elif msg.text in ["🛒 Rút Mã Code", "💵 Rút Tiền Mặt", "🎮 Đổi Phần Quà']:
            bot.send_message(msg.chat.id, f"👉 Vui lòng sử dụng cú pháp lệnh sau để thực hiện yêu cầu xử lý:\n<code>/rut {config.get('min_rut', 10000)}</code>", parse_mode="HTML")
            return

        # XỬ LÝ LỆNH RÚT DỰA TRÊN TỪNG LOẠI BOT
        if msg.text and msg.text.startswith("/rut"):
            args = msg.text.split()
            if len(args) < 2: return
            try: amount = int(args[1])
            except: return

            bal = userdata.get(u_str, {}).get("balance", 0)
            min_r = config.get("min_rut", 10000)
            
            if amount < min_r or bal < amount:
                bot.send_message(msg.chat.id, f"❌ Thao tác thất bại! Số dư không đủ điều kiện hoặc nhỏ hơn hạn mức tối thiểu {min_r}đ.")
                return
                
            b_type = config.get("bot_type", "code")
            if b_type == "code":
                if not codes:
                    bot.send_message(msg.chat.id, "⚠️ Kho hàng mã Code quà tặng tạm thời hết, vui lòng thông báo cho quản trị viên.")
                    return
                code_out = codes.pop(0)
                userdata[u_str]["balance"] -= amount
                log_rutcode.append({"user_id": u_str, "amount": amount, "type": "code", "gift": code_out})
                bot.send_message(msg.chat.id, f"🎉 <b>Rút thành công! Mã Quà Tặng Của Bạn:</b>\n<code>{code_out}</code>", parse_mode="HTML")
            else:
                userdata[u_str]["balance"] -= amount
                log_rutcode.append({"user_id": u_str, "amount": amount, "type": b_type, "status": "Pending"})
                bot.send_message(msg.chat.id, "✅ <b>Yêu cầu đã được gửi lên Ban Quản Trị!</b> Hệ thống sẽ xem xét và giải ngân trong vòng 24h.")

            db.update_sub_bot_data(token, {"codes_list": codes, "userdata_map": userdata, "log_rutcode_list": log_rutcode})
            return

        # ==========================================
        # CONTROL PANEL DÀNH CHO ADMIN BOT CON
        # ==========================================
        if u_str in admins:
            if msg.text == "/menu":
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("➕ Thêm Kênh Bắt Buộc", callback_data="admsub_addchannel"),
                    types.InlineKeyboardButton("🗑 Xóa Toàn Bộ Kênh", callback_data="admsub_delchannel"),
                    types.InlineKeyboardButton("📦 Thêm Kho Mã Code", callback_data="admsub_addcode"),
                    types.InlineKeyboardButton("💳 Cộng Tiền Thành Viên", callback_data="admsub_addmoney"),
                    types.InlineKeyboardButton("🚫 Khóa Tài Khoản", callback_data="admsub_banuser")
                )
                bot.send_message(msg.chat.id, "🛠 <b>BẢNG ĐIỀU KHIỂN CỦA QUẢN TRỊ VIÊN BOT:</b>", reply_markup=markup, parse_mode="HTML")
                return
                
            elif msg.text.startswith("/addchannel "):
                channels.append(msg.text.split()[1].strip())
                db.update_sub_bot_data(token, {"channels_list": channels})
                bot.send_message(msg.chat.id, "✅ Đã áp dụng cấu hình kênh bắt buộc mới thành công.")
                return
                
            elif msg.text.startswith("/addcode\n"):
                raw_lines = msg.text.split("\n")[1:]
                for line in raw_lines:
                    if line.strip(): codes.append(line.strip())
                db.update_sub_bot_data(token, {"codes_list": codes})
                bot.send_message(msg.chat.id, f"✅ Đã nạp thành công thêm {len(raw_lines)} mã code vào cơ sở dữ liệu.")
                return
                
            elif msg.text.startswith("/congtiem "):
                parts = msg.text.split()
                if len(parts) == 3:
                    target_id, money_amt = parts[1], int(parts[2])
                    if target_id not in userdata: userdata[target_id] = {"balance": 0, "verified": True}
                    userdata[target_id]["balance"] += money_amt
                    db.update_sub_bot_data(token, {"userdata_map": userdata})
                    bot.send_message(msg.chat.id, f"✅ Đã cộng tài sản thành công thêm {money_amt}đ cho ID {target_id}.")
                return

    # XỬ LÝ SỰ KIỆN CALLBACK BUTTONS TRÊN BOT CON
    elif update.callback_query:
        call = update.callback_query
        u_str = str(call.from_user.id)
        
        bot_info = db.get_sub_bot(token)
        userdata = bot_info.get("userdata_map") or {}
        channels = bot_info.get("channels_list") or []
        invited = bot_info.get("invited_map") or {}
        
        if call.data == "check_join_channels":
            # Chuyển tiếp sang bước xác thực Captcha hình ảnh 4 số
            userdata[u_str]["verified"] = False
            db.update_sub_bot_data(token, {"userdata_map": userdata})
            trigger_captcha_flow(bot, call.message.chat.id, u_str)
            bot.answer_callback_query(call.id)
            
        elif call.data.startswith("admsub_"):
            action = call.data.replace("admsub_", "")
            syntax = {
                "addchannel": "<code>/addchannel @TenKenhCuaBan</code>",
                "delchannel": "<i>Chức năng đang cập nhật tự động</i>",
                "addcode": "Cú pháp nạp mã số hàng loạt:\n<code>/addcode\nMAMA1\nMAMA2\nMAMA3</code>",
                "addmoney": "<code>/congtiem ID_USER SỐ_TIỀN</code>",
                "banuser": "<code>/ban ID_USER</code>"
            }
            bot.send_message(call.message.chat.id, f"✏️ <b>Hướng dẫn cú pháp Admin:</b>\n{syntax.get(action, '')}", parse_mode="HTML")
            bot.answer_callback_query(call.id)

# --- TRÌNH XỬ LÝ CAPTCHA ĐỘC LẬP CHỐNG SPAM ---
def trigger_captcha_flow(bot, chat_id, user_id_str):
    # Tạo ngẫu nhiên 4 chữ số
    captcha_text = str(random.randint(1000, 9999))
    
    # Lấy thông tin người giới thiệu tạm thời ra
    bot_info = db.get_sub_bot(bot.token)
    invited_map = bot_info.get("invited_map") or {}
    ref_id = invited_map.get(user_id_str, None)
    
    # Lưu thông tin captcha vào bộ nhớ RAM tạm thời của server Render
    captcha_storage[user_id_str] = {
        "code": captcha_text,
        "ref_id": ref_id
    }
    
    # Sinh ảnh vẽ text số từ Pillow
    photo_stream = generate_captcha_image(captcha_text)
    
    bot.send_photo(
        chat_id, 
        photo=photo_stream, 
        caption="🤖 <b>HỆ THỐNG XÁC THỰC CAPTCHA HÌNH ẢNH</b>\n━━━━━━━━━━━━━━━\n👉 Vui lòng nhìn hình ảnh phía trên và điền lại chính xác 4 chữ số xuất hiện trong ảnh để mở khóa bàn phím chức năng bot con!",
        parse_mode="HTML"
    )

def send_sub_bot_main_menu(bot, chat_id, bot_type):
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if bot_type == "code":
        menu.row("💰 Số dư của tôi", "🛒 Rút Mã Code")
    elif bot_type == "money":
        menu.row("💰 Số dư của tôi", "💵 Rút Tiền Mặt")
    else:
        menu.row("💰 Số dư của tôi", "🎮 Đổi Phần Quà")
    menu.row("📮 Mời Bạn Bè")
    bot.send_message(chat_id, "🎛 <b>BÀN PHÍM CHỨC NĂNG ĐÃ ĐƯỢC MỞ KHÓA:</b>", reply_markup=menu, parse_mode="HTML")

# ==========================================
# CÁC ROUTE CỔNG ĐÓN WEBHOOK TỪ FASTAPI
# ==========================================
@app.post("/webhook/master")
async def handle_master_webhook(request: Request):
    try:
        json_data = await request.json()
        update = types.Update.de_json(json_data)
        master_bot.process_new_updates([update])
    except Exception as e:
        print(f"Lỗi cổng webhook master: {e}")
    return Response(status_code=200)

@app.post("/webhook/sub/{token}")
async def handle_sub_webhook(token: str, request: Request):
    try:
        json_data = await request.json()
        process_sub_bot_event(token, json_data)
    except Exception as e:
        print(f"Lỗi cổng webhook bot con: {e}")
    return Response(status_code=200)

@app.post("/webhook/sepay")
async def handle_sepay_webhook(request: Request):
    try:
        data = await request.json()
        content = data.get("content", "")
        amount = int(data.get("amount", 0))
        
        if "NAP" in content.upper():
            parts = content.split()
            for part in parts:
                if part.isdigit():
                    target_user_id = int(part)
                    new_bal = db.create_or_update_user(target_user_id, balance_add=amount)
                    try:
                        master_bot.send_message(target_user_id, f"🔔 <b>Hệ thống SePay thông báo:</b> Tài khoản của bạn đã được cộng tự động thành công +<code>{amount}</code> VNĐ. Số dư hiện tại: {new_bal} VNĐ.", parse_mode="HTML")
                    except: pass
                    break
    except Exception as e:
        print(f"Lỗi đồng bộ xử lý webhook từ SePay: {e}")
    return Response(status_code=200)

@app.get("/")
def home_check():
    return {"status": "online", "message": "Hệ thống cổng tổng kết nối an toàn 100% không lỗi lầm."}
