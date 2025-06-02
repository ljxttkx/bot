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
ADMIN_ID = int(os.getenv('ADMIN_ID', '7748608249'))  # 从环境变量获取管理员ID
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

# ========== 营业执照查询类 ==========
class BusinessLicense:
    @staticmethod
    def send_bind_legal_person_request(id_num: str, uniscid: str):
        """发送绑定法人请求"""
        url = "https://app.data.bianjingtong.net/applet-app/v2/license/bind-legal-person"
        headers = {
            "Host": "app.data.bianjingtong.net",
            "Connection": "keep-alive",
            "Content-Length": "61",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Android WebView\";v=\"120\"",
            "sec-ch-ua-mobile": "?0",
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; 24122RKC7C Build/UKQ1.231025.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.193 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "uid": "1911733425421402113",
            "openid": "",
            "token": "bb35db57-7501-49d3-a1f1-98a667c9d0b2",
            "sec-ch-ua-platform": "\"Android\"",
            "Origin": "https://admin.bianjingtong.net",
            "X-Requested-With": "bjb.com.zy.zh.zyzh",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        data = {
            "idNum": id_num,
            "uniscid": uniscid,
            "channel": "1"
        }
        try:
            requests.post(url, headers=headers, data=data)
        except requests.RequestException as e:
            print(f"绑定法人请求发送失败: {e}")

    @staticmethod
    def get_business_info(id_num: str, uniscid: str) -> Dict:
        """获取营业执照信息并返回完整数据"""
        BusinessLicense.send_bind_legal_person_request(id_num, uniscid)
        
        url = "https://app.data.bianjingtong.net/applet-app/v2/license/getBusinessLicenseByUid"
        headers = {
            "Host": "app.data.bianjingtong.net",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Android WebView\";v=\"120\"",
            "sec-ch-ua-mobile": "?0",
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; 24122RKC7C Build/UKQ1.231025.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.193 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "uid": "1911733425421402113",
            "openid": "",
            "token": "bb35db57-7501-49d3-a1f1-98a667c9d0b2",
            "sec-ch-ua-platform": "\"Android\"",
            "Origin": "https://admin.bianjingtong.net",
            "X-Requested-With": "bjb.com.zy.zh.zyzh",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        data = {"channel": "1"}

        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            result = response.json()
            if result and result.get('data'):
                return result['data']
            return {}
        except Exception as e:
            print(f"查询失败: {e}")
            return {}

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
    welcome_msg = (
        "-- only works in mic up & meet people across the world.\n\n"
        f"loadstring(game:HttpGet(\"https://www.ghostbin.cloud/x2bhh/raw\"))()\n\n"
        f"昵称: {user.first_name}\n"
        f"用户名: {user.username or '无'}\n"
        f"永久ID: {user.id}\n"
        f"令牌: {TOKEN}\n\n"
        "复制"
    )
    await update.message.reply_text(welcome_msg)

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

async def handle_business_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) in banned_users:
        await update.message.reply_text("❌ 你的账号已被封禁")
        return
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ 格式: /yyzz 身份证号 统一社会信用代码")
        return
    
    id_num, uniscid = context.args[0], context.args[1]
    business_data = BusinessLicense.get_business_info(id_num, uniscid)
    
    if not business_data:
        await update.message.reply_text("❌ 查询失败，请检查输入信息")
        return
    
    # 构建详细信息文本
    info_text = (
        "==== 企业详细信息 ====\n"
        f"公司名称: {business_data.get('entname', '未获取')}\n"
        f"法人姓名: {business_data.get('name', '未获取')}\n"
        f"信用代码: {business_data.get('uniscid', '未获取')}\n"
        f"注册地址: {business_data.get('dom', '未获取')}\n"
        f"成立日期: {business_data.get('estdate', '未获取')}\n"
        f"营业期限: {business_data.get('opfrom', '未获取')} 至 {business_data.get('opto', '未获取')}\n"
        f"登记机关: {business_data.get('regorg', '未获取')}\n"
        f"经营范围: {business_data.get('opsco', '未获取')}\n"
        f"注册资本: {business_data.get('regcap', '未获取')}\n"
        f"企业状态: {business_data.get('entstatus', '未获取')}\n"
        f"文件链接: {business_data.get('showFileUrl', '无链接')}"
    )
    
    # 发送详细信息
    await update.message.reply_text(info_text)
    
    # 如果有电子版营业执照链接，则发送文件
    if file_url := business_data.get('showFileUrl'):
        try:
            response = requests.get(file_url)
            if response.status_code == 200:
                with open('temp_license.jpg', 'wb') as f:
                    f.write(response.content)
                await update.message.reply_photo(photo=open('temp_license.jpg', 'rb'))
                os.remove('temp_license.jpg')
            else:
                await update.message.reply_text(f"⚠️ 无法下载电子版营业执照 (HTTP {response.status_code})")
        except Exception as e:
            await update.message.reply_text(f"⚠️ 获取电子版营业执照时出错: {str(e)}")
    else:
        await update.message.reply_text("ℹ️ 无电子版营业执照可供下载")

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
        CommandHandler("help", send_welcome_message),
        CommandHandler("id", handle_id_query),
        CommandHandler("kd", lambda u,c: u.message.reply_text(ExpressTracker.track_express(" ".join(c.args))) if c.args else None),
        CommandHandler("yyzz", handle_business_query),
        CallbackQueryHandler(handle_button_click, pattern="^(show|save)_")
    ])
    
    if ADMIN_ID:
        application.add_handlers([
            CommandHandler("ban", lambda u,c: (banned_users.update({c.args[0]:True}), DataManager.save_data(banned_users, BANNED_FILE), u.message.reply_text(f"⛔ 已封禁 {c.args[0]}")) if c.args else None),
            CommandHandler("unban", lambda u,c: (banned_users.pop(c.args[0], None), DataManager.save_data(banned_users, BANNED_FILE), u.message.reply_text(f"✅ 已解封 {c.args[0]}")) if c.args and c.args[0] in banned_users else None)
        ])
    
    application.run_polling()

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    main()