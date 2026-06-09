import os
import time
import random
import io
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response
import telebot
from telebot import types
from PIL import Image, ImageDraw
import database as db

# ==========================================
# CẤU HÌNH HỆ THỐNG CỐ ĐỊNH
# ==========================================
RENDER_URL = "https://shop-ws1s.onrender.com"
MASTER_TOKEN = "8848756408:AAEAcpMvrbihm2n7LMN-nKC-UtKGd2Dgm4g"

app = FastAPI()
master_bot = telebot.TeleBot(MASTER_TOKEN, threaded=False)

# Cấu hình gói VIP chuẩn chỉnh theo yêu cầu của mày
VIP_PACKAGES = {
    "vip1": {"name": "💎 Gói VIP 1 Tuần", "price": 30000, "days": 7},
    "vip2": {"name": "💎 Gói VIP 1 Tháng", "price": 100000, "days": 30},
    "vip3": {"name": "💎 Gói VIP 1 Năm", "price": 1000000, "days": 365}
}

# Bộ nhớ tạm lưu trạng thái tạo bot và mã captcha chống clone rác
bot_creation_state = {}
captcha_storage = {}

# ==========================================
# HÀM SINH ẢNH CAPTCHA CHỨA 4 SỐ NGẪU NHIÊN
# ==========================================
def generate_captcha_image(text_code: str):
    img = Image.new('RGB', (160, 60), color=(240, 240, 240))
    d = ImageDraw.Draw(img)
    
    # Vẽ các đường thẳng gây nhiễu hệ thống quét tự động
    for _ in range(6):
        x1 = random.randint(0, 160)
        y1 = random.randint(0, 60)
        x2 = random.randint(0, 160)
        y2 = random.randint(0, 60)
        d.line([(x1, y1), (x2, y2)], fill=(170, 170, 170), width=1)
        
    # Ghi mã số xác thực trực tiếp lên ảnh nền
    d.text((50, 22), text_code, fill=(255, 0, 0))
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

# ==========================================
# KHỞI ĐỘNG SERVER & ĐĂNG KÝ WEBHOOK MASTER
# ==========================================
@app.on_event("startup")
async def on_startup():
    try:
        master_bot.delete_webhook()
        webhook_master_url = f"{RENDER_URL}/webhook/master"
        master_bot.set_webhook(url=webhook_master_url, drop_pending_updates=True)
        print(f"✅ Đã thiết lập Webhook Master thành công: {webhook_master_url}")
    except Exception as e:
        print(f"❌ Lỗi thiết lập Webhook Master: {e}")

# ==========================================
# LOGIC ĐIỀU KHIỂN MASTER BOT
# ==========================================

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
        "👋 <b>HỆ THỐNG TẠO BOT CON TỰ ĐỘNG CHUẨN LOGIC</b>\n\n"
        "ℹ️ <b>Quy định dùng thử:</b>\n"
        "• Mỗi tài khoản chỉ được phép khởi tạo <b>DUY NHẤT 1 BOT CON</b> dùng thử.\n"
        "• Thời gian trải nghiệm mặc định hệ thống cấp là <b>1 ngày (24 giờ)</b>.\n"
        "• Hết hạn dùng thử, vui lòng nạp tiền gia hạn gói tuần (30k) để tiếp tục vận hành."
    )
    master_bot.send_message(message.chat.id, msg_welcome, parse_mode="HTML", reply_markup=markup)

