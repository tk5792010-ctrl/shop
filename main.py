import os
import time
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response
import telebot
from telebot import types
import database as db

# ==========================================
# CẤU HÌNH HỆ THỐNG
# ==========================================
RENDER_URL = "https://shop-ws1s.onrender.com"
MASTER_TOKEN = "8848756408:AAEAcpMvrbihm2n7LMN-nKC-UtKGd2Dgm4g"

app = FastAPI()
master_bot = telebot.TeleBot(MASTER_TOKEN, threaded=False)

# Cấu hình gói VIP
VIP_PACKAGES = {
    "vip0": {"name": "VIP 0 Test Trải Nghiệm 24H", "price": 0, "days": 1},
    "vip1": {"name": "VIP 1 (1 Tuần)", "price": 59000, "days": 7},
    "vip2": {"name": "VIP 2 (1 Tháng)", "price": 179000, "days": 30},
    "vip3": {"name": "VIP 3 (1 Năm)", "price": 1999000, "days": 365},
    "vip4": {"name": "VIP 4 (Vĩnh Viễn)", "price": 9999000, "days": 36500} # 100 năm
}

# ==========================================
# KHỞI ĐỘNG SERVER & WEBHOOK MASTER
# ==========================================
@app.on_event("startup")
async def on_startup():
    try:
        master_bot.delete_webhook()
        webhook_master_url = f"{RENDER_URL}/webhook/master"
        master_bot.set_webhook(url=webhook_master_url, drop_pending_updates=True)
        print(f"✅ Webhook Master đã set: {webhook_master_url}")
    except Exception as e:
        print(f"❌ Lỗi set webhook: {e}")

# ==========================================
# LOGIC MASTER BOT (Quản lý, Nạp Tiền, Tạo Bot)
# ==========================================

# --- GIAO DIỆN CHÍNH ---
@master_bot.message_handler(commands=['start'])
def master_start(message):
    uid = message.from_user.id
    db.create_or_update_user(user_id=uid, username=message.from_user.username)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🤖 Tạo Bot"),
        types.KeyboardButton("▶️ Quản Lý Bot")
    )
    markup.add(
        types.KeyboardButton("💥 Dịch Vụ MXH 💥"),
        types.KeyboardButton("💎 Mua Gói VIP")
    )
    markup.add(
        types.KeyboardButton("💳 Nạp Tiền"),
        types.KeyboardButton("👤 Tài khoản")
    )
    markup.add(types.KeyboardButton("📚 Hướng dẫn sử dụng 🔗"))
    
    msg_welcome = (
        "👋 <b>Xin chào, Chào mừng bạn đến với hệ thống tạo bot tự động!</b>\n\n"
        "💡 <b>Hướng Dẫn Sử Dụng:</b>\n"
        "1️⃣ Chọn <b>Tạo Bot</b> để tạo bot mới. Điền Tên Bot, Admin ID và Token Bot lấy từ @BotFather.\n"
        "2️⃣ Chọn <b>Quản Lý Bot</b> để Bật/Tắt bot của bạn.\n"
        "3️⃣ Xem Video Hướng Dẫn Setup Bot Bên Trên Để Đưa Bot Vào Hoạt Động Nha.\n\n"
        "<i>‼️ Lưu Ý : Nên Mua Gói Vip Để Bot Được Duy Trì Lâu Dài Vận Hành Mượt Mà Hơn Nhé👍</i>"
    )
    master_bot.send_message(message.chat.id, msg_welcome, parse_mode="HTML", reply_markup=markup)

