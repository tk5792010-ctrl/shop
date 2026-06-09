import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Cấu hình Supabase (Gắn cứng luôn như mày muốn)
SUPABASE_URL = "https://dmnxbtayyadssvicdxtm.supabase.co"
SUPABASE_KEY = "sb_publishable_u9nAB8p-53_fxBzpP6lGDg_XInTwvfp"

db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Xử lý bảng users (Dùng cho Master Bot và Nạp Tiền) ---
def get_user(user_id: int):
    res = db.table("users").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None

def create_or_update_user(user_id: int, username: str = None, balance_add: int = 0):
    user = get_user(user_id)
    if user:
        new_balance = user['balance'] + balance_add
        db.table("users").update({"username": username, "balance": new_balance}).eq("user_id", user_id).execute()
        return new_balance
    else:
        db.table("users").insert({"user_id": user_id, "username": username, "balance": balance_add}).execute()
        return balance_add

def update_user_balance(user_id: int, new_balance: int):
    db.table("users").update({"balance": new_balance}).eq("user_id", user_id).execute()

# --- Xử lý bảng sub_bots (Dùng cho Bot Con) ---
def get_sub_bot(token: str):
    res = db.table("sub_bots").select("*").eq("bot_token", token).execute()
    return res.data[0] if res.data else None

def get_bots_by_creator(creator_id: str):
    res = db.table("sub_bots").select("*").eq("creator_id", creator_id).execute()
    return res.data if res.data else []

def save_sub_bot(bot_data: dict):
    db.table("sub_bots").upsert(bot_data).execute()

def update_sub_bot_status(token: str, status: str):
    db.table("sub_bots").update({"status": status}).eq("bot_token", token).execute()

def update_sub_bot_data(token: str, updates: dict):
    db.table("sub_bots").update(updates).eq("bot_token", token).execute()
  
