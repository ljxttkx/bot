#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import requests
import re
import json
from typing import Optional, Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler
)
from flask import Flask
from threading import Thread

# ========== 保持在线服务 ==========
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ========== 配置设置 ==========
TOKEN = os.getenv('TOKEN')  # 从环境变量获取
ADMIN_ID = 7748608249
USERS_FILE = "users.json"
BANNED_FILE = "banned.json"

# ========== Roblox API 类 ==========
class RobloxAPI:
    BASE_URL = "https://users.roblox.com/v1"
    THUMBNAILS_URL = "https://thumbnails.roblox.com/v1"
    
    @classmethod
    def _make_request(cls, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        try:
            response = requests.request(method, url, **kwargs)
            time.sleep(1)
            if response.status_code == 429:
                print(f"⚠️ 请求过于频繁 (URL: {url})")
                return None
            elif not response.ok:
                print(f"❌ 请求失败 [{response.status_code}]: {url}")
                return None
            return response
        except requests.RequestException as e:
            print(f"🔌 网络请求出错: {e}")
            return None
    
    @classmethod
    def get_user_id(cls, username: str) -> Optional[int]:
        url = f"{cls.BASE_URL}/usernames/users"
        payload = {"usernames": [username]}
        response = cls._make_request("POST", url, json=payload)
        if response and data := response.json().get("data"):
            return data[0]["id"]
        print(f"⚠️ 未找到用户: {username}")
        return None
    
    @classmethod
    def get_avatar_url(cls, user_id: int, size: str = "150x150", is_circular: bool = False) -> Optional[str]:
        url = f"{cls.THUMBNAILS_URL}/users/avatar"
        params = {
            "userIds": user_id,
            "size": size,
            "format": "png",
            "isCircular": str(is_circular).lower()
        }
        response = cls._make_request("GET", url, params=params)
        if response and data := response.json().get("data"):
            return data[0]["imageUrl"]
        return None

# ========== 快递查询类 ==========
class ExpressTracker:
    @staticmethod
    def clean_sign(sign):
        return re.sub(r'[\x00-\x1F\x7F]+', '', sign)

    @staticmethod
    def track_express(no: str) -> str:
        url = 'https://saas.ouqila.cn/api/sa/v1/order/queryExpress'
        headers = {
            'Host': 'saas.ouqila.cn',
            'Connection': 'keep-alive',
            'content-type': 'application/json',
            'Accept-Encoding': 'gzip,compress,br,deflate',
            'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 17_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.56(0x18003828) NetType/WIFI Language/zh_CN',
            'Referer': 'https://servicewechat.com/wx8beb5d54926e53e5/96/page-frame.html',
            'sign': ExpressTracker.clean_sign('8eb6543a-e6cd-486b-b53a-253036f3a1f4&"I)\x00\x05}Mf\x14]-l\n\x00_\x04\x0b^%F\x17\x04V-zWP\x07\x06uG*QRy\x1fa"')
        }
        data = {
            "no": no,
            "com": "auto",
            "token": "a974d03149df5518b71503502ee390a1",
            "host": "et",
            "appId": "wx8beb5d54926e53e5"
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            return response.text.encode('utf8').decode('unicode_escape')
        except requests.exceptions.RequestException as e:
            return f"请求发生错误: {e}"

# ========== 数据管理类 ==========
class DataManager:
    @staticmethod
    def load_data(filename: str) -> Dict:
        if os.path.exists(filename):
            with open(filename, "r", encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    @staticmethod
    def save_data(data: Dict, filename: str):
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

# ========== 初始化数据 ==========
users_data = DataManager.load_data(USERS_FILE)
banned_users = DataManager.load_data(BANNED_FILE)

# ========== 机器人功能 ==========
async def send_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_info = f"👤 你的账户信息\n🆔 永久ID: <code>{user.id}</code>\n📛 用户名: <code>{user.username or '无'}</code>\n📝 名字: <code>{user.first_name}</code>\n\n"
    commands = "┏━━━━━━━━━━━━━━━━━━━━┓\n┃      📋 可用命令     ┃\n┣━━━━━━━━━━━━━━━━━━━━┫\n┃/id <用户名> - 查询Roblox ID\n┃/kd <单号> - 查询快递\n┃/stray - 帮助信息\n┗━━━━━━━━━━━━━━━━━━━━┛\n"
    if user.id == ADMIN_ID:
        commands += "\n👮 管理员命令:\n/ban <用户ID> - 封禁\n/unban <用户ID> - 解封"
    await update.message.reply_text(f"👋 你好 {user.first_name}！\n\n{user_info}{commands}", parse_mode='HTML')

async def handle_id_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) in banned_users:
        await update.message.reply_text("❌ 你的账号已被封禁")
        return
    if not context.args:
        await update.message.reply_text("⚠️ 格式: /id Roblox用户名")
        return
    username = " ".join(context.args)
    if user_id := RobloxAPI.get_user_id(username):
        keyboard = [
            [InlineKeyboardButton("🖼️ 显示头像", callback_data=f"show_{user_id}")],
            [InlineKeyboardButton("💾 保存头像", callback_data=f"save_{user_id}")]
        ]
        await update.message.reply_text(
            f"✅ 查询成功\n👤 用户名: {username}\n🆔 ID: {user_id}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("❌ 用户不存在")

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, user_id = query.data.split("_")
    if avatar_url := RobloxAPI.get_avatar_url(user_id):
        await query.edit_message_text(f"🖼️ 头像链接:\n{avatar_url}" if action == "show" else f"💾 下载链接:\n{avatar_url}")

# ========== 主程序 ==========
def main():
    keep_alive()  # 启动保活服务
    
    application = Application.builder().token(TOKEN).build()
    application.add_handlers([
        CommandHandler("start", send_welcome_message),
        CommandHandler("stray", send_welcome_message),
        CommandHandler("id", handle_id_query),
        CommandHandler("kd", lambda u,c: u.message.reply_text(ExpressTracker.track_express(" ".join(c.args))) if c.args else ...,
        CallbackQueryHandler(handle_button_click, pattern="^(show|save)_")
    ])
    
    if ADMIN_ID:
        application.add_handlers([
            CommandHandler("ban", lambda u,c: (banned_users.update({c.args[0]:True}), DataManager.save_data(banned_users, BANNED_FILE), u.message.reply_text(f"⛔ 已封禁 {c.args[0]}")) if c.args else ...),
            CommandHandler("unban", lambda u,c: (banned_users.pop(c.args[0], DataManager.save_data(banned_users, BANNED_FILE), u.message.reply_text(f"✅ 已解封 {c.args[0]}")) if c.args and c.args[0] in banned_users else ...)
        ])
    
    application.run_polling()

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    main()