# --- THÔNG TIN TÀI KHOẢN ---
@master_bot.message_handler(func=lambda m: m.text == "👤 Tài khoản")
def acc_info(message):
    uid = message.from_user.id
    user = db.get_user(uid)
    if not user:
        return
        
    bots = db.get_bots_by_creator(str(uid))
    bot_count = len(bots)
    
    msg = (
        "👤 <b>THÔNG TIN TÀI KHOẢN</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"💰 Số dư: <b>{user['balance']} VNĐ</b>\n"
        f"👑 Cấp độ: Thường\n"
        f"⏳ Hạn VIP: N/A\n"
        f"🤖 Bot đã tạo: {bot_count}\n"
        f"🆓 Bot Free: Đã dùng\n"
        "━━━━━━━━━━━━━━━\n"
        f"💳 Để nạp tiền tự động, chuyển khoản với nội dung:\n"
        f"<code>NAP {uid}</code>"
    )
    master_bot.send_message(message.chat.id, msg, parse_mode="HTML")

# --- NẠP TIỀN QUÉT MÃ QR (AUTO SEPAY) ---
@master_bot.message_handler(func=lambda m: m.text == "💳 Nạp Tiền")
def deposit_info(message):
    uid = message.from_user.id
    # URL tạo QR Code động của VietQR (Thay số tài khoản ACB của mày vào đây)
    bank_bin = "970416" # Mã BIN ACB
    account_no = "49581007" # Thay bằng STK của mày
    account_name = "TRUONG GIA NHU" # Thay bằng Tên của mày
    amount = 50000 # Mặc định hiển thị 50k
    content = f"NAP {uid}"
    
    qr_url = f"https://img.vietqr.io/image/{bank_bin}-{account_no}-compact2.png?amount={amount}&addInfo={content}&accountName={account_name}"
    
    msg = (
        "💳 <b>NẠP TIỀN TỰ ĐỘNG 24/7</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "🏦 Ngân hàng: <b>ACB</b>\n"
        f"🔢 Số tài khoản: <b>{account_no}</b>\n"
        f"👤 Chủ TK: <b>{account_name}</b>\n"
        f"📝 Nội dung: <code>NAP {uid}</code>\n"
        "━━━━━━━━━━━━━━━\n"
        "⚠️ <b>LƯU Ý:</b>\n"
        "1. Quét mã QR dưới đây để điền sẵn nội dung.\n"
        "2. Chuyển đúng nội dung để hệ thống cộng tiền tự động.\n"
        "3. Sau 1-2 phút tiền sẽ tự động vào tài khoản.\n"
        "4. ⚠️ Min nạp là 10k. Nạp dưới 10k sẽ bị trừ chiết khấu."
    )
    master_bot.send_photo(message.chat.id, photo=qr_url, caption=msg, parse_mode="HTML")

# --- MUA GÓI VIP ---
@master_bot.message_handler(func=lambda m: m.text == "💎 Mua Gói VIP")
def buy_vip_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, pkg in VIP_PACKAGES.items():
        markup.add(types.InlineKeyboardButton(f"{pkg['name']}", callback_data=f"buyvip_{key}"))
        
    master_bot.send_message(message.chat.id, "🛒 <b>Chọn gói VIP bạn muốn mua:</b>", parse_mode="HTML", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('buyvip_'))
def handle_buy_vip(call):
    uid = call.from_user.id
    vip_key = call.data.split('_')[1]
    pkg = VIP_PACKAGES.get(vip_key)
    
    if not pkg: return
    
    user = db.get_user(uid)
    if not user: return
    
    if user['balance'] < pkg['price']:
        master_bot.answer_callback_query(call.id, f"❌ Bạn không đủ tiền! Cần {pkg['price']} VNĐ.", show_alert=True)
        return
        
    # Trừ tiền
    new_bal = user['balance'] - pkg['price']
    db.update_user_balance(uid, new_bal)
    
    # Cộng ngày vào toàn bộ bot của user này
    bots = db.get_bots_by_creator(str(uid))
    exp_add = timedelta(days=pkg['days'])
    
    for b in bots:
        current_exp = datetime.fromisoformat(b['expired_at'].replace("Z", "+00:00")) if b.get('expired_at') else datetime.now()
        if current_exp < datetime.now():
            current_exp = datetime.now()
            
        new_exp = (current_exp + exp_add).isoformat()
        db.update_sub_bot_data(b['bot_token'], {"expired_at": new_exp, "status": "running"})
        
    master_bot.answer_callback_query(call.id, f"✅ Mua thành công {pkg['name']}!", show_alert=True)
    master_bot.send_message(call.message.chat.id, f"🎉 <b>Đã kích hoạt {pkg['name']} thành công!</b>\nTất cả bot của bạn đã được gia hạn thêm {pkg['days']} ngày. Số dư còn: {new_bal} VNĐ.", parse_mode="HTML")

