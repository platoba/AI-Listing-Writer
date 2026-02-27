# AI Listing Writer

✍️ AI-powered e-commerce product listing generator for Telegram.

Generate professional product listings for **6 platforms** with one message.

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

- ✅ 6 platform-specific listing templates
- ✅ Auto language detection (Chinese/English)
- ✅ SEO-optimized output
- ✅ TikTok short video script generation
- ✅ Compatible with any OpenAI-compatible API
- ✅ Works in private chats and groups

### Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/AI-Listing-Writer.git
cd AI-Listing-Writer
cp .env.example .env
# Edit .env with your credentials
pip install -r requirements.txt
python bot.py
```

### Usage

```
# Method 1: Platform + Product
amazon wireless earbuds noise cancelling
shopee 蓝牙耳机 主动降噪

# Method 2: Select platform first
/amazon → then type product description
/shopee → then type product description
```

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

发送: `平台名 产品描述`

```
amazon bluetooth speaker waterproof
shopee 无线鼠标 静音 办公
tiktok 网红同款手机壳 ins风
lazada portable charger 20000mah
独立站 premium yoga mat eco-friendly
```

### 部署

```bash
pip install -r requirements.txt
python bot.py
```

---

## 🔗 More Tools

- [MultiAffiliateTGBot](https://github.com/YOUR_USERNAME/MultiAffiliateTGBot) - Multi-platform affiliate link bot
- [Amazon-SP-API-Python](https://github.com/YOUR_USERNAME/Amazon-SP-API-Python) - Amazon SP-API client
