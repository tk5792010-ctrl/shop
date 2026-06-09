import os
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response
import telebot
from telebot import types  # Cứu cánh cho cái lỗi AttributeError hãm l**
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# CẤU HÌNH MÔI TRƯỜNG & DATABASE
# ==========================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://dmnxbtayyadssvicdxtm.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_u9nAB8p-53_fxBzpP6lGDg_XInTwvfp")
MASTER_BOT_TOKEN = os.getenv("MASTER_BOT_TOKEN", "8848756408:AAEAcpMvrbihm2n7LMN-nKC-UtKGd2Dgm4g")
RENDER_URL = os.getenv("RENDER_URL", "https://shop-ws1s.onrender.com")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

# Khởi tạo instance cho Bot Cha (Master Bot)
master_bot = telebot.TeleBot(MASTER_BOT_TOKEN, threaded=False)

# ==========================================
# CÁC HÀM TIỆN ÍCH XỬ LÝ DỮ LIỆU (SUPABASE)
# ==========================================
def get_bot_data(token: str):
    res = supabase.table("sub_bots").select("*").eq("bot_token", token).execute()
    if res.data:
        return res.data[0]
    return None

def save_bot_data(token: str, updates: dict):
    supabase.table("sub_bots").update(updates).eq("bot_token", token).execute()

def check_expired(bot_info: dict) -> bool:
    if not bot_info or not bot_info.get("expired_at"):
        return True
    exp_time = datetime.fromisoformat(bot_info["expired_at"].replace("Z", "+00:00"))
    return datetime.now(exp_time.tzinfo) > exp_time