# --- QUẢN LÝ BOT ---
@master_bot.message_handler(func=lambda m: m.text == "▶️ Quản Lý Bot")
def manage_bots(message):
    uid = message.from_user.id
    bots = db.get_bots_by_creator(str(uid))
    
    if not bots:
        master_bot.send_message(message.chat.id, "❌ Bạn chưa có bot nào. Hãy nhấn 'Tạo Bot' để bắt đầu.")
        return
        
    markup = types.InlineKeyboardMarkup()
    for b in bots:
        try:
            bot_info = telebot.TeleBot(b['bot_token']).get_me()
            name = bot_info.username
        except:
            name = "UnknownBot"
            
        status_icon = "🟢" if b['status'] == "running" else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status_icon} @{name}", callback_data=f"managebot_{b['bot_token']}"))
        
    master_bot.send_message(message.chat.id, "📋 <b>Danh sách bot của bạn:</b>\n<i>Chọn bot để cài đặt/chạy/dừng</i>", parse_mode="HTML", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('managebot_'))
def bot_detail(call):
    token = call.data.split('_')[1]
    bot_data = db.get_sub_bot(token)
    if not bot_data: return
    
    try:
        bot_info = telebot.TeleBot(token).get_me()
        bot_username = bot_info.username
        bot_name = bot_info.first_name
    except:
        bot_username = "Unknown"
        bot_name = "Unknown"
        
    status_text = "Đang chạy 🟢" if bot_data['status'] == "running" else "Đã dừng 🔴"
    exp_date = bot_data.get('expired_at', 'N/A')[:19].replace("T", " ") if bot_data.get('expired_at') else 'N/A'
    
    msg = (
        f"🤖 <b>Bot:</b> {bot_name}\n"
        f"👤 <b>Username:</b> @{bot_username}\n"
        f"⏳ <b>Hạn dùng:</b> {exp_date}\n"
        f"📊 <b>Trạng thái:</b> {status_text}"
    )
    
    markup = types.InlineKeyboardMarkup()
    if bot_data['status'] == "running":
        markup.add(types.InlineKeyboardButton("🔴 Dừng Bot", callback_data=f"stopbot_{token}"))
    else:
        markup.add(types.InlineKeyboardButton("🟢 Chạy Bot", callback_data=f"startbot_{token}"))
        
    markup.add(types.InlineKeyboardButton("⬅️ Quay lại", callback_data="manage_back"))
    
    master_bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data == "manage_back")
def manage_back(call):
    manage_bots(call.message)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('stopbot_') or call.data.startswith('startbot_'))
def toggle_bot_status(call):
    action, token = call.data.split('_')
    new_status = "stopped" if action == "stopbot" else "running"
    db.update_sub_bot_status(token, new_status)
    
    master_bot.answer_callback_query(call.id, "✅ Cập nhật trạng thái thành công!")
    bot_detail(call)

# --- TẠO BOT MỚI ---
bot_creation_state = {}

