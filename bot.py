"""
AI Listing Writer v3.0 - Telegram Bot
AI驱动的电商产品listing文案生成器
支持 Amazon / Shopee / Lazada / AliExpress / TikTok Shop / 独立站 / eBay / Walmart

Features:
- /all: Batch generate for all platforms at once
- /compare: Multi-platform comparison with AI analysis
- /keywords: AI-powered SEO keyword suggestions
- /export: Export history to CSV/JSON/TXT/HTML
- /history: View generation history
- /stats: Usage statistics
- /optimize: Optimize existing listing
- /translate: Translate listing to another language
- Rate limiting + Redis persistence
"""

import re
import time
import requests
import threading

from app.config import config
from app.platforms import PLATFORMS, list_platforms
from app.ai_engine import call_ai, optimize_listing, translate_listing
from app.history import HistoryStore
from app.export import export_records
from app.keywords import suggest_keywords_ai

def _ensure_config():
    """Validate config on first real use, not on import."""
    config.validate()


_config_validated = False

API_URL = f"https://api.telegram.org/bot{config.BOT_TOKEN}"
store = HistoryStore(config.REDIS_URL, config.MAX_HISTORY)

# User states (platform selection, optimize mode, etc.)
user_states: dict[int, dict] = {}


def tg_request(method: str, params: dict = None, json_data: dict = None):
    """Make Telegram API request."""
    try:
        if json_data:
            r = requests.post(f"{API_URL}/{method}", json=json_data, timeout=35)
        else:
            r = requests.get(f"{API_URL}/{method}", params=params, timeout=35)
        return r.json()
    except Exception as e:
        print(f"[API错误] {method}: {e}")
        return None


def tg_send(chat_id: int, text: str, reply_to: int = None, parse_mode: str = "Markdown"):
    """Send message with fallback."""
    params = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if reply_to:
        params["reply_to_message_id"] = reply_to
    if parse_mode:
        params["parse_mode"] = parse_mode
    result = tg_request("sendMessage", params)
    if not result or not result.get("ok"):
        params.pop("parse_mode", None)
        result = tg_request("sendMessage", params)
    return result


def send_long(chat_id: int, text: str, header: str = "", reply_to: int = None):
    """Send long text in chunks."""
    full = header + text if header else text
    if len(full) <= 4000:
        tg_send(chat_id, full, reply_to)
        return
    chunks = [full[i:i + 4000] for i in range(0, len(full), 4000)]
    for i, chunk in enumerate(chunks):
        tg_send(chat_id, chunk, reply_to if i == 0 else None)
        time.sleep(0.3)


def detect_lang(text: str) -> str:
    """Detect if text is Chinese or English."""
    return "Chinese (简体中文)" if re.search(r'[\u4e00-\u9fff]', text) else "English"


def generate_listing(chat_id: int, msg_id: int, platform_key: str, product: str):
    """Generate listing for a single platform."""
    p = PLATFORMS[platform_key]
    lang = detect_lang(product)

    if not store.check_rate_limit(chat_id, config.RATE_LIMIT_PER_MIN):
        tg_send(chat_id, "⚠️ 请求过于频繁，请稍后再试（每分钟限10次）", msg_id)
        return

    tg_send(chat_id, f"{p['emoji']} 正在为 *{p['name']}* 生成listing...\n产品: {product}", msg_id)

    prompt = p["template"].format(product=product, lang=lang)
    result = call_ai(prompt)

    send_long(chat_id, result, f"{p['emoji']} *{p['name']} Listing*\n\n", msg_id)

    store.add_record(chat_id, platform_key, product, result)
    print(f"[生成] {platform_key} | {product[:30]} | {lang}")


