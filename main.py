import os
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response
import telebot
from telebot import types
from supabase import create_client, Client

# ==========================================
# CẤU HÌNH HỆ THỐNG CỦA MÀY (ĐÃ GẮN CỨNG)
# ==========================================
RENDER_URL = "https://shop-ws1s.onrender.com"
MASTER_TOKEN = "8848756408:AAEAcpMvrbihm2n7LMN-nKC-UtKGd2Dgm4g"
SUPABASE_URL = "https://dmnxbtayyadssvicdxtm.supabase.co"
SUPABASE_KEY = "sb_publishable_u9nAB8p-53_fxBzpP6lGDg_XInTwvfp"

# Khởi tạo kết nối Supabase và FastAPI
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

# Khởi tạo Bot Cha
master_bot = telebot.TeleBot(MASTER_TOKEN, threaded=False)

# ==========================================
# SỰ KIỆN KHỞI ĐỘNG SERVER (TỰ ĐỘNG SET WEBHOOK BOT CHA)
# ==========================================
@app.on_event("startup")
async def on_startup():
    try:
        master_bot.remove_webhook()
        webhook_master_url = f"{RENDER_URL}/webhook/master"
        master_bot.set_webhook(url=webhook_master_url)
        print(f"[SERVER START] Đã set thành công Webhook Bot Cha: {webhook_master_url}")
    except Exception as e:
        print(f"[LỖI STARTUP] Không thể set webhook bot cha: {e}")

# ==========================================
# CÁC HÀM XỬ LÝ DỮ LIỆU TỪ SUPABASE
# ==========================================
def get_bot_data(token: str):
    try:
        res = supabase.table("sub_bots").select("*").eq("bot_token", token).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        
        # Sửa lỗi PGRST116: Nếu bot chưa có trong DB, tự tạo bản ghi mới
        print(f"[HỆ THỐNG] Không tìm thấy dữ liệu bot con. Tự khởi tạo mặc định...")
        exp_date = (datetime.now() + timedelta(days=2)).isoformat()
        new_bot = {
            "bot_token": token,
            "status": "running",
            "expired_at": exp_date,
            "users_list": [],
            "admins_list": [],
            "channels_list": [],
            "codes_list": [],
            "ban_user_list": [],
            "invited_map": {},
            "userdata_map": {},
            "log_rutcode_list": [],
            "config_data": {"ref_bonus": 1000, "min_rut": 10000, "invite_image": "", "game_link": ""}
        }
        supabase.table("sub_bots").insert(new_bot).execute()
        return new_bot
    except Exception as e:
        print(f"[LỖI SUPABASE] Lấy dữ liệu bot thất bại: {e}")
        return None

def save_bot_data(token: str, updates: dict):
    try:
        supabase.table("sub_bots").update(updates).eq("bot_token", token).execute()
    except Exception as e:
        print(f"[LỖI SUPABASE] Lưu dữ liệu thất bại: {e}")

def check_expired(bot_info: dict) -> bool:
    if not bot_info or not bot_info.get("expired_at"):
        return True
    try:
        exp_time = datetime.fromisoformat(bot_info["expired_at"].replace("Z", "+00:00"))
        return datetime.now(exp_time.tzinfo) > exp_time
    except Exception as e:
        print(f"[LỖI HẠN SỬ DỤNG] {e}")
        return False

