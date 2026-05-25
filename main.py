import os
import time
import sqlite3
import telebot
from telebot import types
from flask import Flask, request, jsonify
from threading import Thread

# ==========================================
# CẤU HÌNH CẤU HÌNH HỆ THỐNG (THAY ĐỔI TẠI ĐÂY)
# ==========================================
BOT_TOKEN = "8654764187:AAGSqHRK59Ood6Z32KktLOpiytlZgWbD24E"  # Lấy từ @BotFather
ADMIN_ID = 7816353760             # ID Telegram của bạn (Kiểu số)
API_API_KEY_SEPAY = "8EX4HZHKG6C17JMLLHTBKVNJC7GPUSVBVEYWAUQLWGR2R0BM6WOPDSO53MBQFWNX" # Dùng để xác thực webhook nếu cần

# Khởi tạo Bot và Flask App (Dùng cho Webhook & Keep-alive)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ==========================================
# KHỞI TẠO DATABASE (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect("shop_game.db")
    cursor = conn.cursor()
    # Bảng người dùng
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        balance INTEGER DEFAULT 0,
                        total_deposit INTEGER DEFAULT 0)''')
    # Bảng danh mục game
    cursor.execute('''CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE)''')
    # Bảng lưu trữ Code Game
    cursor.execute('''CREATE TABLE IF NOT EXISTS game_codes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category_id INTEGER,
                        code_value TEXT,
                        price INTEGER,
                        status TEXT DEFAULT 'CON_HANG',
                        FOREIGN KEY(category_id) REFERENCES categories(id))''')
    # Bảng lịch sử hóa đơn nạp tiền
    cursor.execute('''CREATE TABLE IF NOT EXISTS invoices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        amount INTEGER,
                        code_transaction TEXT UNIQUE,
                        status TEXT DEFAULT 'PENDING',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# CÁC HÀM TRỢ GIÚP DATABASE
# ==========================================
def get_user(user_id, username=""):
    conn = sqlite3.connect("shop_game.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, balance, total_deposit FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)", (user_id, username, 0))
        conn.commit()
        user = (user_id, username, 0, 0)
    conn.close()
    return user

def update_balance(user_id, amount):
    conn = sqlite3.connect("shop_game.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ?, total_deposit = total_deposit + ? WHERE user_id = ?", (amount, amount, user_id))
    conn.commit()
    conn.close()

# ==========================================
# GIAO DIỆN ĐẸP - MENU CHÍNH
# ==========================================
def main_menu_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_shop = types.InlineKeyboardButton("🛒 Mua Code Game", callback_data="menu_shop")
    btn_profile = types.InlineKeyboardButton("👤 Tài Khoản", callback_data="menu_profile")
    btn_deposit = types.InlineKeyboardButton("💳 Nạp Tiền Auto", callback_data="menu_deposit")
    btn_support = types.InlineKeyboardButton("🤝 Hỗ Trợ / Contact", callback_data="menu_support")
    
    markup.add(btn_shop, btn_profile)
    markup.add(btn_deposit, btn_support)
    
    if user_id == ADMIN_ID:
        btn_admin = types.InlineKeyboardButton("👑 PANEL QUẢN TRỊ (ADMIN)", callback_data="admin_panel")
        markup.add(btn_admin)
    return markup

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Người dùng"
    get_user(user_id, username) # Đảm bảo user có trong hệ thống
    
    welcome_text = (
        f"🤖 <b>CHÀO MỪNG BẠN ĐẾN VỚI SHOP CODE GAME AUTO</b> 🤖\n"
        f"──────────────────────────────\n"
        f"🔥 Hệ thống phân phối Giftcode, Code Game tự động 24/7.\n"
        f"⚡️ Nạp tiền qua <b>VPBank</b> tự động xử lý trong 30 giây.\n"
        f"──────────────────────────────\n"
        f"<i>Vui lòng chọn các tính năng bên dưới:</i>"
    )
    bot.send_message(user_id, welcome_text, reply_markup=main_menu_keyboard(user_id))

