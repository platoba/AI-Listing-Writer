"""
AI Listing Writer - Telegram Bot
AI驱动的电商产品listing文案生成器
支持 Amazon / Shopee / Lazada / AliExpress / TikTok Shop / 独立站
"""

import os
import re
import time
import json
import requests

TOKEN = os.environ.get("BOT_TOKEN", "")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

if not TOKEN:
    raise ValueError("未设置 BOT_TOKEN!")
if not OPENAI_KEY:
    raise ValueError("未设置 OPENAI_API_KEY!")

API_URL = f"https://api.telegram.org/bot{TOKEN}"

PLATFORMS = {
    "amazon": {
        "name": "Amazon",
        "emoji": "🛒",
        "template": """Generate an Amazon product listing for: {product}

Output format:
**Title** (200 chars max, keyword-rich)
**Bullet Points** (5 bullets, benefit-focused)
**Description** (HTML formatted, 2000 chars)
**Search Terms** (250 chars, comma-separated backend keywords)
**Target Audience**: Who would buy this

Language: {lang}
Tone: Professional, benefit-driven, SEO-optimized"""
    },
    "shopee": {
        "name": "Shopee",
        "emoji": "🧡",
        "template": """Generate a Shopee product listing for: {product}

Output format:
**标题** (120 chars max, 含关键词+emoji)
**商品描述** (结构化, 含emoji分隔, 突出卖点)
**标签** (10个热门标签, #开头)
**规格参数** (表格形式)

Language: {lang}
Tone: 活泼、吸引眼球、适合东南亚市场"""
    },
    "lazada": {
        "name": "Lazada",
        "emoji": "💜",
        "template": """Generate a Lazada product listing for: {product}

Output format:
**Title** (keyword-rich, 150 chars)
**Short Description** (3-5 bullet points)
**Long Description** (HTML, with features table)
**Keywords** (15 keywords)

Language: {lang}
Tone: Clear, trustworthy, conversion-focused"""
    },
    "aliexpress": {
        "name": "AliExpress",
        "emoji": "🔴",
        "template": """Generate an AliExpress product listing for: {product}

Output format:
**Title** (128 chars, keyword-dense)
**Description** (HTML, image placeholders, specs table)
**Keywords** (20 keywords for search)
**Selling Points** (5 key USPs)

Language: {lang}
Tone: Value-focused, international buyer friendly"""
    },
    "tiktok": {
        "name": "TikTok Shop",
        "emoji": "🎵",
        "template": """Generate a TikTok Shop product listing for: {product}

Output format:
**标题** (short, catchy, with emoji)
**卖点** (3个核心卖点, 适合短视频口播)
**描述** (简短有力, 适合年轻人)
**标签** (10个TikTok热门标签)
**短视频脚本** (15秒带货脚本)

Language: {lang}
Tone: 年轻、潮流、有感染力"""
    },
    "独立站": {
        "name": "独立站/Shopify",
        "emoji": "🌐",
        "template": """Generate a Shopify/independent store product page for: {product}

Output format:
**SEO Title** (60 chars)
**Meta Description** (155 chars)
**H1 Headline** (compelling, benefit-driven)
**Product Description** (storytelling + features + benefits)
**FAQ** (5 common questions)
**Social Proof Copy** (review-style testimonials)

Language: {lang}
Tone: Brand-focused, storytelling, premium feel"""
    },
}


def tg_get(method, params=None):
    try:
        r = requests.get(f"{API_URL}/{method}", params=params, timeout=35)
        return r.json()
    except Exception as e:
        print(f"[API错误] {method}: {e}")
        return None


def tg_send(chat_id, text, reply_to=None, parse_mode="Markdown"):
    params = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if reply_to:
        params["reply_to_message_id"] = reply_to
    if parse_mode:
        params["parse_mode"] = parse_mode
    result = tg_get("sendMessage", params)
    # fallback without parse_mode if markdown fails
    if not result or not result.get("ok"):
        params.pop("parse_mode", None)
        result = tg_get("sendMessage", params)
    return result


def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    return tg_get("getUpdates", params)


