# AI Listing Writer v2.0 - Telegram Bot

[![CI](https://github.com/platoba/AI-Listing-Writer/actions/workflows/ci.yml/badge.svg)](https://github.com/platoba/AI-Listing-Writer/actions)

✍️ AI-powered e-commerce product listing generator for **8 platforms**.

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
| 🏷️ eBay | Title + Item Specifics + Description + Shipping | EN/CN |
| 🔵 Walmart | Product Name + Features + Descriptions + Attributes | EN/CN |

### v2.0 New Features

- 🚀 **Batch Mode** — `/all product` generates listings for all 8 platforms at once
- 🔧 **Optimize** — `/optimize` analyzes and improves existing listings
- 🌍 **Translate** — `/translate zh` translates listings while preserving SEO structure
- 📋 **History** — `/history` view your recent generations
- 📊 **Stats** — `/stats` usage statistics by platform
- ⚡ **Rate Limiting** — configurable per-minute limits
- 🔄 **Retry Logic** — automatic retry on API failures with exponential backoff
- 🐳 **Docker Compose** — one-command deployment with Redis persistence
- 🏗️ **Modular Architecture** — clean separation: config / platforms / AI engine / history

### Quick Start

```bash
git clone https://github.com/platoba/AI-Listing-Writer.git
cd AI-Listing-Writer
cp .env.example .env
# Edit .env with your tokens
```

**Option A: Docker Compose (recommended)**
```bash
docker compose up -d
```

**Option B: Direct**
```bash
pip install -r requirements.txt
python bot.py
```

### Usage

```
/amazon bluetooth earbuds noise cancelling
/shopee 蓝牙耳机 主动降噪 运动防水
/tiktok 网红同款手机壳 ins风
/ebay vintage leather wallet handmade
/walmart kids water bottle BPA free

# Batch: all platforms at once
/all wireless earbuds premium

# Optimize existing listing
/optimize
(paste your listing)

# Translate
/translate zh
(paste English listing → Chinese)
```

### Architecture

```
AI-Listing-Writer/
├── app/
│   ├── __init__.py        # Version
│   ├── config.py          # Environment config
│   ├── platforms.py       # 8 platform templates
│   ├── ai_engine.py       # AI generation + retry + optimize + translate
│   └── history.py         # Redis/in-memory history + rate limiting
├── bot.py                 # Main bot entry point
├── tests/
│   └── test_bot.py        # 20 tests (config/platforms/AI/history/commands)
├── docker-compose.yml     # Bot + Redis
├── Dockerfile
├── .github/workflows/ci.yml
└── .env.example
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | ✅ | — | Telegram Bot Token |
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key (or compatible) |
| `OPENAI_BASE_URL` | ❌ | openai.com | Custom API endpoint |
| `OPENAI_MODEL` | ❌ | gpt-4o-mini | Model name |
| `REDIS_URL` | ❌ | localhost:6379 | Redis connection (falls back to in-memory) |
| `RATE_LIMIT_PER_MIN` | ❌ | 10 | Max requests per user per minute |
| `AI_TEMPERATURE` | ❌ | 0.7 | Generation creativity |
| `AI_MAX_TOKENS` | ❌ | 2000 | Max output tokens |

### License

MIT

---

## 中文

### AI电商Listing文案生成器 v2.0

一个Telegram机器人，用AI为8大电商平台生成专业的产品listing文案。

### v2.0 新功能

- 🚀 **批量模式** — `/all 产品` 一键生成全平台listing
- 🔧 **优化模式** — `/optimize` 分析并改进已有listing
- 🌍 **翻译模式** — `/translate en` 保持SEO结构翻译
- 📋 **历史记录** — `/history` 查看最近生成
- 📊 **使用统计** — `/stats` 按平台统计
- 🏷️ **新增eBay** — 标题+物品属性+描述+物流建议
- 🔵 **新增Walmart** — 产品名+特性+描述+属性

### 使用方法

```
/amazon 蓝牙音箱 防水 便携
/shopee wireless earbuds TWS
/tiktok 网红零食 辣条 大包装
/all 无线鼠标 静音 办公
```

### Docker一键部署

```bash
cp .env.example .env
# 编辑 .env 填入 BOT_TOKEN 和 OPENAI_API_KEY
docker compose up -d
```

---

## 🔗 More Tools

- [MultiAffiliateTGBot](https://github.com/platoba/MultiAffiliateTGBot) - 5-platform affiliate link bot
- [Amazon-SP-API-Python](https://github.com/platoba/Amazon-SP-API-Python) - Modern Amazon SP-API client
- [Shopify-Scout](https://github.com/platoba/Shopify-Scout) - AI product research tool