# ==========================================
# XỬ LÝ CALLBACK QUY TRÌNH MUA HÀNG & PROFILE
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id
    data = call.data

    # Quay lại menu chính
    if data == "back_to_main":
        bot.edit_message_text(
            chat_id=user_id,
            message_id=call.message.message_id,
            text="🤖 <b>MENU CHÍNH - HỆ THỐNG SHOP CODE GAME</b>\nVui lòng chọn chức năng:",
            reply_markup=main_menu_keyboard(user_id)
        )
    
    # Xem thông tin tài khoản
    elif data == "menu_profile":
        _, username, balance, total_deposit = get_user(user_id)
        profile_text = (
            f"👤 <b>THÔNG TIN TÀI KHOẢN</b>\n"
            f"──────────────────────────────\n"
            f"🆔 ID Tài khoản: <code>{user_id}</code>\n"
            f"📌 Username: @{username}\n"
            f"💰 Số dư hiện tại: <b>{balance:,} VNĐ</b>\n"
            f"📈 Tổng tiền đã nạp: <b>{total_deposit:,} VNĐ</b>\n"
            f"──────────────────────────────"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Quay Lại", callback_data="back_to_main"))
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=profile_text, reply_markup=markup)

    # Xem Hướng dẫn nạp tiền
    elif data == "menu_deposit":
        deposit_text = (
            f"💳 <b>HỆ THỐNG NẠP TIỀN TỰ ĐỘNG (VPBANK)</b>\n"
            f"──────────────────────────────\n"
            f"Bạn vui lòng chuyển khoản theo thông tin chính xác bên dưới:\n\n"
            f"🏦 Ngân hàng: <b>VPBANK (Ngân hàng TMCP Việt Nam Thịnh Vượng)</b>\n"
            f"🔢 Số tài khoản: <code>0336293609</code>\n" # Thay số tk của bạn vào đây nếu sepay lấy cấu hình từ tài khoản này
            f"👤 Chủ tài khoản: <b>NGUYEN THANH HOP</b>\n"
            f"📝 Nội dung chuyển khoản bắt buộc:\n"
            f"👉 <code>NAP {user_id}</code>\n\n"
            f"⚠️ <b>LƯU Ý:</b> Nhập đúng nội dung <code>NAP {user_id}</code> để hệ thống tự động cộng tiền sau 15-30 giây."
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Kiểm tra số dư", callback_data="menu_profile"))
        markup.add(types.InlineKeyboardButton("🔙 Quay Lại", callback_data="back_to_main"))
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=deposit_text, reply_markup=markup)

    # Hỗ trợ khách hàng
    elif data == "menu_support":
        support_text = (
            f"🤝 <b>HỖ TRỢ & LIÊN HỆ KHÁCH HÀNG</b>\n"
            f"──────────────────────────────\n"
            f"Nếu gặp lỗi trong quá trình nạp tiền, mua sắm hoặc cần hợp tác, vui lòng liên hệ Admin:\n\n"
            f"👤 <b>Admin Telegram:</b> @Tên_User_Admin_Của_Bạn\n"
            f"⏰ Thời gian hỗ trợ: 08:00 - 23:00 hàng ngày.\n"
            f"🔰 Uy tín - Chất lượng - An toàn."
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Quay Lại", callback_data="back_to_main"))
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=support_text, reply_markup=markup)

    # Xem danh mục mua code game
    elif data == "menu_shop":
        conn = sqlite3.connect("shop_game.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()
        conn.close()

        if not categories:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Quay Lại", callback_data="back_to_main"))
            bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text="❌ Hiện tại shop chưa phân loại danh mục game nào!", reply_markup=markup)
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        for cat in categories:
            # Đếm số lượng code còn hàng trong danh mục này
            conn = sqlite3.connect("shop_game.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM game_codes WHERE category_id = ? AND status = 'CON_HANG'", (cat[0],))
            count = c.fetchone()[0]
            conn.close()
            
            markup.add(types.InlineKeyboardButton(f"🎮 {cat[1]} ({count} mục)", callback_data=f"buy_cat_{cat[0]}"))
        markup.add(types.InlineKeyboardButton("🔙 Quay Lại", callback_data="back_to_main"))
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text="🎮 <b>CHỌN DÒNG GAME BẠN MUỐN MUA CODE</b>", reply_markup=markup)

    # Chọn một danh mục cụ thể
    elif data.startswith("buy_cat_"):
        cat_id = int(data.split("_")[2])
        conn = sqlite3.connect("shop_game.db")
        cursor = conn.cursor()
        cursor.execute("SELECT price, COUNT(*) FROM game_codes WHERE category_id = ? AND status = 'CON_HANG' GROUP BY price", (cat_id,))
        products = cursor.fetchall()
        cursor.execute("SELECT name FROM categories WHERE id = ?", (cat_id,))
        cat_name = cursor.fetchone()[0]
        conn.close()

        markup = types.InlineKeyboardMarkup(row_width=1)
        if not products:
            markup.add(types.InlineKeyboardButton("🔙 Quay Lại", callback_data="menu_shop"))
            bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=f"❌ Thể loại <b>{cat_name}</b> tạm thời hết hàng!", reply_markup=markup)
            return

        for prod in products:
            price = prod[0]
            stock = prod[1]
            markup.add(types.InlineKeyboardButton(f"🛒 Loại Giá: {price:,} VNĐ (Còn: {stock})", callback_data=f"confirm_buy_{cat_id}_{price}"))
        
        markup.add(types.InlineKeyboardButton("🔙 Quay lại danh mục", callback_data="menu_shop"))
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=f"🎮 Phân mục: <b>{cat_name}</b>\nVui lòng lựa chọn gói giá cần mua:", reply_markup=markup)

    # Xác nhận mua code cụ thể
    elif data.startswith("confirm_buy_"):
        parts = data.split("_")
        cat_id = int(parts[2])
        price = int(parts[3])

        _, _, balance, _ = get_user(user_id)
        if balance < price:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💳 Nạp Tiền Ngay", callback_data="menu_deposit"))
            markup.add(types.InlineKeyboardButton("🔙 Quay Lại", callback_data="menu_shop"))
            bot.answer_callback_query(call.id, "❌ Tài khoản của bạn không đủ tiền!", show_alert=True)
            return

        # Thực hiện lấy code và trừ tiền an toàn bằng Transaction
        conn = sqlite3.connect("shop_game.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, code_value FROM game_codes WHERE category_id = ? AND price = ? AND status = 'CON_HANG' LIMIT 1", (cat_id, price))
        code_item = cursor.fetchone()

        if not code_item:
            conn.close()
            bot.answer_callback_query(call.id, "❌ Rất tiếc, loại code này vừa mới hết hàng!", show_alert=True)
            return

        code_db_id, code_text = code_item
        
        try:
            # Trừ tiền user
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))
            # Cập nhật trạng thái code đã bán
            cursor.execute("UPDATE game_codes SET status = 'DA_BAN' WHERE id = ?", (code_db_id,))
            conn.commit()
            
            # Gửi mã code cho khách hàng
            success_msg = (
                f"🎉 <b>MUA CODE THÀNH CÔNG!</b> 🎉\n"
                f"──────────────────────────────\n"
                f"💰 Giá tiền: <code>{price:,} VNĐ</code>\n"
                f"🔑 ĐÂY LÀ MÃ CODE CỦA BẠN:\n\n"
                f"👉 <code>{code_text}</code>\n\n"
                f"<i>(Hãy click trực tiếp vào mã code ở trên để tự động Copy)</i>\n"
                f"──────────────────────────────\n"
                f"Cảm ơn bạn đã ủng hộ dịch vụ của chúng tôi!"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Tiếp tục mua sắm", callback_data="menu_shop"))
            bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=success_msg, reply_markup=markup)
            
        except Exception as e:
            conn.rollback()
            bot.send_message(user_id, "❌ Có lỗi hệ thống xảy ra trong quá trình giao dịch. Vui lòng liên hệ Admin.")
        finally:
            conn.close()

    # ==========================================
    # CÁC CHỨC NĂNG ADMIN PANEL
    # ==========================================
    elif data == "admin_panel" and user_id == ADMIN_ID:
        adm_text = (
            f"👑 <b>HỆ THỐNG QUẢN TRỊ ADMIN PANEL</b> 👑\n"
            f"──────────────────────────────\n"
            f"Dưới đây là các lệnh thao tác nhanh cấu hình dữ liệu shop:"
        )
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ Thêm Thể Loại Game Mới", callback_data="adm_add_cat"),
            types.InlineKeyboardButton("📥 Up Thêm Code Game Mới", callback_data="adm_add_code"),
            types.InlineKeyboardButton("🔙 Thoát Admin", callback_data="back_to_main")
        )
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=adm_text, reply_markup=markup)

    elif data == "adm_add_cat" and user_id == ADMIN_ID:
        msg = bot.send_message(user_id, "⌨️ Nhập <b>Tên Thể Loại Game Mới</b> muốn thêm (Ví dụ: <i>Liên Quân Mobile, Roblox, Free Fire</i>):")
        bot.register_next_step_handler(msg, process_add_category)

    elif data == "adm_add_code" and user_id == ADMIN_ID:
        conn = sqlite3.connect("shop_game.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories")
        cats = cursor.fetchall()
        conn.close()
        
        if not cats:
            bot.send_message(user_id, "❌ Hãy tạo ít nhất một Thể loại Game trước khi Up code!")
            return
            
        markup = types.InlineKeyboardMarkup(row_width=2)
        for c in cats:
            markup.add(types.InlineKeyboardButton(c[1], callback_data=f"adm_selectcat_{c[0]}"))
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text="🎮 Chọn thể loại game bạn muốn nạp code vào:", reply_markup=markup)

    elif data.startswith("adm_selectcat_") and user_id == ADMIN_ID:
        cat_id = int(data.split("_")[2])
        msg = bot.send_message(user_id, "⌨️ Vui lòng nhập thông tin theo cấu trúc:\n<code>MệnhGiá|MãMãCode</code>\n\nVí dụ:\n<code>20000|GIFTCODE-LIENQUAN-VIP999</code>")
        bot.register_next_step_handler(msg, lambda m: process_up_code(m, cat_id))