def call_ai(prompt, system_msg="You are an expert e-commerce copywriter and SEO specialist."):
    """调用OpenAI兼容API"""
    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    try:
        r = requests.post(f"{OPENAI_BASE}/chat/completions", headers=headers, json=data, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[AI错误] {e}")
        return f"⚠️ AI生成失败: {e}"


# 用户状态
user_states = {}


def process_command(chat_id, msg_id, text):
    """处理命令和消息"""

    if text == "/start":
        platforms_list = "\n".join(f"  {v['emoji']} /{k} — {v['name']}" for k, v in PLATFORMS.items())
        tg_send(chat_id,
            f"✍️ *AI Listing Writer*\n\n"
            f"AI驱动的电商产品listing文案生成器。\n\n"
            f"📌 选择平台:\n{platforms_list}\n\n"
            f"或直接发送: `平台名 产品描述`\n"
            f"例如: `amazon wireless earbuds`\n"
            f"例如: `shopee 蓝牙耳机 降噪`\n\n"
            f"🌐 支持中英文生成",
            msg_id)
        return

    if text == "/help":
        tg_send(chat_id,
            f"📖 *使用帮助*\n\n"
            f"*方式一:* 先选平台再输入产品\n"
            f"  1. 发送 /amazon 或 /shopee 等\n"
            f"  2. 输入产品关键词\n\n"
            f"*方式二:* 一步到位\n"
            f"  发送: `平台 产品描述`\n"
            f"  例: `amazon bluetooth speaker waterproof`\n"
            f"  例: `tiktok 网红同款手机壳`\n\n"
            f"*语言:* 自动检测中英文，也可指定\n"
            f"  例: `shopee wireless mouse` → 英文listing\n"
            f"  例: `shopee 无线鼠标` → 中文listing",
            msg_id)
        return

    # 平台选择命令
    for key in PLATFORMS:
        if text == f"/{key}":
            user_states[chat_id] = {"platform": key}
            p = PLATFORMS[key]
            tg_send(chat_id,
                f"{p['emoji']} 已选择 *{p['name']}*\n\n"
                f"现在请输入产品描述/关键词:\n"
                f"例: `bluetooth earbuds noise cancelling`",
                msg_id)
            return

    # 检查是否有平台前缀
    platform = None
    product = text

    for key in PLATFORMS:
        if text.lower().startswith(key + " "):
            platform = key
            product = text[len(key)+1:].strip()
            break

    # 检查用户状态
    if not platform and chat_id in user_states:
        platform = user_states[chat_id].get("platform")
        product = text
        del user_states[chat_id]

    if not platform:
        tg_send(chat_id,
            "请先选择平台，或使用格式: `平台 产品描述`\n"
            "例: `amazon wireless earbuds`\n"
            "发送 /start 查看所有平台",
            msg_id)
        return

    if not product or len(product) < 2:
        tg_send(chat_id, "请输入产品描述/关键词", msg_id)
        return

    # 检测语言
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', product))
    lang = "Chinese (简体中文)" if has_chinese else "English"

    p = PLATFORMS[platform]
    tg_send(chat_id, f"{p['emoji']} 正在为 *{p['name']}* 生成listing...\n产品: {product}", msg_id)

    prompt = p["template"].format(product=product, lang=lang)
    result = call_ai(prompt)

    # 分段发送（Telegram消息限制4096字符）
    if len(result) > 4000:
        chunks = [result[i:i+4000] for i in range(0, len(result), 4000)]
        for i, chunk in enumerate(chunks):
            header = f"{p['emoji']} *{p['name']} Listing* ({i+1}/{len(chunks)})\n\n" if i == 0 else ""
            tg_send(chat_id, header + chunk, msg_id if i == 0 else None)
    else:
        tg_send(chat_id, f"{p['emoji']} *{p['name']} Listing*\n\n{result}", msg_id)

    print(f"[生成] {platform} | {product[:30]} | {lang}")


def main():
    print(f"\n{'='*50}")
    print(f"  AI Listing Writer Bot")
    print(f"  Model: {OPENAI_MODEL}")
    print(f"  Platforms: {len(PLATFORMS)}")
    print(f"{'='*50}")

    me = tg_get("getMe")
    if me and me.get("ok"):
        print(f"\n✅ @{me['result']['username']} 已上线!")
    else:
        print("\n❌ 无法连接Telegram!")
        return

    offset = None
    while True:
        try:
            result = get_updates(offset)
            if not result or not result.get("ok"):
                time.sleep(5)
                continue

            for update in result.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")
                if not msg:
                    continue
                chat_id = msg["chat"]["id"]
                msg_id = msg.get("message_id")
                text = (msg.get("text") or "").strip()
                if text:
                    process_command(chat_id, msg_id, text)

        except KeyboardInterrupt:
            print("\n\n👋 已停止!")
            break
        except Exception as e:
            print(f"[错误] {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