def generate_all(chat_id: int, msg_id: int, product: str):
    """Batch generate for all platforms."""
    lang = detect_lang(product)

    if not store.check_rate_limit(chat_id, config.RATE_LIMIT_PER_MIN):
        tg_send(chat_id, "⚠️ 请求过于频繁，请稍后再试", msg_id)
        return

    tg_send(chat_id, f"🚀 *批量生成模式*\n产品: {product}\n正在为 {len(PLATFORMS)} 个平台生成listing...", msg_id)

    for key, p in PLATFORMS.items():
        try:
            prompt = p["template"].format(product=product, lang=lang)
            result = call_ai(prompt)
            send_long(chat_id, result, f"\n{'='*30}\n{p['emoji']} *{p['name']}*\n\n")
            store.add_record(chat_id, key, product, result)
            time.sleep(0.5)
        except Exception as e:
            tg_send(chat_id, f"⚠️ {p['name']} 生成失败: {e}")

    tg_send(chat_id, f"✅ 全部 {len(PLATFORMS)} 个平台listing已生成!")
    print(f"[批量] {product[:30]} | {lang} | {len(PLATFORMS)} platforms")


def cmd_history(chat_id: int, msg_id: int):
    """Show generation history."""
    history = store.get_history(chat_id, 10)
    if not history:
        tg_send(chat_id, "📭 暂无生成记录", msg_id)
        return
    lines = ["📋 *最近生成记录*\n"]
    for i, r in enumerate(history, 1):
        ts = time.strftime("%m-%d %H:%M", time.localtime(r["ts"]))
        lines.append(f"{i}. [{ts}] {r['platform']} — {r['product'][:40]}")
    tg_send(chat_id, "\n".join(lines), msg_id)


def cmd_stats(chat_id: int, msg_id: int):
    """Show usage stats."""
    stats = store.get_stats(chat_id)
    if stats["total"] == 0:
        tg_send(chat_id, "📊 暂无使用数据", msg_id)
        return
    lines = [f"📊 *使用统计*\n\n总生成次数: {stats['total']}\n\n*平台分布:*"]
    for p, count in sorted(stats["platforms"].items(), key=lambda x: -x[1]):
        info = PLATFORMS.get(p, {"emoji": "❓", "name": p})
        lines.append(f"  {info['emoji']} {info['name']}: {count}次")
    tg_send(chat_id, "\n".join(lines), msg_id)


def cmd_export(chat_id: int, msg_id: int, fmt: str = "csv"):
    """Export generation history in specified format."""
    history = store.get_history(chat_id, 50)
    if not history:
        tg_send(chat_id, "📭 暂无记录可导出", msg_id)
        return
    result = export_records(history, fmt)
    if result is None:
        tg_send(chat_id, f"⚠️ 不支持的格式: {fmt}\n支持: csv, json, txt, html", msg_id)
        return
    header = f"📦 *导出 ({fmt.upper()})* — {len(history)}条记录\n\n"
    send_long(chat_id, f"```\n{result}\n```", header, msg_id)


def cmd_keywords(chat_id: int, msg_id: int, product: str, platform: str = "amazon"):
    """Generate keyword suggestions for a product."""
    tg_send(chat_id, f"🔍 正在为 *{product}* 生成关键词建议...\n平台: {platform}", msg_id)
    result = suggest_keywords_ai(product, platform)
    send_long(chat_id, result, "🔍 *关键词建议*\n\n", msg_id)