# ==========================================
# CÁC HÀM XỬ LÝ NHẬP LIỆU PHÍA ADMIN
# ==========================================
def process_add_category(message):
    if message.text.startswith("/"): return
    cat_name = message.text.strip()
    try:
        conn = sqlite3.connect("shop_game.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (cat_name,))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ Đã thêm thành công thể loại game: <b>{cat_name}</b>", reply_markup=main_menu_keyboard(ADMIN_ID))
    except sqlite3.IntegrityError:
        bot.send_message(message.chat.id, "❌ Tên thể loại này đã tồn tại sẵn trong hệ thống.")

def process_up_code(message, cat_id):
    if message.text.startswith("/"): return
    text = message.text.strip()
    if "|" not in text:
        bot.send_message(message.chat.id, "❌ Nhập sai định dạng rồi! Vui lòng làm lại và sử dụng dấu gạch đứng | để phân tách.")
        return
    
    try:
        price_str, code_val = text.split("|", 1)
        price = int(price_str.strip())
        code_val = code_val.strip()
        
        conn = sqlite3.connect("shop_game.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO game_codes (category_id, code_value, price) VALUES (?, ?, ?)", (cat_id, code_val, price))
        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, f"✅ Thêm code thành công!\n💰 Mệnh giá bán: {price:,} VNĐ\n🔑 Code: <code>{code_val}</code>", reply_markup=main_menu_keyboard(ADMIN_ID))
    except ValueError:
        bot.send_message(message.chat.id, "❌ Mệnh giá tiền phải là số nguyên dương hợp lệ!")

