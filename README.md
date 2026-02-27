# AI Listing Writer - Telegram Bot

✍️ AI-powered e-commerce product listing generator for **6 platforms**.

[English](#english) | [中文](#中文)

## English

### Supported Platforms

| Platform | Output | Language |
|----------|--------|----------|
| 🛒 Amazon | Title + 5 Bullets + Description + Search Terms | EN/CN |
| 🧡 Shopee | 标题 + 描述 + 标签 + 规格 | EN/CN |
| 💜 Lazada | Title + Short/Long Description + Keywords | EN/CN |
| 🔴 AliExpress | Title + Description + Keywords + USPs | EN/CN |
| 🎵 TikTok Shop | 标题 + 卖点 + 描述 + 短视频脚本 | EN/CN |
| 🌐 Shopify/独立站 | SEO Title + Meta + Description + FAQ | EN/CN |

### Features

- ✅ One command, full listing — title, bullets, description, keywords, all at once
- ✅ Auto language detection (Chinese/English)
- ✅ Platform-specific SEO optimization
- ✅ TikTok Shop: includes 15-second video script
- ✅ Compatible with any OpenAI-compatible API (GPT-4o, Claude, DeepSeek, etc.)

### Quick Start

```bash
git clone https://github.com/platoba/AI-Listing-Writer.git
cd AI-Listing-Writer
cp .env.example .env
# Edit .env
pip install -r requirements.txt
python bot.py
```

### Usage

```
/amazon bluetooth earbuds noise cancelling
/shopee 蓝牙耳机 主动降噪 运动防水
/tiktok 网红同款手机壳 ins风
/lazada wireless mouse ergonomic
```

Or just type: `amazon wireless speaker` — platform + product in one line.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | ✅ | Telegram Bot Token |
| `OPENAI_API_KEY` | ✅ | OpenAI API key (or compatible) |
| `OPENAI_BASE_URL` | ❌ | Custom API endpoint |
| `OPENAI_MODEL` | ❌ | Model name (default: gpt-4o-mini) |

### License

MIT

---

## 中文

### AI电商Listing文案生成器

一个Telegram机器人，用AI为6大电商平台生成专业的产品listing文案。

### 使用方法

发送 `/平台名 产品描述` 即可：

```
/amazon 蓝牙音箱 防水 便携
/shopee wireless earbuds TWS
/tiktok 网红零食 辣条 大包装
```

自动检测中英文，生成对应语言的listing。

---

## 🔗 More Tools

- [MultiAffiliateTGBot](https://github.com/platoba/MultiAffiliateTGBot) - 5-platform affiliate link bot
- [Amazon-SP-API-Python](https://github.com/platoba/Amazon-SP-API-Python) - Modern Amazon SP-API client