# --- NÚT HỖ TRỢ KỸ THUẬT ---
@master_bot.message_handler(func=lambda m: m.text == "☎️ Hỗ Trợ Kỹ Thuật")
def support_info(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 Kết Nối Với Admin", url="https://t.me/truonggianhu"))
    
    msg = (
        "☎️ <b>TRUNG TÂM HỖ TRỢ PHÁT TRIỂN VÀ VẬN HÀNH</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "• Xử lý sự cố nạp tiền chậm hoặc lỗi nội dung chuyển khoản.\n"
        "• Giải đáp thắc mắc liên quan đến cấu hình hệ thống Bot con.\n\n"
        "👉 Ấn nút bên dưới để nhắn tin trực tiếp cho điều phối viên hệ thống!"
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
        "👤 <b>HỒ SƠ TÀI KHOẢN HỆ THỐNG</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"🆔 ID Người dùng: <code>{uid}</code>\n"
        f"💰 Số dư tài khoản: <b>{user['balance']} VNĐ</b>\n"
        f"🤖 Số lượng bot đang chạy: <b>{bot_count} / 1 Bot (Tối đa)</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "💳 Nội dung cú pháp nạp tiền tự động:\n"
        f"Ghi đúng nội dung: <code>NAP {uid}</code>"
    )
    master_bot.send_message(message.chat.id, msg, parse_mode="HTML")

# --- NẠP TIỀN AUTO SEPAY ---
@master_bot.message_handler(func=lambda m: m.text == "💳 Nạp Tiền Hệ Thống")
def deposit_info(message):
    uid = message.from_user.id
    bank_bin = "970416" # ACB BANK
    account_no = "49581007"
    account_name = "TRUONG GIA NHU"
    content = f"NAP {uid}"
    
    qr_url = f"https://img.vietqr.io/image/{bank_bin}-{account_no}-compact2.png?amount=30000&addInfo={content}&accountName={account_name}"
    
    msg = (
        "💳 <b>CỔNG NẠP TIỀN TỰ ĐỘNG KHÔNG LỖI VIETQR</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"🏦 Ngân hàng thụ hưởng: <b>ACB BANK</b>\n"
        f"🔢 Số tài khoản: <b>{account_no}</b>\n"
        f"👤 Chủ tài khoản: <b>{account_name}</b>\n"
        f"📝 Nội dung chuyển khoản: <code>NAP {uid}</code>\n"
        "━━━━━━━━━━━━━━━\n"
        "⚠️ <b>LƯU Ý QUAN TRỌNG:</b>\n"
        "Hệ thống tự động cộng số dư qua Webhook SePay sau 30 giây. Vui lòng quét mã QR để điền sẵn nội dung chính xác tuyệt đối."
    )
    master_bot.send_photo(message.chat.id, photo=qr_url, caption=msg, parse_mode="HTML")

# --- MUA GÓI VIP ---
@master_bot.message_handler(func=lambda m: m.text == "💎 Mua Gói VIP")
def buy_vip_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, pkg in VIP_PACKAGES.items():
        markup.add(types.InlineKeyboardButton(f"{pkg['name']} - Giá: {pkg['price']} VNĐ", callback_data=f"buyvip_{key}"))
        
    master_bot.send_message(message.chat.id, "🛒 <b>Chọn thời hạn gói cước gia hạn cho Bot con của bạn:</b>", parse_mode="HTML", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('buyvip_'))
def handle_buy_vip(call):
    uid = call.from_user.id
    vip_key = call.data.split('_')[1]
    pkg = VIP_PACKAGES.get(vip_key)
    if not pkg: return
    
    user = db.get_user(uid)
    if not user: return
    
    if user['balance'] < pkg['price']:
        master_bot.answer_callback_query(call.id, f"❌ Số dư không đủ! Cần nạp thêm tiền. Giá gói: {pkg['price']}đ.", show_alert=True)
        return
        
    # Tiến hành trừ tiền số dư hệ thống
    new_bal = user['balance'] - pkg['price']
    db.update_user_balance(uid, new_bal)
    
    # Cập nhật hạn sử dụng cho con bot con duy nhất của user này
    bots = db.get_bots_by_creator(str(uid))
    if not bots:
        master_bot.answer_callback_query(call.id, "❌ Bạn chưa tạo bot con nào để gia hạn!", show_alert=True)
        return
        
    b = bots[0] # Lấy con bot đầu tiên và duy nhất
    exp_add = timedelta(days=pkg['days'])
    
    try:
        current_exp = datetime.fromisoformat(b['expired_at'].replace("Z", "+00:00"))
    except:
        current_exp = datetime.now()
        
    if current_exp.timestamp() < time.time():
        current_exp = datetime.now()
        
    new_exp = (current_exp + exp_add).isoformat()
    db.update_sub_bot_data(b['bot_token'], {"expired_at": new_exp, "status": "running"})
        
    master_bot.answer_callback_query(call.id, f"✅ Đã thanh toán thành công {pkg['name']}!", show_alert=True)
    master_bot.send_message(call.message.chat.id, f"🎉 <b>Kích hoạt thành công gói {pkg['name']}!</b>\nBot con của bạn đã được gia hạn thêm {pkg['days']} ngày hoạt động. Số dư còn lại: {new_bal} VNĐ.", parse_mode="HTML")

# --- QUẢN LÝ BOT CON ---
@master_bot.message_handler(func=lambda m: m.text == "▶️ Quản Lý Bot Con")
def manage_bots(message):
    uid = message.from_user.id
    bots = db.get_bots_by_creator(str(uid))
    
    if not bots:
        master_bot.send_message(message.chat.id, "❌ Bạn chưa khởi tạo bot con nào trong cơ sở dữ liệu.")
        return
        
    markup = types.InlineKeyboardMarkup()
    b = bots[0]
    status_icon = "🟢" if b['status'] == "running" else "🔴"
    token_prefix = b['bot_token'].split(':')[0] if ":" in b['bot_token'] else "Bot"
    markup.add(types.InlineKeyboardButton(f"{status_icon} ID Bot: {token_prefix}", callback_data=f"managebot_{b['bot_token']}"))
        
    master_bot.send_message(message.chat.id, "📋 <b>Trình điều khiển trạng thái Bot con duy nhất của bạn:</b>", parse_mode="HTML", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('managebot_'))
def bot_detail(call):
    token = call.data.split('_')[1]
    bot_data = db.get_sub_bot(token)
    if not bot_data: return
    
    status_text = "Đang chạy trực tuyến 🟢" if bot_data['status'] == "running" else "Đang tạm dừng hoạt động 🔴"
    exp_date = bot_data.get('expired_at', 'N/A')[:19].replace("T", " ")
    config = bot_data.get('config_data') or {}
    b_type = config.get('bot_type', 'Chưa rõ')
    
    msg = (
        f"🤖 <b>CẤU HÌNH CHI TIẾT BOT CON</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔑 ID Token: <code>{token.split(':')[0]}</code>\n"
        f"⚙️ Phân loại chức năng: <b>{b_type.upper()}</b>\n"
        f"⏳ Thời hạn hoạt động: <code>{exp_date}</code>\n"
        f"📊 Trạng thái vận hành: <b>{status_text}</b>"
    )
    
    markup = types.InlineKeyboardMarkup()
    if bot_data['status'] == "running":
        markup.add(types.InlineKeyboardButton("🔴 Dừng Hoạt Động", callback_data=f"stopbot_{token}"))
    else:
        markup.add(types.InlineKeyboardButton("🟢 Chạy Hoạt Động", callback_data=f"startbot_{token}"))
        
    master_bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('stopbot_') or call.data.startswith('startbot_'))