# ==========================================
# WEBHOOK SEPAY - AUTO NẠP TIỀN VPBANK
# ==========================================
@app.route('/sepay-webhook', methods=['POST'])
def sepay_webhook():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
    
    # Lấy các thông số SePay gửi sang khi có giao dịch chuyển khoản mới
    content = data.get('code')            # Nội dung chuyển khoản thực tế
    amount = data.get('transferAmount')    # Số tiền khách chuyển khoản (Kiểu số)
    transaction_id = data.get('id')        # Mã giao dịch duy nhất của SePay

    if not content or not amount:
        return jsonify({"status": "error", "message": "Missing arguments"}), 200

    # Phân tích nội dung chuyển khoản "NAP XXXXXXX"
    content = content.strip().upper()
    if content.startswith("NAP"):
        try:
            parts = content.split(" ")
            if len(parts) >= 2:
                user_id = int(parts[1]) # Lấy ID người dùng từ nội dung chuyển tiền
                
                # Thực hiện cộng tiền vào Database của user đó
                conn = sqlite3.connect("shop_game.db")
                cursor = conn.cursor()
                
                # Kiểm tra trùng lặp giao dịch (đề phòng gửi trùng webhook)
                cursor.execute("SELECT id FROM invoices WHERE code_transaction = ?", (str(transaction_id),))
                if cursor.fetchone():
                    conn.close()
                    return jsonify({"status": "success", "message": "Transaction already processed"}), 200
                
                # Kiểm tra user có tồn tại không
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                if cursor.fetchone():
                    # Thêm hóa đơn & cộng tiền tài khoản
                    cursor.execute("INSERT INTO invoices (user_id, amount, code_transaction, status) VALUES (?, ?, ?, 'SUCCESS')", 
                                   (user_id, amount, str(transaction_id)))
                    cursor.execute("UPDATE users SET balance = balance + ?, total_deposit = total_deposit + ? WHERE user_id = ?", 
                                   (amount, amount, user_id))
                    conn.commit()
                    conn.close()
                    
                    # Gửi tin nhắn thông báo tự động cho khách hàng qua Telegram bot
                    deposit_alert = (
                        f"💳 <b>THÔNG BÁO NẠP TIỀN THÀNH CÔNG!</b>\n"
                        f"──────────────────────────────\n"
                        f"💰 Hệ thống đã nhận: <b>+{amount:,} VNĐ</b> từ ngân hàng VPBank.\n"
                        f"🆔 Mã giao dịch: <code>{transaction_id}</code>\n"
                        f"⚡ Số dư của bạn đã được cập nhật tự động thành công!\n"
                        f"🛒 Chúc bạn mua sắm vui vẻ."
                    )
                    bot.send_message(user_id, deposit_alert)
                    
                    # Thông báo cho Admin biết có người vừa nạp tiền
                    bot.send_message(ADMIN_ID, f"👑 <b>Admin Alert:</b> User <code>{user_id}</code> vừa nạp <b>{amount:,} VNĐ</b> thành công!")
                    return jsonify({"status": "success", "message": "Processed successfully"}), 200
                else:
                    conn.close()
                    return jsonify({"status": "error", "message": "User not found"}), 200
        except Exception as e:
            print(f"Lỗi xử lý webhook: {str(e)}")
            return jsonify({"status": "error", "message": "Internal error"}), 500

    return jsonify({"status": "success", "message": "Content not matching format"}), 200

# Route mặc định để Render check sống/chết web (UptimeRobot ping vào đây)
@app.route('/')
def home():
    return "Bot Game is Running Live 24/7!", 200

# ==========================================
# CƠ CHẾ LIVE 24/7 VÀ CHẠY ĐỒNG THỜI BOT + WEB
# ==========================================
def run_flask():
    # Render yêu cầu dùng PORT lấy từ môi trường hệ thống
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

def run_bot():
    while True:
        try:
            print("Khởi chạy polling Telegram Bot...")
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Lỗi Polling, khởi động lại sau 5 giây... Chi tiết lỗi: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # Luồng 1: Chạy Flask để hứng Webhook từ SePay và cổng Ping Sống
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    # Luồng 2: Chạy Polling nhận lệnh Telegram
    run_bot()
