import asyncio
import os
import json
import sys
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from supabase import create_client, Client

# --- CẤU HÌNH HỆ THỐNG ---
RENDER_URL = "https://shop-ws1s.onrender.com"  # Thay đổi thành URL Render của bạn
MASTER_TOKEN = "8848756408:AAEAcpMvrbihm2n7LMN-nKC-UtKGd2Dgm4g" # Token Bot Cha
SUPABASE_URL = "https://dmnxbtayyadssvicdxtm.supabase.co"
SUPABASE_KEY = "sb_publishable_u9nAB8p-53_fxBzpP6lGDg_XInTwvfp"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

master_bot = Bot(token=MASTER_TOKEN)
dp = Dispatcher()

class BotCreation(StatesGroup):
    waiting_for_type = State()
    waiting_for_name = State()
    waiting_for_admin_id = State()
    waiting_for_token = State()

# --- BÀN PHÍM ĐIỀU KHIỂN BOT CHA (GIỐNG VIDEO) ---
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🆕 Tạo Bot"), KeyboardButton(text="▶️ Quản Lý Bot")],
        [KeyboardButton(text="💥 Dịch Vụ MXH 💥"), KeyboardButton(text="💎 Mua Gói VIP")],
        [KeyboardButton(text="💳 Nạp Tiền"), KeyboardButton(text="👤 Tài Khoản")]
    ],
    resize_keyboard=True
)

@app.on_event("startup")
async def on_startup():
    await master_bot.set_webhook(f"{RENDER_URL}/webhook/master")

# --- WEBHOOK SEPAY (NẠP TIỀN TỰ ĐỘNG) ---
@app.post("/webhook/sepay")
async def sepay_webhook(request: Request):
    data = await request.json()
    content = data.get("content", "")
    amount = int(data.get("transferAmount", 0))
    try:
        parts = content.split()
        user_id = None
        for part in parts:
            if part.isdigit():
                user_id = int(part)
                break
        if user_id:
            user = supabase.table("users").select("*").eq("user_id", user_id).execute()
            if user.data:
                new_balance = user.data[0]["balance"] + amount
                supabase.table("users").update({"balance": new_balance}).eq("user_id", user_id).execute()
                await master_bot.send_message(user_id, f"💳 **Nạp tiền thành công!**\n💰 Số tiền: +{amount:,} VNĐ\n💵 Số dư hiện tại: {new_balance:,} VNĐ")
                return {"status": "success"}
    except Exception as e:
        print(f"Lỗi SePay: {e}")
    return {"status": "failed"}

@app.post("/webhook/master")
async def master_webhook(request: Request):
    update = Update.model_validate(await request.json(), context={"bot": master_bot})
    await dp.feed_update(master_bot, update)
    return Response(status_code=200)

# --- XỬ LÝ WEBHOOK CHO TẤT CẢ BOT CON ---
@app.post("/webhook/sub/{token}")
async def sub_webhook(token: str, request: Request):
    try:
        bot_res = supabase.table("sub_bots").select("*").eq("bot_token", token).execute()
        if not bot_res.data:
            return Response(status_code=404)
        
        bot_info = bot_res.data[0]
        expired_at = datetime.fromisoformat(bot_info['expired_at'].replace('z', '+00:00'))
        if datetime.now(expired_at.tzinfo) > expired_at:
            supabase.table("sub_bots").update({"status": "expired"}).eq("bot_token", token).execute()
            sub_bot = Bot(token=token)
            await sub_bot.send_message(bot_info['admin_id'], "⚠️ Bot của bạn đã hết hạn dùng thử 2 ngày! Vui lòng gia hạn gói VIP tại Bot Cha.")
            return Response(status_code=200)

        update_data = await request.json()
        await process_sub_bot_full_logic(token, bot_info, update_data)
        return Response(status_code=200)
    except Exception as e:
        print(f"Lỗi hệ thống bot con {token[:10]}: {e}")
        return Response(status_code=500)