# ==========================================
# LOGIC XỬ LÝ SỰ KIỆN CHO BOT CON (SUB-BOT)
# ==========================================
def process_sub_bot_event(token: str, update_dict: dict):
    bot_info = get_bot_data(token)
    if not bot_info:
        return
        
    bot = telebot.TeleBot(token, threaded=False)
    
    # Đọc dữ liệu an toàn, chặn lỗi rỗng
    users = bot_info.get("users_list") or []
    admins = bot_info.get("admins_list") or []
    channels = bot_info.get("channels_list") or []
    codes = bot_info.get("codes_list") or []
    ban_users = bot_info.get("ban_user_list") or []
    invited = bot_info.get("invited_map") or {}
    userdata = bot_info.get("userdata_map") or {}
    log_rutcode = bot_info.get("log_rutcode_list") or []
    config = bot_info.get("config_data") or {"ref_bonus": 1000, "min_rut": 10000, "invite_image": "", "game_link": ""}
    
    creator_id = bot_info.get("creator_id")
    if creator_id and str(creator_id) not in admins:
        admins.append(str(creator_id))

    update = types.Update.de_json(update_dict)
    
    if update.message:
        msg = update.message
        user_id = msg.from_user.id
        u_str = str(user_id)
        
        print(f"[BOT CON] Tin nhắn từ {user_id}: {msg.text}")

        if check_expired(bot_info):
            bot.send_message(msg.chat.id, "❌ Bot này đã hết hạn dùng thử. Liên hệ Bot Cha để gia hạn!")
            return

        if u_str in ban_users and u_str not in admins:
            bot.send_message(msg.chat.id, "⛔ Bạn đã bị cấm sử dụng bot này.")
            return

        # ---- XỬ LÝ LỆNH /START ----
        if msg.text and msg.text.startswith("/start"):
            args = msg.text.split()
            if u_str not in users:
                users.append(u_str)
                userdata[u_str] = {"balance": 0}
                if len(args) > 1:
                    ref = args[1]
                    if ref != u_str:
                        invited[u_str] = ref

            if not channels:
                bot.send_message(msg.chat.id, "Hiện tại hệ thống chưa thiết lập kênh bắt buộc tham gia.")
                menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
                menu.row("💰 Số dư của tôi", "🛒 Rút code")
                menu.row("📮MỜI BẠN BÈ", "📄 Link Game")
                menu.row("📊 Thống kê bot")
                bot.send_message(msg.chat.id, "🎉 Chào mừng bạn đến với hệ thống!", reply_markup=menu)
            else:
                text = "🔍 Vui lòng tham gia vào tất cả các nhóm sau để bắt đầu sử dụng:\n"
                for ch in channels:
                    text += f"\n💠 {ch}"
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("✅ Tôi đã tham gia", callback_data="check_join"))
                bot.send_message(msg.chat.id, text, reply_markup=markup)
            
            save_bot_data(token, {"users_list": users, "invited_map": invited, "userdata_map": userdata})
            return

        # ---- XỬ LÝ PHÍM CHỨC NĂNG CHUNG ----
        if msg.text == "💰 Số dư của tôi":
            bal = userdata.get(u_str, {}).get("balance", 0)
            ref_b = config.get("ref_bonus", 1000)
            bot.send_message(msg.chat.id, f"💰 <b>Số dư của bạn</b>\n─────\n✨ Hiện tại: <b>{bal} VND</b>\n👉 Mời bạn bè nhận thêm: <b>{ref_b} VND/người</b>", parse_mode="HTML")
            return

        elif msg.text == "🛒 Rút code":
            bot.send_message(msg.chat.id, "<b>Hướng Dẫn Rút Code:</b>\n─────\n➡️ <code>/rutcode [Tên Nhân Vật] [Số Tiền]</code>\nVD: <code>/rutcode xuanson 10000</code>", parse_mode="HTML")
            return

        elif msg.text == "📄 Link Game":
            link = config.get("game_link", "")
            if link:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🎮 CHƠI NGAY", url=link))
                bot.send_message(msg.chat.id, f"🎮 <b>Link Game Chính Thức:</b>\n{link}", parse_mode='HTML', reply_markup=markup)
            else:
                bot.send_message(msg.chat.id, "Hiện chưa có link game nào được cập nhật.")
            return

        elif msg.text == "📊 Thống kê bot":
            total_users = len(users)
            total_rut = len(log_rutcode)
            total_amount = sum(l.get("amount", 0) for l in log_rutcode)
            text = f"📈 <b>Thống kê bot</b>\n─────\n👥 Tổng số user: <b>{total_users}</b>\n🔁 Tổng số lượt rút: <b>{total_rut}</b>\n💸 Tổng tiền đã rút: <b>{total_amount} VND</b>"
            bot.send_message(msg.chat.id, text, parse_mode="HTML")
            return

        elif msg.text == "📮MỜI BẠN BÈ":
            invite_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
            caption = f"<b>🔍 LINK GIỚI THIỆU CỦA BẠN:</b> <code>{invite_link}</code>\n\n<b>🔻 MỜI 1 BẠN = {config.get('ref_bonus', 1000)} VNĐ</b>\n<b>🤝 TỐI THIỂU RÚT: {config.get('min_rut', 10000)} VNĐ</b>"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📤 Chia sẻ", url=f"https://t.me/share/url?url={invite_link}"))
            
            img = config.get("invite_image", "")
            if img:
                bot.send_photo(msg.chat.id, photo=img, caption=caption, parse_mode="HTML", reply_markup=markup)
            else:
                bot.send_message(msg.chat.id, caption, parse_mode="HTML", reply_markup=markup)
            return

        # ---- XỬ LÝ LỆNH /RUTCODE ----
        if msg.text and msg.text.startswith("/rutcode"):
            args = msg.text.split()
            if len(args) < 3:
                bot.send_message(msg.chat.id, "⚠️ Dùng đúng mẫu: <code>/rutcode &lt;tên_nhân_vật&gt; &lt;số_tiền&gt;</code>", parse_mode="HTML")
                return
            
            note = args[1]
            try: amount = int(args[2])
            except: 
                bot.send_message(msg.chat.id, "⚠️ Số tiền phải là một con số hợp lệ.")
                return

            bal = userdata.get(u_str, {}).get("balance", 0)
            min_r = config.get("min_rut", 10000)
            
            if amount < min_r:
                bot.send_message(msg.chat.id, f"⚠️ Số tiền rút tối thiểu là {min_r}đ.")
                return
            if bal < amount:
                bot.send_message(msg.chat.id, "⚠️ Bạn không đủ số dư để thực hiện giao dịch này.")
                return
            if not codes:
                bot.send_message(msg.chat.id, "⚠️ Kho hàng hiện đang hết code, vui lòng quay lại sau.")
                return
                
            code_out = codes.pop(0)
            userdata[u_str]["balance"] -= amount
            log_rutcode.append({"user_id": u_str, "amount": amount})
            
            bot.send_message(msg.chat.id, f"✅ <b>RÚT THÀNH CÔNG</b>\n\nNhân vật: {note}\n💵 Số tiền: {amount} VND\n🎁 CODE CỦA BẠN: <code>{code_out}</code>", parse_mode="HTML")
            
            for adm in admins:
                try: bot.send_message(int(adm), f"🔔 Yêu cầu rút từ @{msg.from_user.username} (ID: {u_str})\n- Nhân vật: {note}\n- Tiền: {amount} VND\n- Code xuất: {code_out}")
                except: pass
                
            save_bot_data(token, {"codes_list": codes, "userdata_map": userdata, "log_rutcode_list": log_rutcode})
            return

        # ---- MENU QUẢN TRỊ ADMIN BOT CON ----
        if u_str in admins:
            if msg.text.startswith("/menu"):
                help_text = (
                    "🛠 <b>MENU QUẢN TRỊ ADMIN:</b>\n\n"
                    "<code>/themkenh @username</code> - Thêm kênh bắt buộc\n"
                    "<code>/xoakenh @username</code> - Xóa kênh bắt buộc\n"
                    "<code>/themcode</code> - Nhập danh sách code (xuống dòng)\n"
                    "<code>/xoacodeall</code> - Xóa trắng kho code\n"
                    "<code>/naptien [ID] [Số tiền]</code> - Nạp tiền cho User\n"
                    "<code>/trutien [ID] [Số tiền]</code> - Trừ tiền User\n"
                    "<code>/thuongmoiban [Số tiền]</code> - Set thưởng REF\n"
                    "<code>/minrut [Số tiền]</code> - Set min rút\n"
                    "<code>/ban [ID]</code> - Cấm User\n"
                    "<code>/unban [ID]</code> - Mở cấm User\n"
                    "<code>/thongbao [Nội dung]</code> - Gửi tin nhắn cho toàn bộ User"
                )
                bot.send_message(msg.chat.id, help_text, parse_mode="HTML")
                return

            elif msg.text.startswith("/themkenh"):
                parts = msg.text.split()
                if len(parts) > 1:
                    channels.append(parts[1])
                    save_bot_data(token, {"channels_list": channels})
                    bot.send_message(msg.chat.id, f"✅ Đã thêm kênh: {parts[1]}")
                return

            elif msg.text.startswith("/xoakenh"):
                parts = msg.text.split()
                if len(parts) > 1 and parts[1] in channels:
                    channels.remove(parts[1])
                    save_bot_data(token, {"channels_list": channels})
                    bot.send_message(msg.chat.id, f"✅ Đã xóa kênh: {parts[1]}")
                return

            elif msg.text.startswith("/themcode"):
                lines = msg.text.split("\n")[1:]
                added = 0
                for line in lines:
                    c = line.strip()
                    if c and c not in codes:
                        codes.append(c)
                        added += 1
                save_bot_data(token, {"codes_list": codes})
                bot.send_message(msg.chat.id, f"✅ Thành công thêm {added} mã code. Tổng kho: {len(codes)} code.")
                return

            elif msg.text.startswith("/xoacodeall"):
                codes.clear()
                save_bot_data(token, {"codes_list": codes})
                bot.send_message(msg.chat.id, "✅ Đã xóa sạch kho code.")
                return

            elif msg.text.startswith("/naptien"):
                parts = msg.text.split()
                if len(parts) == 3:
                    t_id, amt = parts[1], int(parts[2])
                    if t_id not in userdata: userdata[t_id] = {"balance": 0}
                    userdata[t_id]["balance"] += amt
                    save_bot_data(token, {"userdata_map": userdata})
                    bot.send_message(msg.chat.id, f"✅ Đã nạp {amt}đ cho ID {t_id}.")
                return

            elif msg.text.startswith("/trutien"):
                parts = msg.text.split()
                if len(parts) == 3:
                    t_id, amt = parts[1], int(parts[2])
                    if t_id in userdata:
                        userdata[t_id]["balance"] -= amt
                        save_bot_data(token, {"userdata_map": userdata})
                        bot.send_message(msg.chat.id, f"✅ Đã trừ {amt}đ của ID {t_id}.")
                return

            elif msg.text.startswith("/thuongmoiban"):
                parts = msg.text.split()
                if len(parts) == 2:
                    config["ref_bonus"] = int(parts[1])
                    save_bot_data(token, {"config_data": config})
                    bot.send_message(msg.chat.id, f"✅ Đã cập nhật thưởng mời: {parts[1]}đ")
                return

            elif msg.text.startswith("/minrut"):
                parts = msg.text.split()
                if len(parts) == 2:
                    config["min_rut"] = int(parts[1])
                    save_bot_data(token, {"config_data": config})
                    bot.send_message(msg.chat.id, f"✅ Đã cập nhật min rút: {parts[1]}đ")
                return

            elif msg.text.startswith("/ban"):
                parts = msg.text.split()
                if len(parts) == 2:
                    b_id = parts[1]
                    if b_id not in ban_users: ban_users.append(b_id)
                    save_bot_data(token, {"ban_user_list": ban_users})
                    bot.send_message(msg.chat.id, f"✅ Đã cấm ID {b_id}.")
                return

            elif msg.text.startswith("/unban"):
                parts = msg.text.split()
                if len(parts) == 2:
                    b_id = parts[1]
                    if b_id in ban_users: ban_users.remove(b_id)
                    save_bot_data(token, {"ban_user_list": ban_users})
                    bot.send_message(msg.chat.id, f"✅ Đã bỏ cấm ID {b_id}.")
                return

            elif msg.text.startswith("/thongbao"):
                args = msg.text.split(" ", 1)
                if len(args) == 2:
                    txt = args[1]
                    sent = 0
                    for u in users:
                        try: 
                            bot.send_message(int(u), f"📢 <b>THÔNG BÁO TỪ ADMIN:</b>\n\n{txt}", parse_mode="HTML")
                            sent += 1
                        except: pass
                    bot.send_message(msg.chat.id, f"✅ Đã gửi thông báo tới {sent} người dùng.")
                return

    # ---- XỬ LÝ NÚT BẤM CALLBACK (CHECK JOIN KÊNH) ----
    elif update.callback_query:
        call = update.callback_query
        u_str = str(call.from_user.id)
        
        if call.data == "check_join":
            not_joined = []
            for ch in channels:
                try:
                    stat = bot.get_chat_member(ch, call.from_user.id).status
                    if stat in ['left', 'kicked']: not_joined.append(ch)
                except:
                    not_joined.append(ch)
                    
            if not_joined:
                msg_err = "❌ Bạn chưa tham gia đủ các kênh:\n" + "\n".join(f"💠 {ch}" for ch in not_joined)
                bot.send_message(call.message.chat.id, msg_err)
            else:
                if u_str in invited:
                    ref_id = invited.pop(u_str)
                    bonus = config.get("ref_bonus", 1000)
                    if ref_id not in userdata: userdata[ref_id] = {"balance": 0}
                    userdata[ref_id]["balance"] += bonus
                    try: bot.send_message(int(ref_id), f"🎁 Bạn nhận được {bonus}đ từ việc giới thiệu ID {u_str}!")
                    except: pass
                    save_bot_data(token, {"invited_map": invited, "userdata_map": userdata})

                menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
                menu.row("💰 Số dư của tôi", "🛒 Rút code")
                menu.row("📮MỜI BẠN BÈ", "📄 Link Game")
                menu.row("📊 Thống kê bot")
                bot.send_message(call.message.chat.id, "🎉 Cảm ơn bạn đã tham gia kênh! Bắt đầu kiếm tiền thôi.", reply_markup=menu)
            bot.answer_callback_query(call.id)