@master_bot.message_handler(func=lambda m: m.text == "🤖 Tạo Bot")
def start_create_bot(message):
    uid = message.from_user.id
    bot_creation_state[uid] = {"step": 1}
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🎁 Bot Mời bạn Bè Nhận Code", callback_data="type_code"),
        types.InlineKeyboardButton("💰 Bot Mời bạn Bè Kiếm Tiền", callback_data="type_money")
    )
    markup.add(types.InlineKeyboardButton("🎮 Bot Đổi Điểm TNV Game", callback_data="type_game"))
    
    master_bot.send_message(message.chat.id, "🛠 <b>BẢNG QUẢN TRỊ BOT</b>\n✅ Chọn một chức năng bên dưới để Bắt Đầu SETUP BOT HOÀN CHỈNH 👇", parse_mode="HTML", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('type_'))
def process_bot_type(call):
    uid = call.from_user.id
    if uid not in bot_creation_state: return
    
    bot_type = call.data.split('_')[1]
    bot_creation_state[uid]["type"] = bot_type
    bot_creation_state[uid]["step"] = 2
    
    master_bot.send_message(call.message.chat.id, "✅ Đã chọn chức năng.\n👉 <b>Nhập Token cho con bot mới này:</b>", parse_mode="HTML")
    master_bot.answer_callback_query(call.id)

@master_bot.message_handler(func=lambda m: m.from_user.id in bot_creation_state and bot_creation_state[m.from_user.id]["step"] == 2)
def process_bot_token(message):
    uid = message.from_user.id
    token = message.text.strip()
    
    try:
        # Test token
        test_bot = telebot.TeleBot(token)
        bot_info = test_bot.get_me()
        
        # Lưu DB
        exp_date = (datetime.now() + timedelta(days=1)).isoformat() # Free 1 ngày
        bot_data = {
            "bot_token": token,
            "creator_id": str(uid),
            "admin_id": str(uid),
            "status": "running",
            "expired_at": exp_date,
            "config_data": {"bot_type": bot_creation_state[uid]["type"], "ref_bonus": 1000, "min_rut": 10000}
        }
        db.save_sub_bot(bot_data)
        
        # Set Webhook cho bot con
        webhook_sub_url = f"{RENDER_URL}/webhook/sub/{token}"
        test_bot.remove_webhook()
        test_bot.set_webhook(url=webhook_sub_url, drop_pending_updates=True)
        
        del bot_creation_state[uid]
        master_bot.send_message(message.chat.id, f"✅ <b>TẠO BOT THÀNH CÔNG!</b>\n🤖 Bot: @{bot_info.username}\n👉 Hãy vào bot của bạn và gõ /start", parse_mode="HTML")
        
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ Token không hợp lệ: {e}")