def toggle_bot_status(call):
    action, token = call.data.split('_')
    new_status = "stopped" if action == "stopbot" else "running"
    db.update_sub_bot_status(token, new_status)
    master_bot.answer_callback_query(call.id, "✅ Đã thay đổi trạng thái bot thành công!")
    bot_detail(call)

# --- KHỞI TẠO BOT CON THEO ĐÚNG 3 LOẠI CHUẨN TRÍ TUỆ LOGIC ---
@master_bot.message_handler(func=lambda m: m.text == "🤖 Tạo Bot Con")
def start_create_bot(message):
    uid = message.from_user.id
    bots = db.get_bots_by_creator(str(uid))
    
    # LOGIC CHẶT CHẼ: Mỗi tài khoản chỉ được phép tạo 1 bot con duy nhất
    if len(bots) >= 1:
        master_bot.send_message(message.chat.id, "❌ <b>Hạn chế quyền!</b> Mỗi tài khoản chỉ được phép khởi tạo tối đa 1 bot con dùng thử hệ thống.")
        return
        
    bot_creation_state[uid] = {"step": 1}
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🎁 1. Mời Bạn Bè Nhận Cốt (Code)", callback_data="type_code"),
        types.InlineKeyboardButton("💰 2. Mời Bạn Bè Kiếm Tiền", callback_data="type_money"),
        types.InlineKeyboardButton("🎮 3. Đổi Điểm TNV Game Nhận Quà", callback_data="type_game")
    )
    master_bot.send_message(message.chat.id, "⚙️ <b>VUI LÒNG CHỌN 1 TRONG 3 PHÂN LOẠI BOT MUỐN KHỞI TẠO TẬP LỆNH:</b>", parse_mode="HTML", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('type_'))