# =========================================================================
# XỬ LÝ 100% LOGIC BẢN GỐC 456HIT.PY SANG WEBHOOK (KHÔNG CẮT GIẢM LỆNH NÀO)
# =========================================================================
async def process_sub_bot_full_logic(token: str, bot_info: dict, update_data: dict):
    bot = Bot(token=token)
    update = Update.model_validate(update_data, context={"bot": bot})
    
    # Xử lý nút bấm Callback Quy Trình Kiểm Tra Nhóm
    if update.callback_query:
        call = update.callback_query
        user_id = str(call.from_user.id)
        
        channels = json.loads(bot_info['channels_list'])
        config = json.loads(bot_info['config_data'])
        invited = json.loads(bot_info['invited_map'])
        userdata = json.loads(bot_info['userdata_map'])
        
        if call.data == "check_join":
            not_joined = []
            for ch in channels:
                try:
                    member = await bot.get_chat_member(ch, int(user_id))
                    if member.status in ['left', 'kicked']:
                        not_joined.append(ch)
                except:
                    not_joined.append(ch)
            
            if not_joined:
                msg = "❌ Bạn chưa tham gia các kênh sau:\n" + "\n".join(f"💠 {ch}" for ch in not_joined)
                await bot.send_message(call.message.chat.id, msg)
                return
            
            # Cộng thưởng giới thiệu nếu có trong map trung gian
            referrer = invited.pop(user_id, None)
            if referrer:
                ref_bonus = config.get("ref_bonus", 1)
                if referrer not in userdata:
                    userdata[referrer] = {"balance": 0}
                userdata[referrer]["balance"] += ref_bonus
                try:
                    await bot.send_message(int(referrer), f"🎁 BẠN NHẬN {ref_bonus}đ TỪ LƯỢT GIỚI THIỆU {user_id}!")
                except:
                    pass
            
            # Lưu lại trạng thái DB
            supabase.table("sub_bots").update({
                "invited_map": json.dumps(invited),
                "userdata_map": json.dumps(userdata)
            }).eq("bot_token", token).execute()
            
            # Mở phím menu chính của con bot
            menu = ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="💰 Số dư của tôi")],
                [KeyboardButton(text="🛒 Rút code"), KeyboardButton(text="📮MỜI BẠN BÈ")],
                [KeyboardButton(text="📄 Link Game"), KeyboardButton(text="📊 Thống kê bot")]
            ], resize_keyboard=True)
            await bot.send_message(call.message.chat.id, "✅ Vui lòng thả cảm xúc!3 bài gần nhất để được ưu tiên @ChiaSeKinhNghiemGame!", reply_markup=menu)
            return

        # Xử lý các Callback từ nút bấm /menu ẩn của Admin con
        elif call.data.startswith("admin_"):
            command = call.data.replace("admin_", "")
            admins = json.loads(bot_info['admins_list'])
            if user_id not in admins and int(user_id) != bot_info['admin_id']:
                return
            
            commands_map = {
                "themkenh": "/themkenh @tenkenh", "xoakenh": "/xoakenh @tenkenh",
                "themadmin": "/themadmin user_id", "xoaadmin": "/xoaadmin user_id", "dsadmin": "/dsadmin",
                "themcode": "/themcode (gửi danh sách code theo dòng)", "xoacode": "/xoacode MÃ_CODE",
                "xoacodeall": "/xoacodeall", "dscode": "/dscode", "checkcode": "/checkcode",
                "naptien": "/naptien user_id số_tiền", "trutien": "/trutien user_id số_tiền",
                "thuongmoiban": "/thuongmoiban số_tiền", "minrut": "/minrut số_tiền",
                "uplink": "/uplink LINK", "ban": "/ban user_id", "unban": "/unban user_id",
                "dsban": "/dsban", "thong_bao": "/thongbao nội dung", "chat_user": "/chat ID nội dung"
            }
            if command in commands_map:
                await bot.send_message(call.message.chat.id, f"✏️ Gõ lệnh: `{commands_map[command]}`", parse_mode="Markdown")
            return

    if not update.message or not update.message.text:
        return

    message = update.message
    text = message.text
    user_id = message.from_user.id
    str_user_id = str(user_id)
    
    # Khôi phục toàn bộ các mảng dữ liệu mô phỏng file txt/json của bot con
    users = json.loads(bot_info['users_list'])
    admins = json.loads(bot_info['admins_list'])
    channels = json.loads(bot_info['channels_list'])
    codes = json.loads(bot_info['codes_list'])
    ban_users = json.loads(bot_info['ban_user_list'])
    invited = json.loads(bot_info['invited_map'])
    userdata = json.loads(bot_info['userdata_map'])
    log_rutcode = json.loads(bot_info['log_rutcode_list'])
    config = json.loads(bot_info['config_data'])
    
    # Định nghĩa hàm kiểm tra quyền Admin nhanh dựa trên danh sách nạp vào DB
    def check_is_admin(uid):
        return str(uid) in admins or int(uid) == bot_info['admin_id']

    if str_user_id in ban_users:
        await message.answer("Bạn đã bị cấm sử dụng bot.")
        return

    # LỆNH /start GỐC
    if text.startswith("/start"):
        args = text.split()
        if str_user_id not in users:
            users.append(str_user_id)
            userdata[str_user_id] = {"balance": 0}
            if len(args) > 1 and args[1] != str_user_id:
                invited[str_user_id] = args[1]
            
            supabase.table("sub_bots").update({
                "users_list": json.dumps(users),
                "userdata_map": json.dumps(userdata),
                "invited_map": json.dumps(invited)
            }).eq("bot_token", token).execute()

        if not channels:
            await message.answer("Hiện tại chưa có kênh nào để tham gia.")
            return

        txt = "🔍 Vui lòng vào tất cả các nhóm sau để sử dụng bot\n"
        for ch in channels:
            txt += f"\n💠 {ch}"
        
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Tôi đã tham gia", callback_data="check_join")]])
        await message.answer(txt, reply_markup=markup)
        return

    # SỐ DƯ CỦA TÔI GỐC
    elif text == "💰 Số dư của tôi":
        balance = userdata.get(str_user_id, {}).get("balance", 0)
        await message.answer(f"💰 Số dư của bạn\n─────\n✨ Hiện tại: {balance} VND\n👉 Mời bạn bè để nhận thêm ngẫu nhiên {config.get('ref_bonus', 1)} VND mỗi người!", parse_mode='Markdown')

    # MỜI BẠN BÈ GỐC
    elif text == "📮MỜI BẠN BÈ":
        bot_me = await bot.get_me()
        invite_link = f"https://t.me/{bot_me.username}?start={user_id}"
        caption = f"<b>🔍 LINK GIỚI THIỆU CỦA BẠN: </b> <code>{invite_link}</code>\n\n<b>🔻 MỜI 1 BẠN = {config.get('ref_bonus', 1)} VNĐ</b>\n<b>🤝 ĐIỂM TỐI THIỂU GIAO DỊCH: {config.get('min_rut', 1000)} VNĐ</b>"
        share_url = f"https://t.me/share/url?url={invite_link}&text=Tham gia bot nhận quà: {invite_link}"
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📤 Chia sẻ vào nhóm", url=share_url)]])
        
        if config.get("invite_image"):
            await bot.send_photo(message.chat.id, photo=config["invite_image"], caption=caption, parse_mode="HTML", reply_markup=markup)
        else:
            await message.answer(caption, parse_mode="HTML", reply_markup=markup)

    # RÚT CODE NÚT GIAO DIỆN PHÍM CƠ
    elif text == "🛒 Rút code":
        await message.answer("Hướng Dẫn Thực Hiện:\n─────\n➡️/rutcode [ID TELE OR TNV]  [ SỐ TIỀN ]\nVD  /rutcode xuanson 1000")

    # LỆNH /rutcode GỐC CHẠY CHÍNH XÁC LOGIC TRỪ TIỀN
    elif text.startswith("/rutcode"):
        args = text.split()
        if len(args) < 3:
            await message.answer("Dùng: /rutcode <ghi_chú> <số_tiền>")
            return
        note = args[1]
        try:
            amount = int(args[2])
        except:
            await message.answer("Số tiền không hợp lệ.")
            return

        balance = userdata.get(str_user_id, {}).get("balance", 0)
        min_rut = config.get("min_rut", 1000)

        if amount < min_rut:
            await message.answer(f"Số tiền rút tối thiểu là {min_rut}đ.")
            return
        if balance < amount:
            await message.answer(f"Bạn không đủ số dư để rút {amount}đ.")
            return
        if not codes:
            await message.answer("⚠️ Hiện tại không còn code nào.")
            return

        code = codes.pop(0)
        userdata[str_user_id]["balance"] -= amount
        log_entry = {"user_id": str_user_id, "amount": amount}
        log_rutcode.append(log_entry)

        supabase.table("sub_bots").update({
            "codes_list": json.dumps(codes),
            "userdata_map": json.dumps(userdata),
            "log_rutcode_list": json.dumps(log_rutcode)
        }).eq("bot_token", token).execute()

        await message.answer(f"📤 Rút Thành Công {note} \n\n 💵SỐ TIỀN: {amount} VNDD\n CODE: {code}")
        
        # Bắn báo cáo về nhóm Admin hoặc Admin gốc
        try:
            await bot.send_message(bot_info['admin_id'], f"Yêu cầu rút từ @{message.from_user.username} \n(🆔: {user_id})\n\n-TÊN NHÂN VẬT: {note}\n-Số tiền: {amount} VND.\n-CODE: {code}")
        except:
            pass

    # LINK GAME PHÍM CƠ GỐC
    elif text == "📄 Link Game":
        link = config.get("game_link")
        if link:
            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎮 VÔ NGAY", url=link)]])
            await message.answer(f"🎮 *Link Game Chính Thức:*\n[{link}]({link})", parse_mode='Markdown', reply_markup=markup)
        else:
            await message.answer("Hiện chưa có link game nào được cập nhật.")

    # THỐNG KÊ BOT PHÍM CƠ GỐC
    elif text == "📊 Thống kê bot":
        total_users = len(users)
        total_rut = len(log_rutcode)
        total_amount = sum(log.get("amount", 0) for log in log_rutcode)
        await message.answer(f"📈<b> Thống kê bot</b>\n─────\n👥 Tổng số user: <b>{total_users}</b>\n🔁 Tổng số lượt rút: <b>{total_rut}</b>\n💸 Tổng tiền đã rút: <b>{total_amount}VND</b>", parse_mode="HTML")

    # =========================================================================
    # HỆ THỐNG TOÀN BỘ CÁC LỆNH ADMIN CON KHÔNG THAY ĐỔI
    # =========================================================================
    elif text == "/menu" and check_is_admin(user_id):
        markup = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
            [InlineKeyboardButton(text="➕ /themkenh", callback_data="admin_themkenh"), InlineKeyboardButton(text="➖ /xoakenh", callback_data="admin_xoakenh")],
            [InlineKeyboardButton(text="👤 /themadmin", callback_data="admin_themadmin"), InlineKeyboardButton(text="❌ /xoaadmin", callback_data="admin_xoaadmin")],
            [InlineKeyboardButton(text="📋 /dsadmin", callback_data="admin_dsadmin"), InlineKeyboardButton(text="➕ /themcode", callback_data="admin_themcode")],
            [InlineKeyboardButton(text="🗑️ /xoacode", callback_data="admin_xoacode"), InlineKeyboardButton(text="🔥 /xoacodeall", callback_data="admin_xoacodeall")],
            [InlineKeyboardButton(text="📄 /dscode", callback_data="admin_dscode"), InlineKeyboardButton(text="🔍 /checkcode", callback_data="admin_checkcode")],
            [InlineKeyboardButton(text="➕ /naptien", callback_data="admin_naptien"), InlineKeyboardButton(text="➖ /trutien", callback_data="admin_trutien")],
            [InlineKeyboardButton(text="🎁 /thuongmoiban", callback_data="admin_thuongmoiban"), InlineKeyboardButton(text="💰 /minrut", callback_data="admin_minrut")],
            [InlineKeyboardButton(text="🔗 /uplink", callback_data="admin_uplink"), InlineKeyboardButton(text="🚫 /ban", callback_data="admin_ban")],
            [InlineKeyboardButton(text="✅ /unban", callback_data="admin_unban"), InlineKeyboardButton(text="📃 /dsban", callback_data="admin_dsban")]
        ])
        await message.answer("📋 <b>Menu quản trị:</b>\nChọn thao tác bên dưới:", reply_markup=markup, parse_mode="HTML")

    elif text.startswith("/themkenh") and check_is_admin(user_id):
        args = text.split()
        if len(args) >= 2:
            chat_id = args[1]
            if chat_id not in channels:
                channels.append(chat_id)
                supabase.table("sub_bots").update({"channels_list": json.dumps(channels)}).eq("bot_token", token).execute()
                await message.answer(f"Đã thêm kênh: {chat_id}")

    elif text.startswith("/xoakenh") and check_is_admin(user_id):
        args = text.split()
        if len(args) >= 2:
            chat_id = args[1]
            if chat_id in channels:
                channels.remove(chat_id)
                supabase.table("sub_bots").update({"channels_list": json.dumps(channels)}).eq("bot_token", token).execute()
                await message.answer(f"Đã xoá kênh: {chat_id}")

    elif text.startswith("/themcode") and check_is_admin(user_id):
        lines = text.split('\n')
        if len(lines) >= 2:
            new_arr = [line.strip() for line in lines[1:] if line.strip() and line.strip() not in codes]
            codes.extend(new_arr)
            supabase.table("sub_bots").update({"codes_list": json.dumps(codes)}).eq("bot_token", token).execute()
            await message.answer(f"Đã thêm {len(new_arr)} code mới.")

    elif text == "/xoacodeall" and check_is_admin(user_id):
        supabase.table("sub_bots").update({"codes_list": "[]"}).eq("bot_token", token).execute()
        await message.answer("🗑️ Đã xóa toàn bộ mã code.")

    elif text == "/dscode" and check_is_admin(user_id):
        if not codes: await message.answer("✅ Danh sách code đang trống.")
        else: await message.answer("📄 Danh sách code:\n\n" + "\n".join(codes))

    elif text == "/checkcode" and check_is_admin(user_id):
        await message.answer(f"✅Tổng số code còn lại: {len(codes)}")

    elif text.startswith("/minrut") and check_is_admin(user_id):
        config["min_rut"] = int(text.split()[1])
        supabase.table("sub_bots").update({"config_data": json.dumps(config)}).eq("bot_token", token).execute()
        await message.answer(f"✅ Đã cập nhật min_rut = {config['min_rut']}đ")

    elif text.startswith("/thuongmoiban") and check_is_admin(user_id):
        config["ref_bonus"] = int(text.split()[1])
        supabase.table("sub_bots").update({"config_data": json.dumps(config)}).eq("bot_token", token).execute()
        await message.answer(f"✅ Đã cập nhật tiền thưởng mời bạn = {config['ref_bonus']}đ")

    elif text.startswith("/uplink") and check_is_admin(user_id):
        config["game_link"] = text.split()[1].strip()
        supabase.table("sub_bots").update({"config_data": json.dumps(config)}).eq("bot_token", token).execute()
        await message.answer(f"Đã cập nhật link game:\n{config['game_link']}")

    elif text.startswith("/ban") and check_is_admin(user_id):
        ban_id = text.split()[1].strip()
        if ban_id not in ban_users:
            ban_users.append(ban_id)
            supabase.table("sub_bots").update({"ban_user_list": json.dumps(ban_users)}).eq("bot_token", token).execute()
            await message.answer(f"Đã ban user ID {ban_id}.")

    elif text.startswith("/unban") and check_is_admin(user_id):
        unban_id = text.split()[1].strip()
        if unban_id in ban_users:
            ban_users.remove(unban_id)
            supabase.table("sub_bots").update({"ban_user_list": json.dumps(ban_users)}).eq("bot_token", token).execute()
            await message.answer(f"✅ Đã gỡ ban người dùng ID {unban_id}.")

    elif text.startswith("/naptien") and check_is_admin(user_id):
        _, target_id, amount = text.strip().split()
        if target_id not in userdata: userdata[target_id] = {"balance": 0}
        userdata[target_id]["balance"] += int(amount)
        supabase.table("sub_bots").update({"userdata_map": json.dumps(userdata)}).eq("bot_token", token).execute()
        await message.answer(f"✅ Đã nạp {amount}đ cho ID {target_id}.")

    elif text.startswith("/trutien") and check_is_admin(user_id):
        _, target_id, amount = text.strip().split()
        if target_id in userdata and userdata[target_id]["balance"] >= int(amount):
            userdata[target_id]["balance"] -= int(amount)
            supabase.table("sub_bots").update({"userdata_map": json.dumps(userdata)}).eq("bot_token", token).execute()
            await message.answer(f"✅ Đã trừ {amount}đ của ID {target_id}.")

    elif text.startswith("/themadmin") and check_is_admin(user_id):
        new_admin = text.split()[1].strip()
        if new_admin not in admins:
            admins.append(new_admin)
            supabase.table("sub_bots").update({"admins_list": json.dumps(admins)}).eq("bot_token", token).execute()
            await message.answer(f"Đã thêm admin mới: {new_admin}")

    elif text.startswith("/xoaadmin") and check_is_admin(user_id):
        remove_id = text.split()[1].strip()
        if remove_id in admins:
            admins.remove(remove_id)
            supabase.table("sub_bots").update({"admins_list": json.dumps(admins)}).eq("bot_token", token).execute()
            await message.answer(f"Đã xoá admin: {remove_id}")

    elif text == "/dsadmin" and check_is_admin(user_id):
        await message.answer(f"✅<b>Danh sách admin:</b>\n" + "\n".join(admins), parse_mode="HTML")

    elif text.startswith("/thongbao") and check_is_admin(user_id):
        content = text.split(" ", 1)[1]
        for uid in users:
            try: await bot.send_message(int(uid), content)
            except: continue
        await message.answer("✅ Đã gửi thông báo đến toàn bộ user thành công.")

    elif text.startswith("/chat") and check_is_admin(user_id):
        _, target_id, content = text.split(" ", 2)
        try:
            await bot.send_message(int(target_id), content)
            await message.answer("✅ Đã gửi tin nhắn.")
        except Exception as e:
            await message.answer(f"Lỗi: {e}")

