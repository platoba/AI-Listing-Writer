"""Tests for the platform validator module."""
from app.validator import (
    validate_listing,
    validate_batch,
    ValidationResult,
    Severity,
    PLATFORM_RULES,
    _extract_sections,
)


# ── Section Extraction ──────────────────────────────────────

class TestExtractSections:
    def test_extracts_bold_sections(self):
        text = """**Title** Some product title
**Bullet Points** First bullet
**Description** A description here"""
        sections = _extract_sections(text)
        assert "title" in sections
        assert "bullet points" in sections
        assert "description" in sections

    def test_handles_colon_separator(self):
        text = "**Title**: My Product Name\n**Price**: $29.99"
        sections = _extract_sections(text)
        assert "title" in sections
        assert "My Product Name" in sections["title"]

    def test_handles_chinese_sections(self):
        text = "**标题**: 测试产品\n**描述**: 这是描述"
        sections = _extract_sections(text)
        assert "标题" in sections

    def test_empty_text(self):
        assert _extract_sections("") == {}

    def test_no_bold_sections(self):
        assert _extract_sections("plain text without sections") == {}


# ── Amazon Validation ───────────────────────────────────────

class TestAmazonValidation:
    def test_valid_listing_passes(self):
        listing = """**Title** Premium Wireless Bluetooth Headphones - Noise Cancelling, 40H Battery
**Bullet Points** Crystal clear sound with advanced drivers
**Description** Experience premium audio quality with our latest headphones.
**Search Terms** wireless headphones, bluetooth, noise cancelling, premium audio"""
        result = validate_listing(listing, "amazon")
        assert result.passed
        assert result.score >= 70

    def test_missing_sections_fails(self):
        listing = "**Title** Just a title\nSome random text"
        result = validate_listing(listing, "amazon")
        assert result.error_count > 0
        assert result.score < 100

    def test_title_too_long(self):
        long_title = "A" * 250
        listing = f"**Title** {long_title}\n**Bullet Points** Bullets\n**Description** Desc\n**Search Terms** terms"
        result = validate_listing(listing, "amazon")
        errors = [i for i in result.issues if i.severity == Severity.ERROR and "title" in i.field]
        assert len(errors) > 0

    def test_forbidden_chars_in_title(self):
        listing = "**Title** ★★★ Best Product FREE Shipping ★★★\n**Bullet Points** x\n**Description** y\n**Search Terms** z"
        result = validate_listing(listing, "amazon")
        issues = [i for i in result.issues if "forbidden" in i.message.lower()]
        assert len(issues) > 0

    def test_forbidden_patterns(self):
        listing = "**Title** #1 Best Seller Free Shipping Deal\n**Bullet Points** x\n**Description** y\n**Search Terms** z"
        result = validate_listing(listing, "amazon")
        warnings = [i for i in result.issues if i.severity == Severity.WARNING]
        assert len(warnings) > 0

    def test_all_caps_warning(self):
        listing = "**Title** SUPER AMAZING PRODUCT BUY NOW TODAY INCREDIBLE DEAL MUST HAVE\n**Bullet Points** x\n**Description** y\n**Search Terms** z"
        result = validate_listing(listing, "amazon")
        caps_issues = [i for i in result.issues if "caps" in i.message.lower()]
        assert len(caps_issues) > 0


# ── eBay Validation ─────────────────────────────────────────

class TestEbayValidation:
    def test_valid_ebay_listing(self):
        listing = """**Title** Vintage Leather Wallet Bifold Card Holder
**Item Specifics** Material: Genuine Leather
**Description** Quality craftsmanship with classic design."""
        result = validate_listing(listing, "ebay")
        assert result.passed

    def test_title_over_80_chars(self):
        long_title = "X" * 100
        listing = f"**Title** {long_title}\n**Item Specifics** x\n**Description** y"
        result = validate_listing(listing, "ebay")
        errors = [i for i in result.issues if i.severity == Severity.ERROR and "title" in i.field]
        assert len(errors) > 0

    def test_forbidden_ebay_chars(self):
        listing = "**Title** ★ Amazing Product ❤ Must See ✅\n**Item Specifics** x\n**Description** y"
        result = validate_listing(listing, "ebay")
        issues = [i for i in result.issues if "forbidden" in i.message.lower()]
        assert len(issues) > 0


# ── Walmart Validation ──────────────────────────────────────

