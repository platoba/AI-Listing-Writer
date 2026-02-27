"""Platform templates for listing generation."""

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
Tone: Professional, benefit-driven, SEO-optimized""",
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
Tone: 活泼、吸引眼球、适合东南亚市场""",
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
Tone: Clear, trustworthy, conversion-focused""",
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
Tone: Value-focused, international buyer friendly""",
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
Tone: 年轻、潮流、有感染力""",
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
Tone: Brand-focused, storytelling, premium feel""",
    },
    "ebay": {
        "name": "eBay",
        "emoji": "🏷️",
        "template": """Generate an eBay product listing for: {product}

Output format:
**Title** (80 chars max, keyword-rich, no special chars)
**Item Specifics** (key-value pairs for category)
**Description** (HTML, professional layout, specs table)
**Condition Notes** (if applicable)
**Shipping Suggestions** (domestic + international)

Language: {lang}
Tone: Trustworthy, detailed, buyer-confidence focused""",
    },
    "walmart": {
        "name": "Walmart Marketplace",
        "emoji": "🔵",
        "template": """Generate a Walmart Marketplace product listing for: {product}

Output format:
**Product Name** (75 chars, clear and descriptive)
**Key Features** (5 bullet points, benefit-driven)
**Shelf Description** (150 chars for search results)
**Long Description** (4000 chars, rich content)
**Attributes** (brand, size, color, material, etc.)

Language: {lang}
Tone: Family-friendly, value-oriented, clear""",
    },
}


def get_platform(key: str):
    """Get platform by key (case-insensitive)."""
    return PLATFORMS.get(key.lower())


def list_platforms() -> str:
    """Format platform list for display."""
    return "\n".join(
        f"  {v['emoji']} /{k} — {v['name']}" for k, v in PLATFORMS.items()
    )