# ==========================================
# LOGIC BOT CHA (QUẢN LÝ / TẠO BOT CON)
# ==========================================
@master_bot.message_handler(commands=['start'])
def master_start(message):
    uid = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    # Lưu user vào database nếu chưa có
    try:
        supabase.table("users").upsert({"user_id": uid, "username": username, "balance": 0}).execute()
    except Exception as e:
        print(f"[LỖI LƯU USER] {e}")

    msg_welcome = (
        "🔥 <b>HỆ THỐNG QUẢN LÝ BOT TỰ ĐỘNG</b>\n\n"
        "⚡ Lệnh khả dụng:\n"
        "➡️ <code>/taobot [TOKEN]</code>: Tạo bot con dùng thử 2 ngày.\n"
        "➡️ <code>/status</code>: Kiểm tra trạng thái bot.\n"
        "➡️ <code>/id</code>: Lấy ID Telegram của bạn."
    )
    master_bot.reply_to(message, msg_welcome, parse_mode="HTML")

@master_bot.message_handler(commands=['id'])
def get_my_id(message):
    master_bot.reply_to(message, f"🆔 ID của bạn là: <code>{message.from_user.id}</code>", parse_mode="HTML")

@master_bot.message_handler(commands=['taobot'])
def master_create_bot(message):
    uid = message.from_user.id
    parts = message.text.split()
    
    if len(parts) < 2:
        master_bot.reply_to(message, "⚠️ Sử dụng cú pháp: <code>/taobot &lt;TOKEN_BOT_CON&gt;</code>", parse_mode="HTML")
        return
        
    sub_token = parts[1].strip()
    
    try:
        # Kiểm tra token có hợp lệ không
        test_bot = telebot.TeleBot(sub_token)
        bot_user = test_bot.get_me()
        
        # Cấp hạn 2 ngày
        exp_date = (datetime.now() + timedelta(days=2)).isoformat()
        
        # Lưu vào Supabase
        supabase.table("sub_bots").upsert({
            "bot_token": sub_token,
            "creator_id": str(uid),
            "admin_id": str(uid),
            "status": "running",
            "expired_at": exp_date
        }).execute()
        
        # Thiết lập webhook cho bot con về URL Render của mày
        webhook_sub_url = f"{RENDER_URL}/webhook/sub/{sub_token}"
        test_bot.remove_webhook()
        test_bot.set_webhook(url=webhook_sub_url)
        
        success_msg = (
            f"✅ <b>TẠO BOT THÀNH CÔNG!</b>\n\n"
            f"🤖 Tên Bot: @{bot_user.username}\n"
            f"⏳ Thời gian dùng thử: <b>2 ngày</b>\n"
            f"📅 Hết hạn: <code>{exp_date}</code>\n\n"
            f"👉 Nhấp vào @{bot_user.username} rồi gõ <code>/menu</code> để quản lý hệ thống của bạn!"
        )
        master_bot.reply_to(message, success_msg, parse_mode="HTML")
        
    except Exception as e:
        master_bot.reply_to(message, f"❌ Lỗi thiết lập bot con: <code>{str(e)}</code>. Kiểm tra lại Token!", parse_mode="HTML")