# =========================================================================
# QUY TRÌNH LUỒNG TẠO BOT CỦA BOT CHA (MASTER BOT)
# =========================================================================
@dp.message(F.text == "🆕 Tạo Bot")
async def init_create_bot(message: Message, state: FSMContext):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Bot Mời Bạn Bè Nhận Code", callback_data="type_bot_code")]
    ])
    await message.answer("🤖 Vui lòng chọn loại Bot bạn muốn khởi tạo:", reply_markup=markup)
    await state.set_state(BotCreation.waiting_for_type)

@dp.callback_query(BotCreation.waiting_for_type)
async def process_type(call: InlineKeyboardMarkup, state: FSMContext):
    await state.update_data(bot_type=call.data)
    await call.message.answer("✍️ Nhập Tên CON BOT Nhé:\n*(Ví dụ: Bot Phát Code)*", parse_mode="Markdown")
    await state.set_state(BotCreation.waiting_for_name)

@dp.message(BotCreation.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(bot_name=message.text)
    await message.answer("🆔 Nhập Admin ID (ID Telegram người quản lý bot này):")
    await state.set_state(BotCreation.waiting_for_admin_id)

@dp.message(BotCreation.waiting_for_admin_id)
async def process_admin_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ ID phải là số. Nhập lại:")
        return
    await state.update_data(admin_id=int(message.text))
    await message.answer("🔑 Vui lòng gửi Token Bot lấy từ @BotFather:")
    await state.set_state(BotCreation.waiting_for_token)

@dp.message(BotCreation.waiting_for_token)
async def process_token(message: Message, state: FSMContext):
    token = message.text.strip()
    user_data = await state.get_data()
    user_id = message.from_user.id
    
    try:
        test_bot = Bot(token=token)
        await test_bot.get_me()
        await test_bot.set_webhook(f"{RENDER_URL}/webhook/sub/{token}")
        
        # Thiết lập thời gian thử nghiệm đúng chuẩn 2 ngày miễn phí
        expired_trial = datetime.now() + timedelta(days=2)
        
        supabase.table("sub_bots").insert({
            "bot_token": token,
            "creator_id": user_id,
            "admin_id": user_data['admin_id'],
            "bot_name": user_data['bot_name'],
            "bot_type": user_data['bot_type'],
            "status": "running",
            "expired_at": expired_trial.isoformat()
        }).execute()
        
        await message.answer(f"✅ Kết nối thành công!\n🤖 Bot **{user_data['bot_name']}** đã chạy trực tuyến.\n🎁 Nhận ngay **2 ngày thử nghiệm miễn phí**.\n📅 Hạn dùng: {expired_trial.strftime('%d/%m/%Y %H:%M')}", reply_markup=main_menu)
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ Khởi chạy thất bại: {e}")