def cmd_compare(chat_id: int, msg_id: int, product: str):
    """Generate and compare listings across top 3 platforms."""
    platforms_to_compare = ["amazon", "shopee", "独立站"]
    lang = detect_lang(product)

    if not store.check_rate_limit(chat_id, config.RATE_LIMIT_PER_MIN):
        tg_send(chat_id, "⚠️ 请求过于频繁，请稍后再试", msg_id)
        return

    tg_send(chat_id, f"⚖️ *对比模式*\n产品: {product}\n正在生成 {len(platforms_to_compare)} 个平台对比...", msg_id)

    results = {}
    for key in platforms_to_compare:
        p = PLATFORMS[key]
        try:
            prompt = p["template"].format(product=product, lang=lang)
            result = call_ai(prompt)
            results[key] = result
            time.sleep(0.3)
        except Exception as e:
            results[key] = f"⚠️ 生成失败: {e}"

    # Send each platform result
    for key, result in results.items():
        p = PLATFORMS[key]
        send_long(chat_id, result, f"\n{'='*30}\n{p['emoji']} *{p['name']}*\n\n")
        store.add_record(chat_id, key, product, result)

    # Generate comparison summary
    summary_prompt = f"""Compare these product listings for "{product}" across platforms.
Give a brief comparison table and recommendation for which platform's listing is strongest.

{chr(10).join(f'--- {k} ---{chr(10)}{v[:500]}' for k, v in results.items())}

Output: Comparison table + strengths/weaknesses + recommendation."""

    summary = call_ai(summary_prompt)
    send_long(chat_id, summary, "\n📊 *对比分析*\n\n")
    print(f"[对比] {product[:30]} | {len(platforms_to_compare)} platforms")