# ==========================================
# ENDPOINT FASTAPI DÀNH CHO WEBHOOK TỪ TELEGRAM & SEPAY
# ==========================================
@app.post("/webhook/master")
async def handle_master_webhook(request: Request):
    try:
        json_data = await request.json()
        update = types.Update.de_json(json_data)
        master_bot.process_new_updates([update])
    except Exception as e:
        print(f"[WEBHOOK MASTER LỖI] {e}")
    return Response(status_code=200)

@app.post("/webhook/sub/{token}")
async def handle_sub_webhook(token: str, request: Request):
    try:
        json_data = await request.json()
        process_sub_bot_event(token, json_data)
    except Exception as e:
        print(f"[WEBHOOK SUB LỖI] Bot con văng: {e}")
    return Response(status_code=200)

@app.post("/webhook/sepay")
async def handle_sepay_webhook(request: Request):
    try:
        data = await request.json()
        content = data.get("content", "")
        amount = int(data.get("amount", 0))
        
        print(f"[SEPAY] Nhận GD: {amount}đ - ND: {content}")
        
        if "NAP" in content.upper():
            parts = content.split()
            target_user_id = int(parts[1])  # Ví dụ cú pháp ck: NAP 123456789
            
            res = supabase.table("users").select("*").eq("user_id", target_user_id).execute()
            if res.data:
                new_bal = res.data[0].get("balance", 0) + amount
                supabase.table("users").update({"balance": new_bal}).eq("user_id", target_user_id).execute()
                
                try: 
                    master_bot.send_message(target_user_id, f"✅ Auto Bank thành công! Nạp thêm {amount}đ. Số dư: {new_bal}đ")
                except: pass
    except Exception as e:
        print(f"[SEPAY LỖI] Xử lý GD thất bại: {e}")
            
    return Response(status_code=200)

@app.get("/")
def home():
    return {"status": "Hệ thống đang chạy ngon lành!"}