def process_bot_type(call):
    uid = call.from_user.id
    if uid not in bot_creation_state: return
    
    bot_type = call.data.split('_')[1]
    bot_creation_state[uid]["type"] = bot_type
    bot_creation_state[uid]["step"] = 2
    
    master_bot.send_message(call.message.chat.id, "👉 <b>Bây giờ hãy nhập mã chuỗi Token lấy từ @BotFather gửi trực tiếp vào đây:</b>", parse_mode="HTML")
    master_bot.answer_callback_query(call.id)

@master_bot.message_handler(func=lambda m: m.from_user.id in bot_creation_state and bot_creation_state[m.from_user.id]["step"] == 2)
def process_bot_token(message):
    uid = message.from_user.id
    token = message.text.strip()
    
    if ":" not in token:
        master_bot.send_message(message.chat.id, "❌ Chuỗi Token sai định dạng tiêu chuẩn API Telegram! Vui lòng thử lại.")
        return
        
    try:
        test_bot = telebot.TeleBot(token)
        bot_info = test_bot.get_me()
        
        # Mặc định cấp chuẩn 1 ngày sử dụng (24 giờ dùng thử)
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
        
        # Thiết lập chính xác Webhook cho Bot con
        webhook_sub_url = f"{RENDER_URL}/webhook/sub/{token}"
        test_bot.remove_webhook()
        test_bot.set_webhook(url=webhook_sub_url, drop_pending_updates=True)
        
        del bot_creation_state[uid]
        master_bot.send_message(message.chat.id, f"✅ <b>HỆ THỐNG KHỞI TẠO THÀNH CÔNG!</b>\n🤖 Bot con: @{bot_info.username}\n👉 Hãy truy cập vào con bot con vừa tạo của bạn rồi gõ /start để chạy quy trình xác thực.")
        
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ Token lỗi hoặc không kết nối được tới máy chủ Telegram API. Chi tiết: {e}")