# ==========================================
# LOGIC XỬ LÝ SỰ KIỆN CHO BOT CON (SUB-BOT)
# ==========================================
def process_sub_bot_event(token: str, update_dict: dict):
    bot_info = get_bot_data(token)
    if not bot_info:
        return
        
    bot = telebot.TeleBot(token, threaded=False)
    
    # Kéo data từ DB ra
    users = bot_info.get("users_list", [])
    admins = bot_info.get("admins_list", [])
    channels = bot_info.get("channels_list", [])
    codes = bot_info.get("codes_list", [])
    ban_users = bot_info.get("ban_user_list", [])
    invited = bot_info.get("invited_map", {})
    userdata = bot_info.get("userdata_map", {})
    log_rutcode = bot_info.get("log_rutcode_list", [])
    config = bot_info.get("config_data", {})
    
    creator_id = bot_info.get("creator_id")
    if creator_id and creator_id not in admins:
        admins.append(creator_id)

    # Đọc update từ webhook (Dùng types chuẩn)
    update = types.Update.de_json(update_dict)
    
    if update.message:
        msg = update.message
        user_id = msg.from_user.id
        u_str = str(user_id)
        
        # Check hạn dùng thử
        if check_expired(bot_info):
            bot.send_message(msg.chat.id, "❌ Bot này đã hết hạn dùng thử 2 ngày. Vui lòng liên hệ Bot Cha để gia hạn!")
            return

        # Check ban
        if u_str in ban_users and not (user_id in admins):
            bot.send_message(msg.chat.id, "⛔ Bạn đã bị cấm sử dụng bot này.")
            return

        # Lệnh /start
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
            else:
                text = "🔍 Vui lòng tham gia vào tất cả các nhóm sau để bắt đầu sử dụng:\n"
                for ch in channels:
                    text += f"\n💠 {ch}"
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("✅ Tôi đã tham gia", callback_data="check_join"))
                bot.send_message(msg.chat.id, text, reply_markup=markup)
            
            save_bot_data(token, {"users_list": users, "invited_map": invited, "userdata_map": userdata})
            return

        # ==========================================
        # PHÍM CHỨC NĂNG DÀNH CHO USER BÌNH THƯỜNG
        # ==========================================
        if msg.text == "💰 Số dư của tôi":
            bal = userdata.get(u_str, {}).get("balance", 0)
            ref_b = config.get("ref_bonus", 1000)
            bot.send_message(msg.chat.id, f"💰 Số dư của bạn\n─────\n✨ Hiện tại: {bal} VND\n👉 Mời bạn bè để nhận thêm {ref_b} VND!", parse_mode="Markdown")
            return

        elif msg.text == "🛒 Rút code":
            bot.send_message(msg.chat.id, "Hướng Dẫn Thực Hiện:\n─────\n➡️ /rutcode [Tên Nhân Vật] [SỐ TIỀN]\nVD: /rutcode xuanson 1000")
            return

        elif msg.text == "📄 Link Game":
            link = config.get("game_link")
            if link:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🎮 VÔ NGAY", url=link))
                bot.send_message(msg.chat.id, f"🎮 *Link Game Chính Thức:*\n{link}", parse_mode='Markdown', reply_markup=markup)
            else:
                bot.send_message(msg.chat.id, "Hiện chưa có link game nào được cập nhật.")
            return

        elif msg.text == "📊 Thống kê bot":
            total_users = len(users)
            total_rut = len(log_rutcode)
            total_amount = sum(l.get("amount", 0) for l in log_rutcode)
            text = f"📈<b> Thống kê bot</b>\n─────\n👥 Tổng số user: <b>{total_users}</b>\n🔁 Tổng số lượt rút: <b>{total_rut}</b>\n💸 Tổng tiền đã rút: <b>{total_amount} VND</b>"
            bot.send_message(msg.chat.id, text, parse_mode="HTML")
            return

        elif msg.text == "📮MỜI BẠN BÈ":
            invite_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
            caption = f"<b>🔍 LINK GIỚI THIỆU CỦA BẠN:</b> <code>{invite_link}</code>\n\n<b>🔻 MỜI 1 BẠN = {config.get('ref_bonus', 1000)} VNĐ</b>\n<b>🤝 TỐI THIỂU RÚT: {config.get('min_rut', 10000)} VNĐ</b>"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📤 Chia sẻ vào nhóm", url=f"https://t.me/share/url?url={invite_link}"))
            
            img = config.get("invite_image")
            if img:
                bot.send_photo(msg.chat.id, photo=img, caption=caption, parse_mode="HTML", reply_markup=markup)
            else:
                bot.send_message(msg.chat.id, caption, parse_mode="HTML", reply_markup=markup)
            return

        # ==========================================
        # XỬ LÝ RÚT CODE KIẾM TIỀN MMO
        # ==========================================
        if msg.text and msg.text.startswith("/rutcode"):
            args = msg.text.split()
            if len(args) < 3:
                bot.send_message(msg.chat.id, "Dùng đúng mẫu: /rutcode <tên_nhân_vật> <số_tiền>")
                return
            
            note = args[1]
            try:
                amount = int(args[2])
            except ValueError:
                bot.send_message(msg.chat.id, "Số tiền phải là số nguyên.")
                return

            bal = userdata.get(u_str, {}).get("balance", 0)
            
            if amount < config.get("min_rut", 10000):
                bot.send_message(msg.chat.id, f"Số tiền rút tối thiểu là {config.get('min_rut', 10000)}đ.")
                return
            if bal < amount:
                bot.send_message(msg.chat.id, f"Bạn không đủ số dư để thực hiện giao dịch này.")
                return
            if not codes:
                bot.send_message(msg.chat.id, "⚠️ Kho hàng hiện đang hết code, vui lòng quay lại sau.")
                return
                
            code_out = codes.pop(0)
            userdata[u_str]["balance"] -= amount
            log_rutcode.append({"user_id": u_str, "amount": amount})
            
            bot.send_message(msg.chat.id, f"📤 Rút Thành Công {note}\n\n💵 SỐ TIỀN: {amount} VND\nCODE: <code>{code_out}</code>", parse_mode="HTML")
            
            # Báo cho toàn bộ admin
            for adm in admins:
                try:
                    bot.send_message(int(adm), f"🔔 Yêu cầu rút từ @{msg.from_user.username} (🆔: {u_str})\n- TNV: {note}\n- Số tiền: {amount} VND.\n- CODE: {code_out}")
                except: pass
                
            save_bot_data(token, {"codes_list": codes, "userdata_map": userdata, "log_rutcode_list": log_rutcode})
            return

        # ==========================================
        # QUẢN TRỊ VIÊN CHO BOT CON
        # ==========================================
        if user_id in admins:
            if msg.text.startswith("/menu"):
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("➕ /themkenh", callback_data="sub_themkenh"),
                    types.InlineKeyboardButton("➖ /xoakenh", callback_data="sub_xoakenh"),
                    types.InlineKeyboardButton("👤 /themadmin", callback_data="sub_themadmin"),
                    types.InlineKeyboardButton("❌ /xoaadmin", callback_data="sub_xoaadmin"),
                    types.InlineKeyboardButton("➕ /themcode", callback_data="sub_themcode"),
                    types.InlineKeyboardButton("🔥 /xoacodeall", callback_data="sub_xoacodeall"),
                    types.InlineKeyboardButton("📄 /dscode", callback_data="sub_dscode"),
                    types.InlineKeyboardButton("➕ /naptien", callback_data="sub_naptien"),
                    types.InlineKeyboardButton("➖ /trutien", callback_data="sub_trutien"),
                    types.InlineKeyboardButton("🎁 /thuongmoiban", callback_data="sub_thuongmoiban"),
                    types.InlineKeyboardButton("💰 /minrut", callback_data="sub_minrut"),
                    types.InlineKeyboardButton("🚫 /ban", callback_data="sub_ban"),
                    types.InlineKeyboardButton("✅ /unban", callback_data="sub_unban")
                )
                bot.send_message(msg.chat.id, "📋 <b>Menu quản trị hệ thống:</b>", reply_markup=markup, parse_mode="HTML")
                return

            elif msg.text.startswith("/themkenh"):
                parts = msg.text.split()
                if len(parts) > 1:
                    channels.append(parts[1])
                    save_bot_data(token, {"channels_list": channels})
                    bot.send_message(msg.chat.id, f"✅ Đã thêm kênh bắt buộc: {parts[1]}")
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
                bot.send_message(msg.chat.id, f"✅ Thành công thêm {added} mã code vào hệ thống.")
                return

            elif msg.text.startswith("/xoacodeall"):
                codes.clear()
                save_bot_data(token, {"codes_list": codes})
                bot.send_message(msg.chat.id, "✅ Đã xóa toàn bộ kho code.")
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

            elif msg.text.startswith("/ban"):
                parts = msg.text.split()
                if len(parts) == 2:
                    b_id = parts[1]
                    if b_id not in ban_users: ban_users.append(b_id)
                    save_bot_data(token, {"ban_user_list": ban_users})
                    bot.send_message(msg.chat.id, f"✅ Đã ban người dùng ID {b_id}.")
                return
                
            elif msg.text.startswith("/unban"):
                parts = msg.text.split()
                if len(parts) == 2:
                    b_id = parts[1]
                    if b_id in ban_users: ban_users.remove(b_id)
                    save_bot_data(token, {"ban_user_list": ban_users})
                    bot.send_message(msg.chat.id, f"✅ Đã gỡ ban người dùng ID {b_id}.")
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
                    bot.send_message(msg.chat.id, f"✅ Đã cập nhật mức rút tối thiểu: {parts[1]}đ")
                return

            elif msg.text.startswith("/uplink"):
                parts = msg.text.split()
                if len(parts) == 2:
                    config["game_link"] = parts[1]
                    save_bot_data(token, {"config_data": config})
                    bot.send_message(msg.chat.id, f"✅ Đã cập nhật link game: {parts[1]}")
                return

            elif msg.text.startswith("/linkanh"):
                parts = msg.text.split()
                if len(parts) == 2:
                    config["invite_image"] = parts[1]
                    save_bot_data(token, {"config_data": config})
                    bot.send_message(msg.chat.id, f"✅ Đã cập nhật ảnh nền mời: {parts[1]}")
                return

            elif msg.text.startswith("/thongbao"):
                args = msg.text.split(" ", 1)
                if len(args) == 2:
                    txt = args[1]
                    success_count = 0
                    for u in users:
                        try: 
                            bot.send_message(int(u), txt)
                            success_count += 1
                        except: pass
                    bot.send_message(msg.chat.id, f"📢 Đã phát thông báo thành công tới {success_count} user.")
                return

    # Xử lý Callback (Nút bấm mượt mà)
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
                    try:
                        bot.send_message(int(ref_id), f"🎁 Bạn được cộng {bonus}đ từ lượt giới thiệu ID {u_str}!")
                    except: pass
                    save_bot_data(token, {"invited_map": invited, "userdata_map": userdata})

                menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
                menu.row("💰 Số dư của tôi")
                menu.row("🛒 Rút code", "📮MỜI BẠN BÈ")
                menu.row("📄 Link Game", "📊 Thống kê bot")
                bot.send_message(call.message.chat.id, "🎉 Chúc mừng bạn đã đăng ký thành công hệ thống!", reply_markup=menu)
            bot.answer_callback_query(call.id)
            
        elif call.data.startswith("sub_"):
            cmd = call.data.replace("sub_", "")
            cmd_hints = {
                "themkenh": "/themkenh @username_kenh", "xoakenh": "/xoakenh @username_kenh",
                "themadmin": "/themadmin user_id", "xoaadmin": "/xoaadmin user_id",
                "themcode": "/themcode (xuống dòng dán danh sách code)", "xoacodeall": "/xoacodeall",
                "dscode": "/dscode", "naptien": "/naptien user_id số_tiền",
                "trutien": "/trutien user_id số_tiền", "thuongmoiban": "/thuongmoiban số_tiền",
                "minrut": "/minrut số_tiền", "ban": "/ban user_id", "unban": "/unban user_id"
            }
            if cmd in cmd_hints:
                bot.send_message(call.message.chat.id, f"✏️ Hãy gõ cú pháp: <code>{cmd_hints[cmd]}</code>", parse_mode="HTML")
            bot.answer_callback_query(call.id)

