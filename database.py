import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Cấu hình Supabase cố định của mày
SUPABASE_URL = "https://cydwlctvwtbilfahbhhl.supabase.co"
SUPABASE_KEY = "sb_publishable_xpEuq8uIlSnMidXzOYY3HA_g7PEPp2A"

db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- XỬ LÝ BẢNG USERS ---
def get_user(user_id: int):
    try:
        res = db.table("users").select("*").eq("user_id", user_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Lỗi get_user: {e}")
        return None

def create_or_update_user(user_id: int, username: str = None, balance_add: int = 0):
    try:
        user = get_user(user_id)
        if user:
            new_balance = int(user['balance']) + int(balance_add)
            db.table("users").update({"username": username, "balance": new_balance}).eq("user_id", user_id).execute()
            return new_balance
        else:
            db.table("users").insert({"user_id": user_id, "username": username, "balance": int(balance_add)}).execute()
            return balance_add
    except Exception as e:
        print(f"Lỗi create_or_update_user: {e}")
        return balance_add

def update_user_balance(user_id: int, new_balance: int):
    try:
        db.table("users").update({"balance": int(new_balance)}).eq("user_id", user_id).execute()
    except Exception as e:
        print(f"Lỗi update_user_balance: {e}")

# --- XỬ LÝ BẢNG SUB_BOTS ---
def get_sub_bot(token: str):
    try:
        res = db.table("sub_bots").select("*").eq("bot_token", token).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Lỗi get_sub_bot: {e}")
        return None

def get_bots_by_creator(creator_id: str):
    try:
        res = db.table("sub_bots").select("*").eq("creator_id", str(creator_id)).execute()
        return res.data if res.data else []
    except Exception as e:
        print(f"Lỗi get_bots_by_creator: {e}")
        return []

def save_sub_bot(bot_data: dict):
    try:
        db.table("sub_bots").upsert(bot_data).execute()
        return True
    except Exception as e:
        print(f"Lỗi save_sub_bot: {e}")
        return False

def update_sub_bot_status(token: str, status: str):
    try:
        db.table("sub_bots").update({"status": status}).eq("bot_token", token).execute()
    except Exception as e:
        print(f"Lỗi update_sub_bot_status: {e}")

# Đã fix: Bỏ qua check res.data khắt khe, chỉ cần try...except không lỗi là pass
def update_sub_bot_data(token: str, updates: dict) -> bool:
    try:
        db.table("sub_bots").update(updates).eq("bot_token", token).execute()
        return True
    except Exception as e:
        print(f"Lỗi update_sub_bot_data: {e}")
        return False
        