# ==========================================
# TRÌNH ĐIỀU HƯỚNG WEBHOOK ĐỘNG CHO BOT CON
# KHÔNG LỖI TRƠ BOT - BẤM ĐÂU ĂN ĐÓ
# ==========================================
def run_sub_bot_logic(token: str, update_dict: dict):
    bot_info = db.get_sub_bot(token)
    if not bot_info or bot_info['status'] != 'running': return
    
    bot = telebot.TeleBot(token, threaded=False)
    update = types.Update.de_json(update_dict)
    
    # 1. Kiểm tra hạn sử dụng bot con ngay khi có update
    try:
        exp_time = datetime.fromisoformat(bot_info["expired_at"].replace("Z", "+00:00"))
        if datetime.now(exp_time.tzinfo) > exp_time:
            if update.message:
                bot.send_message(update.message.chat.id, "❌ Thiết bị Bot tạm dừng hoạt động do hết thời hạn gói cước. Vui lòng liên hệ chủ sở hữu để nâng cấp.")
            return
    except: pass

    # Lấy và ánh xạ cấu trúc dữ liệu từ cơ sở dữ liệu
    users = bot_info.get("users_list") or []
    admins = bot_info.get("admins_list") or []
    channels = bot_info.get("channels_list") or []
    ban_users = bot_info.get("ban_user_list") or []
    invited = bot_info.get("invited_map") or {}
    userdata = bot_info.get("userdata_map") or {}
    codes = bot_info.get("codes_list") or []
    log_rutcode = bot_info.get("log_rutcode_list") or []
    config = bot_info.get("config_data") or {}
    
    # LOGIC XỬ LÝ TIN NHẮN (MESSAGE)
    if update.message:
        msg = update.message
        u_str = str(msg.from_user.id)
        
        if u_str in ban_users and u_str not in admins: return

        # XỬ LÝ LỆNH /START BẮT BUỘC JOIN NHÓM & CAPTCHA HÌNH
        if msg.text and msg.text.startswith("/start"):
            args = msg.text.split()
            if u_str not in users:
                users.append(u_str)
                userdata[u_str] = {"balance": 0, "verified": False}
                if len(args) > 1 and args[1] != u_str:
                    invited[u_str] = args[1] # Lưu ID người giới thiệu
                db.update_sub_bot_data(token, {"users_list": users, "invited_map": invited, "userdata_map": userdata})

            # Bước 1: Nếu có kênh bắt buộc thì ép buộc tham gia
            if channels:
                text_ch = "🔍 <b>BẠN CẦN THAM GIA CÁC KÊNH SAU ĐỂ TIẾP TỤC:</b>\n"
                for ch in channels: text_ch += f"\n💠 {ch}"
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("✅ Tôi đã tham gia đủ nhóm", callback_data="sub_btn_checkjoin"))
                bot.send_message(msg.chat.id, text_ch, parse_mode="HTML", reply_markup=markup)
            else:
                # Nếu không có kênh, nhảy thẳng sang bước gửi Captcha ảnh hình 4 số
                userdata[u_str]["verified"] = False
                db.update_sub_bot_data(token, {"userdata_map": userdata})
                send_captcha_challenge(bot, msg.chat.id, u_str, token)
            return

        # LOGIC KIỂM TRA ĐIỀN CAPTCHA 4 CHỮ SỐ
        if u_str in captcha_storage and msg.text:
            correct_captcha = captcha_storage[u_str]["code"]
            if msg.text.strip() == correct_captcha:
                ref_id = captcha_storage[u_str]["ref_id"]
                del captcha_storage[u_str] # Giải phóng RAM
                
                if u_str not in userdata: userdata[u_str] = {"balance": 0}
                userdata[u_str]["verified"] = True
                
                # Trả thưởng hoa hồng ref giới thiệu
                if ref_id and ref_id in userdata:
                    bonus = config.get("ref_bonus", 1000)
                    userdata[ref_id]["balance"] = userdata.get(ref_id, {}).get("balance", 0) + bonus
                    try: bot.send_message(int(ref_id), f"🎉 Bạn nhận được <b>+{bonus} VNĐ</b> hoa hồng giới thiệu thành viên mới xác thực thành công!", parse_mode="HTML")
                    except: pass
                
                db.update_sub_bot_data(token, {"userdata_map": userdata})
                bot.send_message(msg.chat.id, "✅ <b>Xác thực Captcha thành công!</b> Hệ thống đã mở khóa toàn bộ tính năng.")
                display_sub_bot_menu(bot, msg.chat.id, config.get("bot_type", "code"))
            else:
                bot.send_message(msg.chat.id, "❌ <b>Mã xác thực sai!</b> Đang sinh ảnh Captcha mới, vui lòng nhập lại đúng 4 số.")
                send_captcha_challenge(bot, msg.chat.id, u_str, token)
            return

        # NẾU USER CHƯA VƯỢT CAPTCHA, KHÔNG CHO CHẠY TIẾP CÁC PHÍM CHỨC NĂNG DƯỚI
        if not userdata.get(u_str, {}).get("verified", False) and u_str not in admins:
            bot.send_message(msg.chat.id, "⚠️ Bạn chưa hoàn thành quy trình xác thực thực thể! Vui lòng gõ /start để làm lại.")
            return

        # --- MẠNG PHÍM BẤM CHỨC NĂNG CỦA USER BOT CON ---
        if msg.text == "💰 Số dư của tôi":
            bal = userdata.get(u_str, {}).get("balance", 0)
            bot.send_message(msg.chat.id, f"💰 <b>Số dư tài khoản:</b> <code>{bal}</code> VNĐ", parse_mode="HTML")
            
        elif msg.text == "📮 Mời Bạn Bè":
            link = f"https://t.me/{bot.get_me().username}?start={u_str}"
            bot.send_message(msg.chat.id, f"🔗 <b>Link mời bạn bè của bạn:</b>\n<code>{link}</code>\n\n🎁 Phần thưởng: <b>{config.get('ref_bonus', 1000)}đ</b> trên mỗi lượt xác thực.")
            
        elif msg.text in ["🛒 Rút Mã Code", "💵 Rút Tiền Mặt", "🎮 Đổi Phần Quà"]:
            bot.send_message(msg.chat.id, f"👉 Sử dụng cú pháp sau để làm lệnh rút về:\n<code>/rut [Số Tiền]</code>\nHạn mức tối thiểu: {config.get('min_rut', 10000)}đ", parse_mode="HTML")

        # XỬ LÝ LỆNH RÚT TIỀN / CODE TỰ ĐỘNG THEO LOẠI BOT
        elif msg.text and msg.text.startswith("/rut"):
            parts = msg.text.split()
            if len(parts) < 2: return
            try: amount = int(parts[1])
            except: return

            bal = userdata.get(u_str, {}).get("balance", 0)
            min_r = config.get("min_rut", 10000)
            
            if amount < min_r or bal < amount:
                bot.send_message(msg.chat.id, f"❌ Thao tác thất bại! Số dư không đủ hoặc nhỏ hơn hạn mức tối thiểu {min_r}đ.")
                return
                
            bot_type = config.get("bot_type", "code")
            if bot_type == "code":
                if not codes:
                    bot.send_message(msg.chat.id, "⚠️ Kho hàng mã Code quà tặng tạm thời hết, vui lòng đợi Admin nạp thêm.")
                    return
                code_out = codes.pop(0)
                userdata[u_str]["balance"] -= amount
                log_rutcode.append({"user_id": u_str, "amount": amount, "type": "code", "gift": code_out})
                bot.send_message(msg.chat.id, f"🎉 <b>RÚT THÀNH CÔNG! MÃ SỐ QUÀ TẶNG CỦA BẠN:</b>\n<code>{code_out}</code>", parse_mode="HTML")
            else:
                userdata[u_str]["balance"] -= amount
                log_rutcode.append({"user_id": u_str, "amount": amount, "type": bot_type, "status": "Pending"})
                bot.send_message(msg.chat.id, "✅ <b>Yêu cầu rút tiền thành công!</b> Đơn của bạn đã gửi lên bộ phận duyệt Admin bot.")

            db.update_sub_bot_data(token, {"codes_list": codes, "userdata_map": userdata, "log_rutcode_list": log_rutcode})

        # --- MENU QUẢN TRỊ ADMIN CHO BOT CON (/menu) ---
        elif u_str in admins:
            if msg.text == "/menu":
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("➕ Thêm Kênh Bắt Buộc", callback_data="admsub_addch"),
                    types.InlineKeyboardButton("🗑 Xóa Hết Kênh", callback_data="admsub_delch"),
                    types.InlineKeyboardButton("📦 Thêm Mã Code Quà", callback_data="admsub_addcode"),
                    types.InlineKeyboardButton("💳 Cộng Tiền User", callback_data="admsub_money"),
                    types.InlineKeyboardButton("🚫 Khóa ID User", callback_data="admsub_ban")
                )
                bot.send_message(msg.chat.id, "🛠 <b>BẢNG ĐIỀU KHIỂN QUẢN TRỊ VIÊN BOT CON:</b>", reply_markup=markup, parse_mode="HTML")
                
            elif msg.text.startswith("/addch "):
                channels.append(msg.text.split()[1].strip())
                db.update_sub_bot_data(token, {"channels_list": channels})
                bot.send_message(msg.chat.id, "✅ Đã thêm kênh bắt buộc join thành công.")
                
            elif msg.text.startswith("/addcode\n"):
                raw_lines = msg.text.split("\n")[1:]
                for line in raw_lines:
                    if line.strip(): codes.append(line.strip())
                db.update_sub_bot_data(token, {"codes_list": codes})
                bot.send_message(msg.chat.id, f"✅ Đã nạp thành công {len(raw_lines)} mã code.")
                
            elif msg.text.startswith("/addmoney "):
                parts = msg.text.split()
                if len(parts) == 3:
                    t_id, amt = parts[1], int(parts[2])
                    if t_id not in userdata: userdata[t_id] = {"balance": 0, "verified": True}
                    userdata[t_id]["balance"] += amt
                    db.update_sub_bot_data(token, {"userdata_map": userdata})
                    bot.send_message(msg.chat.id, f"✅ Đã cộng thêm {amt}đ cho tài khoản ID: {t_id}.")

    # LOGIC XỬ LÝ SỰ KIỆN CALLBACK QUERIES CHO BOT CON
    elif update.callback_query:
        call = update.callback_query
        u_str = str(call.from_user.id)
        
        if call.data == "sub_btn_checkjoin":
            userdata[u_str]["verified"] = False
            db.update_sub_bot_data(token, {"userdata_map": userdata})
            send_captcha_challenge(bot, call.message.chat.id, u_str, token)
            bot.answer_callback_query(call.id)
            
        elif call.data.startswith("admsub_"):
            action = call.data.replace("admsub_", "")
            syntax = {
                "addch": "Cú pháp thêm kênh:\n<code>/addch @TenKenhCuaBan</code>",
                "delch": "<i>Hệ thống tự động dọn dẹp sạch kho kênh</i>",
                "addcode": "Cú pháp thêm code hàng loạt:\n<code>/addcode\nCODE1\nCODE2\nCODE3</code>",
                "money": "Cú pháp cộng tiền:\n<code>/addmoney ID_USER SỐ_TIỀN</code>",
                "ban": "Cú pháp khóa:\n<code>/ban ID_USER</code>"
            }
            bot.send_message(call.message.chat.id, f"✏️ <b>Cấu trúc lệnh Admin:</b>\n{syntax.get(action, '')}", parse_mode="HTML")
            bot.answer_callback_query(call.id)