# ==========================================
# LOGIC SUB BOT (Xử lý sự kiện cho Bot Con)
# ==========================================
def process_sub_bot_event(token: str, update_dict: dict):
    bot_info = db.get_sub_bot(token)
    if not bot_info or bot_info['status'] != 'running':
        return
        
    bot = telebot.TeleBot(token, threaded=False)
    update = types.Update.de_json(update_dict)
    
    if not update.message and not update.callback_query:
        return
        
    # Kéo dữ liệu
    users = bot_info.get("users_list") or []
    admins = bot_info.get("admins_list") or []
    channels = bot_info.get("channels_list") or []
    codes = bot_info.get("codes_list") or []
    ban_users = bot_info.get("ban_user_list") or []
    invited = bot_info.get("invited_map") or {}
    userdata = bot_info.get("userdata_map") or {}
    log_rutcode = bot_info.get("log_rutcode_list") or []
    config = bot_info.get("config_data") or {}
    
    creator_id = bot_info.get("creator_id")
    if creator_id and str(creator_id) not in admins:
        admins.append(str(creator_id))

    # --- Xử lý tin nhắn ---
    if update.message:
        msg = update.message
        u_str = str(msg.from_user.id)
        
        # Kiểm tra hạn
        try:
            exp_time = datetime.fromisoformat(bot_info["expired_at"].replace("Z", "+00:00"))
            if datetime.now(exp_time.tzinfo) > exp_time:
                bot.send_message(msg.chat.id, "❌ Bot đã hết hạn. Hãy liên hệ Admin để gia hạn!")
                return
        except: pass

        if u_str in ban_users and u_str not in admins:
            bot.send_message(msg.chat.id, "⛔ Bạn đã bị cấm.")
            return

        # /start
        if msg.text and msg.text.startswith("/start"):
            args = msg.text.split()
            if u_str not in users:
                users.append(u_str)
                userdata[u_str] = {"balance": 0}
                if len(args) > 1 and args[1] != u_str:
                    invited[u_str] = args[1]

            if not channels:
                bot.send_message(msg.chat.id, "Chào mừng bạn!")
                menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
                menu.row("💰 Số dư của tôi", "🛒 Rút code")
                menu.row("📮MỜI BẠN BÈ", "📊 Thống kê bot")
                bot.send_message(msg.chat.id, "Chọn menu bên dưới:", reply_markup=menu)
            else:
                text = "🔍 Vui lòng tham gia các nhóm sau:\n"
                for ch in channels: text += f"\n💠 {ch}"
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("✅ Tôi đã tham gia", callback_data="check_join"))
                bot.send_message(msg.chat.id, text, reply_markup=markup)
            
            db.update_sub_bot_data(token, {"users_list": users, "invited_map": invited, "userdata_map": userdata})
            return

        # Phím chức năng
        if msg.text == "💰 Số dư của tôi":
            bal = userdata.get(u_str, {}).get("balance", 0)
            bot.send_message(msg.chat.id, f"💰 <b>Số dư:</b> {bal} VND", parse_mode="HTML")
            return
            
        elif msg.text == "🛒 Rút code":
            bot.send_message(msg.chat.id, "➡️ Cú pháp: <code>/rutcode [Tên NV] [Số Tiền]</code>", parse_mode="HTML")
            return
            
        elif msg.text == "📊 Thống kê bot":
            bot.send_message(msg.chat.id, f"📈 Tổng User: {len(users)}\n🔁 Số lượt rút: {len(log_rutcode)}")
            return
            
        elif msg.text == "📮MỜI BẠN BÈ":
            link = f"https://t.me/{bot.get_me().username}?start={u_str}"
            bot.send_message(msg.chat.id, f"🔗 Link mời: {link}\n🎁 Thưởng: {config.get('ref_bonus', 1000)}đ/người")
            return

        # Rút code
        if msg.text and msg.text.startswith("/rutcode"):
            args = msg.text.split()
            if len(args) < 3: return
            try: amount = int(args[2])
            except: return

            bal = userdata.get(u_str, {}).get("balance", 0)
            min_r = config.get("min_rut", 10000)
            
            if amount < min_r or bal < amount:
                bot.send_message(msg.chat.id, "❌ Không đủ điều kiện rút.")
                return
            if not codes:
                bot.send_message(msg.chat.id, "⚠️ Hết code.")
                return
                
            code_out = codes.pop(0)
            userdata[u_str]["balance"] -= amount
            log_rutcode.append({"user_id": u_str, "amount": amount})
            
            bot.send_message(msg.chat.id, f"✅ Rút thành công!\n🎁 CODE: <code>{code_out}</code>", parse_mode="HTML")
            db.update_sub_bot_data(token, {"codes_list": codes, "userdata_map": userdata, "log_rutcode_list": log_rutcode})
            return

        # MENU ADMIN BOT CON (Full tính năng)
        if u_str in admins:
            if msg.text == "/menu":
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("➕ Thêm Kênh", callback_data="adm_themkenh"),
                    types.InlineKeyboardButton("➖ Xóa Kênh", callback_data="adm_xoakenh"),
                    types.InlineKeyboardButton("➕ Thêm Code", callback_data="adm_themcode"),
                    types.InlineKeyboardButton("🗑 Xóa Code", callback_data="adm_xoacode"),
                    types.InlineKeyboardButton("💰 Nạp/Trừ Tiền", callback_data="adm_money"),
                    types.InlineKeyboardButton("🚫 Ban/Unban", callback_data="adm_ban")
                )
                bot.send_message(msg.chat.id, "🛠 <b>MENU ADMIN:</b>", reply_markup=markup, parse_mode="HTML")
                return
                
            elif msg.text.startswith("/themkenh "):
                channels.append(msg.text.split()[1])
                db.update_sub_bot_data(token, {"channels_list": channels})
                bot.send_message(msg.chat.id, "✅ Đã thêm kênh.")
                return
                
            elif msg.text.startswith("/themcode\n"):
                new_codes = msg.text.split("\n")[1:]
                codes.extend([c.strip() for c in new_codes if c.strip()])
                db.update_sub_bot_data(token, {"codes_list": codes})
                bot.send_message(msg.chat.id, f"✅ Đã thêm {len(new_codes)} code.")
                return
                
            elif msg.text.startswith("/naptien "):
                parts = msg.text.split()
                if len(parts) == 3:
                    t_id, amt = parts[1], int(parts[2])
                    if t_id not in userdata: userdata[t_id] = {"balance": 0}
                    userdata[t_id]["balance"] += amt
                    db.update_sub_bot_data(token, {"userdata_map": userdata})
                    bot.send_message(msg.chat.id, f"✅ Đã nạp {amt}đ cho {t_id}")
                return

    # --- Xử lý Callback Bot Con ---
    elif update.callback_query:
        call = update.callback_query
        u_str = str(call.from_user.id)
        
        if call.data == "check_join":
            # Logic check join (Giả lập pass cho nhanh)
            if u_str in invited:
                ref_id = invited.pop(u_str)
                bonus = config.get("ref_bonus", 1000)
                if ref_id not in userdata: userdata[ref_id] = {"balance": 0}
                userdata[ref_id]["balance"] += bonus
                try: bot.send_message(int(ref_id), f"🎁 Nhận {bonus}đ từ REF!")
                except: pass
                db.update_sub_bot_data(token, {"invited_map": invited, "userdata_map": userdata})

            menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
            menu.row("💰 Số dư của tôi", "🛒 Rút code")
            menu.row("📮MỜI BẠN BÈ", "📊 Thống kê bot")
            bot.send_message(call.message.chat.id, "🎉 Đã xác nhận tham gia!", reply_markup=menu)
            
        elif call.data.startswith("adm_"):
            cmd = call.data.replace("adm_", "")
            hints = {
                "themkenh": "/themkenh @username", "xoakenh": "/xoakenh @username",
                "themcode": "/themcode\nCode1\nCode2", "xoacode": "/xoacodeall",
                "money": "/naptien ID 10000\n/trutien ID 10000", "ban": "/ban ID\n/unban ID"
            }
            if cmd in hints:
                bot.send_message(call.message.chat.id, f"✏️ Cú pháp:\n<code>{hints[cmd]}</code>", parse_mode="HTML")
        bot.answer_callback_query(call.id)

# ==========================================
# ENDPOINT FASTAPI DÀNH CHO WEBHOOK TỪ TELEGRAM & SEPAY
# ==========================================
@app.post("/webhook/master")
async def handle_master_webhook(request: Request):
    try:
        json_data = await request.json()
        update = types.Update.de_json(json_data)
        master_bot.process_new_updates([update])
    except Exception as e: print(f"Lỗi webhook master: {e}")
    return Response(status_code=200)

@app.post("/webhook/sub/{token}")
async def handle_sub_webhook(token: str, request: Request):
    try:
        json_data = await request.json()
        process_sub_bot_event(token, json_data)
    except Exception as e: print(f"Lỗi webhook sub: {e}")
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
                    try: master_bot.send_message(target_user_id, f"✅ Nạp thành công {amount}đ. Số dư mới: {new_bal}đ")
                    except: pass
                    break
    except Exception as e: print(f"Lỗi Sepay: {e}")
    return Response(status_code=200)

@app.get("/")
def home():
    return {"status": "✅ Server đang chạy ổn định"}