# ==========================================
# LOGIC HỆ THỐNG ĐIỀU PHỐI (MASTER BOT)
# ==========================================
@master_bot.message_handler(commands=['start'])
def master_start(message):
    uid = message.from_user.id
    supabase.table("users").upsert({"user_id": uid, "username": message.from_user.username}).execute()
    
    msg_welcome = (
        "🔥 **HỆ THỐNG KHỞI TẠO BOT KIẾM TIỀN AUTOMATION**\n\n"
        "⚡ Lệnh khả dụng:\n"
        "➡️ `/taobot <TOKEN>` : Khởi tạo bot con sử dụng thử trong 2 ngày.\n"
        "➡️ `/status` : Kiểm tra tình trạng hoạt động các dòng bot của bạn.\n"
        "➡️ `/id` : Lấy nhanh ID định danh tài khoản Telegram của bạn."
    )
    master_bot.reply_to(message, msg_welcome, parse_mode="Markdown")

@master_bot.message_handler(commands=['id'])
def master_id(message):
    master_bot.reply_to(message, f"🆔 ID Telegram của bạn là: `{message.from_user.id}`", parse_mode="Markdown")

@master_bot.message_handler(commands=['taobot'])
def master_create_bot(message):
    uid = message.from_user.id
    parts = message.text.split()
    if len(parts) < 2:
        master_bot.reply_to(message, "⚠️ Vui lòng sử dụng cấu trúc: `/taobot <TOKEN_BOT_CON>`", parse_mode="Markdown")
        return
        
    sub_token = parts[1].strip()
    
    try:
        test_bot = telebot.TeleBot(sub_token)
        bot_user = test_bot.get_me()
        
        exp_date = (datetime.now() + timedelta(days=2)).isoformat()
        
        supabase.table("sub_bots").upsert({
            "bot_token": sub_token,
            "creator_id": uid,
            "admin_id": uid,
            "status": "running",
            "expired_at": exp_date
        }).execute()
        
        webhook_url = f"{RENDER_URL}/webhook/sub/{sub_token}"
        test_bot.remove_webhook()
        test_bot.set_webhook(url=webhook_url)
        
        success_msg = (
            f"✅ **TẠO BOT THÀNH CÔNG!**\n\n"
            f"🤖 Tên Bot: @{bot_user.username}\n"
            f"⏳ Thời gian dùng thử: **2 ngày**\n"
            f"📅 Hết hạn: `{exp_date}`\n\n"
            f"👉 Nhấp vào @{bot_user.username} rồi gõ `/menu` để thiết lập kênh, nạp code!"
        )
        master_bot.reply_to(message, success_msg, parse_mode="Markdown")
        
    except Exception as e:
        master_bot.reply_to(message, f"❌ Lỗi thiết lập bot con: `{str(e)}`. Vui lòng kiểm tra lại Token.")