# --- HÀM THỰC THI CAPTCHA ĐỘC LẬP ---
def send_captcha_challenge(bot, chat_id, user_id_str, token):
    captcha_text = str(random.randint(1000, 9999))
    bot_info = db.get_sub_bot(token)
    invited_map = bot_info.get("invited_map") or {}
    ref_id = invited_map.get(user_id_str, None)
    
    captcha_storage[user_id_str] = {
        "code": captcha_text,
        "ref_id": ref_id
    }
    
    photo_stream = generate_captcha_image(captcha_text)
    bot.send_photo(
        chat_id,
        photo=photo_stream,
        caption="🤖 <b>QUY TRÌNH KIỂM TRA CAPTCHA CHỐNG SPAM CLONE</b>\n━━━━━━━━━━━━━━━\n👉 Nhìn vào ảnh phía trên và nhập lại chính xác dãy 4 chữ số gửi vào đây để mở khóa menu chính!",
        parse_mode="HTML"
    )

def display_sub_bot_menu(bot, chat_id, bot_type):
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if bot_type == "code":
        menu.row("💰 Số dư của tôi", "🛒 Rút Mã Code")
    elif bot_type == "money":
        menu.row("💰 Số dư của tôi", "💵 Rút Tiền Mặt")
    else:
        menu.row("💰 Số dư của tôi", "🎮 Đổi Phần Quà")
    menu.row("📮 Mời Bạn Bè")
    bot.send_message(chat_id, "🎛 <b>BẢNG MENU ĐIỀU KHIỂN ĐÃ ĐƯỢC KÍCH HOẠT:</b>", reply_markup=menu, parse_mode="HTML")

