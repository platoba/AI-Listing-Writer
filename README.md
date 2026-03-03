<div align="center">

# ✍️ AI Listing Writer

### AI-Powered E-Commerce Product Listing Generator for 8 Major Platforms

[![CI](https://github.com/platoba/AI-Listing-Writer/actions/workflows/ci.yml/badge.svg)](https://github.com/platoba/AI-Listing-Writer/actions)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)](https://core.telegram.org/bots)

[🌟 Features](#-features) • [🚀 Quick Start](#-quick-start) • [📖 Platforms](#-supported-platforms) • [💡 Examples](#-usage-examples)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎯 Core Features
- ✅ **8 Platform Support** - Amazon, Shopee, Lazada, AliExpress, TikTok Shop, Shopify, eBay, Walmart
- ✅ **Batch Generation** - Generate listings for all platforms at once
- ✅ **SEO Optimization** - Built-in keyword density analysis
- ✅ **Multi-Language** - English & Chinese support

</td>
<td width="50%">

### 🔥 Advanced Features
- 🚀 **Compare Mode** - AI-powered cross-platform comparison
- 🚀 **Keyword Research** - Smart SEO keyword suggestions
- 🚀 **Listing Optimizer** - Improve existing listings
- 🚀 **Export** - CSV, JSON, TXT, HTML formats

</td>
</tr>
</table>

---

## 🛒 Supported Platforms

| Platform | Output Format | Languages |
|----------|--------------|-----------|
| 🛒 **Amazon** | Title + 5 Bullets + Description + Search Terms | EN/CN |
| 🧡 **Shopee** | 标题 + 描述 + 标签 + 规格 | EN/CN |
| 💜 **Lazada** | Title + Short/Long Description + Keywords | EN/CN |
| 🔴 **AliExpress** | Title + Description + Keywords + USPs | EN/CN |
| 🎵 **TikTok Shop** | 标题 + 卖点 + 描述 + 短视频脚本 | EN/CN |
| 🌐 **Shopify** | SEO Title + Meta + Description + FAQ | EN/CN |
| 🏷️ **eBay** | Title + Item Specifics + Description + Shipping | EN/CN |
| 🔵 **Walmart** | Product Name + Features + Descriptions + Attributes | EN/CN |

---

## 🚀 Quick Start

### Prerequisites

```bash
- Python 3.9+
- Redis (optional, for history)
- Telegram Bot Token
- OpenAI API Key (or compatible endpoint)
```

### Installation

```bash
# Clone the repository
git clone https://github.com/platoba/AI-Listing-Writer.git
cd AI-Listing-Writer

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your tokens:
# - TELEGRAM_BOT_TOKEN
# - OPENAI_API_KEY
# - OPENAI_BASE_URL (optional)

# Run the bot
python bot.py
```

### Docker (Recommended)

```bash
# One-command deployment with Redis
docker-compose up -d

# View logs
docker-compose logs -f bot
```

---

## 💡 Usage Examples

### Basic Usage

```
/amazon wireless earbuds
```

Generates a complete Amazon listing with:
- SEO-optimized title
- 5 compelling bullet points
- Detailed description
- Backend search terms

### Batch Mode

```
/all bluetooth speaker
```

Generates listings for **all 8 platforms** at once with platform-specific optimizations.

### Compare Mode

```
/compare running shoes
```

AI analyzes and compares listings across platforms, highlighting:
- Best title structure
- Most effective keywords
- Platform-specific strengths

### Keyword Research

```
/keywords yoga mat
```

Returns:
- 🎯 Primary keywords (high volume, high relevance)
- 🔍 Long-tail keywords (low competition)
- 📈 Trending keywords
- ❌ Negative keywords to avoid

### Optimize Existing Listing

```
/optimize
[paste your existing listing]
```

AI analyzes and suggests improvements for:
- Keyword density
- Readability
- SEO structure
- Call-to-action

---

## 🏗️ Architecture

```
AI-Listing-Writer/
├── app/
│   ├── config.py           # Configuration management
│   ├── ai_engine.py        # OpenAI integration
│   ├── history.py          # Redis-based history
│   ├── platforms/          # Platform-specific generators
│   │   ├── amazon.py
│   │   ├── shopee.py
│   │   └── ...
│   └── utils/
│       ├── keywords.py     # Keyword research
│       └── export.py       # Export utilities
├── tests/                  # 40+ test cases
├── bot.py                  # Telegram bot entry point
└── docker-compose.yml      # Docker deployment
```

---

## 📊 Commands Reference

| Command | Description |
|---------|-------------|
| `/start` | Welcome message & help |
| `/amazon <product>` | Generate Amazon listing |
| `/shopee <product>` | Generate Shopee listing |
| `/all <product>` | Generate for all 8 platforms |
| `/compare <product>` | Compare listings across platforms |
| `/keywords <product>` | AI keyword research |
| `/optimize` | Improve existing listing |
| `/translate <lang>` | Translate listing (zh/en) |
| `/history` | View recent generations |
| `/stats` | Usage statistics |
| `/export <format>` | Export history (csv/json/txt/html) |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_platforms.py -v
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- Powered by OpenAI API
- Inspired by e-commerce best practices

---

<div align="center">

Made with ❤️ for E-Commerce Sellers

⭐ Star this repo if you find it helpful!

[Report Bug](https://github.com/platoba/AI-Listing-Writer/issues) • [Request Feature](https://github.com/platoba/AI-Listing-Writer/issues)

</div>