@master_bot.message_handler(commands=['status'])
def master_status(message):
    uid = message.from_user.id
    res = supabase.table("sub_bots").select("*").eq("creator_id", uid).execute()
    if not res.data:
        master_bot.reply_to(message, "Bạn chưa khởi tạo con bot nào trên hệ thống.")
        return
        
    txt = "📊 **DANH SÁCH BOT CỦA BẠN:**\n"
    for b in res.data:
        token_hide = b['bot_token'][:10] + "..."
        txt += f"\n🤖 Token: `{token_hide}`\n⏳ Hạn dùng: `{b['expired_at']}`\n"
    master_bot.reply_to(message, txt, parse_mode="Markdown")

# ==========================================
# THIẾT LẬP ROUTING ENDPOINT (FASTAPI GATEWAY & SEPAY WEBHOOK)
# ==========================================
@app.post("/webhook/master")
async def handle_master_webhook(request: Request):
    json_data = await request.json()
    update = types.Update.de_json(json_data)
    master_bot.process_new_updates([update])
    return Response(status_code=200)

@app.post("/webhook/sub/{token}")
async def handle_sub_webhook(token: str, request: Request):
    json_data = await request.json()
    try:
        process_sub_bot_event(token, json_data)
    except Exception as e:
        print(f"Lỗi thực thi bot con [{token[:5]}]: {e}")
    return Response(status_code=200)

@app.post("/webhook/sepay")
async def handle_sepay_webhook(request: Request):
    data = await request.json()
    content = data.get("content", "")
    amount = int(data.get("amount", 0))
    
    # Logic Auto Bank SePay
    if "NAP" in content.upper():
        try:
            parts = content.split()
            target_user_id = int(parts[1])  # Ví dụ content: NAP 123456789
            
            res = supabase.table("users").select("*").eq("user_id", target_user_id).execute()
            if res.data:
                new_bal = res.data[0]["balance"] + amount
                supabase.table("users").update({"balance": new_bal}).eq("user_id", target_user_id).execute()
                
                try: 
                    master_bot.send_message(target_user_id, f"✅ Hệ thống đã nhận {amount}đ từ Auto Bank. Số dư mới: {new_bal}đ")
                except: pass
        except Exception as e:
            print(f"Lỗi xử lý cộng tiền Webhook SePay: {e}")
            
    return Response(status_code=200)

@app.get("/")
def home():
    return {"status": "Live", "message": "Hệ thống Automation đang chạy mượt 100%!"}