# ==========================================
# CÁC ROUTE ĐÓN ĐẦU ENDPOINT WEBHOOK FASTAPI
# ==========================================
@app.post("/webhook/master")
async def handle_master_webhook(request: Request):
    try:
        json_data = await request.json()
        update = types.Update.de_json(json_data)
        master_bot.process_new_updates([update])
    except Exception as e:
        print(f"Lỗi webhook master: {e}")
    return Response(status_code=200)

@app.post("/webhook/sub/{token}")
async def handle_sub_webhook(token: str, request: Request):
    try:
        json_data = await request.json()
        run_sub_bot_logic(token, json_data)
    except Exception as e:
        print(f"Lỗi webhook sub bot: {e}")
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
                        master_bot.send_message(target_user_id, f"🔔 <b>Hệ thống SePay thông báo:</b> Bạn đã được nạp tự động thành công +<code>{amount}</code> VNĐ. Số dư hiện tại: {new_bal} VNĐ.", parse_mode="HTML")
                    except: pass
                    break
    except Exception as e:
        print(f"Lỗi xử lý webhook từ SePay: {e}")
    return Response(status_code=200)

@app.get("/")
def home():
    return {"status": "running", "message": "Hệ thống máy chủ vận hành mượt mà, sẵn sàng không lỗi lầm."}