class TestWalmartValidation:
    def test_valid_walmart_listing(self):
        listing = """**Product Name** Quality Kitchen Blender
**Key Features** Powerful 1200W motor for smooth blending
**Shelf Description** High performance blender for everyday use
**Long Description** Detailed description of the product."""
        result = validate_listing(listing, "walmart")
        assert result.passed

    def test_title_over_75_chars(self):
        long_title = "W" * 80
        listing = f"**Product Name** {long_title}\n**Key Features** x\n**Shelf Description** y\n**Long Description** z"
        result = validate_listing(listing, "walmart")
        errors = [i for i in result.issues if i.severity == Severity.ERROR]
        assert len(errors) > 0


# ── Shopee Validation ───────────────────────────────────────

class TestShopeeValidation:
    def test_valid_shopee_listing(self):
        listing = """**标题** 时尚女包 轻奢手提包 2026新款
**描述** 高品质面料，精致做工，时尚百搭
**标签** #女包 #手提包 #轻奢 #时尚"""
        result = validate_listing(listing, "shopee")
        assert result.passed

    def test_title_too_long(self):
        long_title = "好" * 130
        listing = f"**标题** {long_title}\n**描述** 描述\n**标签** #标签"
        result = validate_listing(listing, "shopee")
        errors = [i for i in result.issues if i.severity == Severity.ERROR]
        assert len(errors) > 0


# ── TikTok Shop Validation ──────────────────────────────────

class TestTikTokValidation:
    def test_valid_tiktok_listing(self):
        listing = """**标题** 🔥爆款保温杯
**卖点** 12小时保温 轻便携带
**描述** 网红同款保温杯
**标签** #保温杯 #网红 #爆款"""
        result = validate_listing(listing, "tiktok")
        assert result.passed


# ── Independent Store Validation ────────────────────────────

class TestIndependentStoreValidation:
    def test_valid_shopify_listing(self):
        listing = """**SEO Title** Premium Coffee Beans | Fresh Roast
**Meta Description** Discover our premium single-origin coffee beans
**Description** Our coffee beans are sourced from the finest farms
**FAQ** Q: How fresh? A: Roasted weekly"""
        result = validate_listing(listing, "独立站")
        assert result.passed


# ── Keyword Stuffing ────────────────────────────────────────

class TestKeywordStuffing:
    def test_detects_stuffing(self):
        listing = " ".join(["headphones"] * 30 + ["wireless"] * 5 + ["other word"] * 5)
        result = validate_listing(f"**Title** Test\n**Bullet Points** x\n**Description** {listing}\n**Search Terms** y", "amazon")
        stuffing_issues = [i for i in result.issues if "stuffing" in i.message.lower()]
        assert len(stuffing_issues) > 0

    def test_no_stuffing_for_normal_text(self):
        listing = "This premium wireless headphone features noise cancellation, long battery life, and comfortable ear cushions for extended use."
        result = validate_listing(f"**Title** Good\n**Bullet Points** x\n**Description** {listing}\n**Search Terms** y", "amazon")
        stuffing_issues = [i for i in result.issues if "stuffing" in i.message.lower()]
        assert len(stuffing_issues) == 0


# ── Unknown Platform ────────────────────────────────────────

class TestUnknownPlatform:
    def test_unknown_platform_info(self):
        result = validate_listing("test", "nonexistent_platform")
        assert len(result.issues) == 1
        assert result.issues[0].severity == Severity.INFO


# ── Batch Validation ────────────────────────────────────────

class TestBatchValidation:
    def test_batch_validates_multiple(self):
        listings = [
            {"text": "**Title** Test\n**Bullet Points** x\n**Description** y\n**Search Terms** z", "platform": "amazon"},
            {"text": "**Title** Test\n**Item Specifics** x\n**Description** y", "platform": "ebay"},
        ]
        results = validate_batch(listings)
        assert len(results) == 2
        assert all(isinstance(r, ValidationResult) for r in results)


# ── Platform Rules Coverage ─────────────────────────────────

class TestPlatformRules:
    def test_all_platforms_have_rules(self):
        expected = ["amazon", "shopee", "lazada", "aliexpress", "tiktok", "独立站", "ebay", "walmart"]
        for p in expected:
            assert p in PLATFORM_RULES, f"Missing rules for {p}"

    def test_all_rules_have_required_sections(self):
        for platform, rules in PLATFORM_RULES.items():
            assert "required_sections" in rules, f"{platform} missing required_sections"

    def test_score_clamped(self):
        # Many errors should not go below 0
        listing = "x"
        result = validate_listing(listing, "amazon")
        assert result.score >= 0
        assert result.score <= 100