def process_message(chat_id: int, msg_id: int, text: str):
    """Route messages to handlers."""

    # Commands
    if text == "/start":
        platforms_list = list_platforms()
        tg_send(chat_id,
            f"✍️ *AI Listing Writer v2.0*\n\n"
            f"AI驱动的电商产品listing文案生成器。\n\n"
            f"📌 *选择平台:*\n{platforms_list}\n\n"
            f"🚀 /all `产品` — 一键生成全平台listing\n"
            f"⚖️ /compare `产品` — 多平台对比分析\n"
            f"🔍 /keywords `产品` — AI关键词建议\n"
            f"📋 /history — 查看生成记录\n"
            f"📊 /stats — 使用统计\n"
            f"📦 /export [csv|json|txt|html] — 导出记录\n"
            f"🔧 /optimize — 优化已有listing\n"
            f"🌍 /translate — 翻译listing\n\n"
            f"或直接发送: `平台名 产品描述`\n"
            f"例如: `amazon wireless earbuds`",
            msg_id)
        return

    if text == "/help":
        tg_send(chat_id,
            "📖 *使用帮助*\n\n"
            "*方式一:* 先选平台再输入产品\n"
            "  1. 发送 /amazon 或 /shopee 等\n"
            "  2. 输入产品关键词\n\n"
            "*方式二:* 一步到位\n"
            "  `amazon bluetooth speaker waterproof`\n\n"
            "*方式三:* 全平台批量\n"
            "  `/all 蓝牙耳机 降噪`\n\n"
            "*优化:* `/optimize` 然后粘贴已有listing\n"
            "*翻译:* `/translate en` 或 `/translate zh`",
            msg_id)
        return

    if text == "/history":
        cmd_history(chat_id, msg_id)
        return

    if text == "/stats":
        cmd_stats(chat_id, msg_id)
        return

    # /export [format]
    if text.startswith("/export"):
        parts = text.split(maxsplit=1)
        fmt = parts[1].strip() if len(parts) > 1 else "csv"
        cmd_export(chat_id, msg_id, fmt)
        return

    # /keywords [platform] product
    if text.startswith("/keywords "):
        rest = text[10:].strip()
        # Check if first word is a platform
        parts = rest.split(maxsplit=1)
        if len(parts) >= 2 and parts[0].lower() in PLATFORMS:
            threading.Thread(
                target=cmd_keywords,
                args=(chat_id, msg_id, parts[1], parts[0].lower()),
                daemon=True,
            ).start()
        else:
            threading.Thread(
                target=cmd_keywords,
                args=(chat_id, msg_id, rest),
                daemon=True,
            ).start()
        return

    # /compare product
    if text.startswith("/compare "):
        product = text[9:].strip()
        if len(product) < 2:
            tg_send(chat_id, "请输入产品描述，例: `/compare wireless earbuds`", msg_id)
            return
        threading.Thread(
            target=cmd_compare, args=(chat_id, msg_id, product), daemon=True
        ).start()
        return

    # /all - batch mode
    if text.startswith("/all "):
        product = text[5:].strip()
        if len(product) < 2:
            tg_send(chat_id, "请输入产品描述，例: `/all wireless earbuds`", msg_id)
            return
        threading.Thread(target=generate_all, args=(chat_id, msg_id, product), daemon=True).start()
        return

    # /optimize
    if text == "/optimize":
        user_states[chat_id] = {"mode": "optimize"}
        tg_send(chat_id, "🔧 请粘贴你要优化的listing文案，我会给出改进建议。\n\n先告诉我平台（如 amazon/shopee），或直接粘贴。", msg_id)
        return

    # /translate
    if text.startswith("/translate"):
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            user_states[chat_id] = {"mode": "translate", "lang": parts[1]}
            tg_send(chat_id, f"🌍 请粘贴要翻译的listing，目标语言: {parts[1]}", msg_id)
        else:
            user_states[chat_id] = {"mode": "translate", "lang": "English"}
            tg_send(chat_id, "🌍 请粘贴要翻译的listing（默认翻译为English）\n提示: `/translate zh` 指定中文", msg_id)
        return

    # Handle user states (optimize/translate mode)
    state = user_states.pop(chat_id, None)
    if state:
        if state.get("mode") == "optimize":
            tg_send(chat_id, "🔧 正在分析和优化...", msg_id)
            platform_name = state.get("platform", "e-commerce")
            result = optimize_listing(text, platform_name)
            send_long(chat_id, result, "🔧 *优化建议*\n\n", msg_id)
            return
        if state.get("mode") == "translate":
            tg_send(chat_id, f"🌍 正在翻译为 {state['lang']}...", msg_id)
            result = translate_listing(text, state["lang"])
            send_long(chat_id, result, "🌍 *翻译结果*\n\n", msg_id)
            return
        # Platform was selected, text is the product
        if state.get("platform"):
            generate_listing(chat_id, msg_id, state["platform"], text)
            return

    # Platform selection commands
    for key in PLATFORMS:
        if text == f"/{key}":
            user_states[chat_id] = {"platform": key}
            p = PLATFORMS[key]
            tg_send(chat_id,
                f"{p['emoji']} 已选择 *{p['name']}*\n\n"
                f"现在请输入产品描述/关键词:",
                msg_id)
            return

    # Inline format: "platform product"
    platform = None
    product = text
    for key in PLATFORMS:
        if text.lower().startswith(key + " "):
            platform = key
            product = text[len(key) + 1:].strip()
            break

    if platform and product and len(product) >= 2:
        generate_listing(chat_id, msg_id, platform, product)
        return

    # Unknown input
    tg_send(chat_id,
        "请选择平台或使用格式: `平台 产品描述`\n"
        "例: `amazon wireless earbuds`\n"
        "全平台: `/all 蓝牙耳机`\n"
        "发送 /start 查看所有功能",
        msg_id)


def main():
    _ensure_config()
    print(f"\n{'=' * 50}")
    print("  AI Listing Writer v3.0")
    print(f"  Model: {config.OPENAI_MODEL}")
    print(f"  Platforms: {len(PLATFORMS)}")
    print(f"  Redis: {'✅' if store.redis else '❌ (in-memory fallback)'}")
    print(f"{'=' * 50}")

    me = tg_request("getMe")
    if me and me.get("ok"):
        print(f"\n✅ @{me['result']['username']} 已上线!")
    else:
        print("\n❌ 无法连接Telegram!")
        return

    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset
            result = tg_request("getUpdates", params)
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
                    process_message(chat_id, msg_id, text)

        except KeyboardInterrupt:
            print("\n\n👋 已停止!")
            break
        except Exception as e:
            print(f"[错误] {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
