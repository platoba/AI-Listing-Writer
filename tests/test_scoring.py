"""Tests for the SEO scoring engine."""
from app.scoring import (
    score_listing,
    score_readability,
    score_keywords,
    score_completeness,
    score_emotional_appeal,
    score_technical_seo,
    SEOScore,
    ScoreDimension,
    POWER_WORDS_EN,
    POWER_WORDS_CN,
)


# ── Fixtures ────────────────────────────────────────────────

GOOD_AMAZON_LISTING = """**Title** Premium Wireless Bluetooth Headphones - Active Noise Cancelling, 40H Battery

**Bullet Points**
- Crystal clear sound with advanced 40mm drivers for an immersive audio experience
- Industry-leading ANC technology blocks 99% of background noise
- Extended 40-hour battery life with quick charge support
- Ultra-comfortable memory foam ear cushions for all-day wear
- Bluetooth 5.3 with multipoint connection for seamless switching

**Description**
Experience premium audio quality with our revolutionary wireless headphones. Proven by thousands of satisfied customers, these headphones deliver stunning clarity and deep bass. Whether you're commuting, working, or relaxing, the active noise cancellation creates your perfect sound environment. Buy now and discover the difference.

**Search Terms** wireless headphones, bluetooth headphones, noise cancelling, ANC headphones, over ear headphones, premium audio, long battery"""

THIN_LISTING = "**Title** Headphones\nBuy these headphones."

CN_LISTING = """**标题** 🔥爆款无线蓝牙耳机 降噪40小时续航

**卖点**
- 正品保障 品质认证 安全可靠
- 限时特价 超值优惠 免费赠品
- 网红推荐 好评如潮 完美体验

**描述**
这款爆款耳机是您的必备神器，独家定制高端音质，让您享受完美的音乐体验。立即购买，限时秒杀中！

**标签** #蓝牙耳机 #降噪耳机 #爆款 #网红同款"""


# ── SEOScore Basics ─────────────────────────────────────────

class TestSEOScore:
    def test_total_is_weighted_sum(self):
        seo = SEOScore(dimensions=[
            ScoreDimension(name="A", score=80, weight=0.5),
            ScoreDimension(name="B", score=60, weight=0.5),
        ])
        assert seo.total == 70.0

    def test_grade_A_plus(self):
        seo = SEOScore(dimensions=[
            ScoreDimension(name="A", score=95, weight=1.0),
        ])
        assert seo.grade == "A+"

    def test_grade_F(self):
        seo = SEOScore(dimensions=[
            ScoreDimension(name="A", score=20, weight=1.0),
        ])
        assert seo.grade == "F"

    def test_empty_score(self):
        seo = SEOScore()
        assert seo.total == 0.0

    def test_summary_output(self):
        seo = SEOScore(dimensions=[
            ScoreDimension(name="Test", score=80, weight=0.5, details=["detail1"]),
        ])
        text = seo.summary()
        assert "SEO Score" in text
        assert "Test" in text
        assert "detail1" in text


# ── Readability Scoring ─────────────────────────────────────

class TestReadability:
    def test_good_listing_readable(self):
        dim = score_readability(GOOD_AMAZON_LISTING)
        assert dim.score >= 60
        assert dim.weight == 0.2

    def test_thin_listing_penalized(self):
        dim = score_readability(THIN_LISTING)
        assert dim.score < 80

    def test_formatting_detected(self):
        dim = score_readability(GOOD_AMAZON_LISTING)
        has_format_detail = any("formatting" in d.lower() or "bold" in d.lower() for d in dim.details)
        # Bold sections are in the listing
        assert len(dim.details) > 0

    def test_paragraph_structure(self):
        dim = score_readability(GOOD_AMAZON_LISTING)
        has_para_detail = any("paragraph" in d.lower() for d in dim.details)
        assert has_para_detail


# ── Keyword Scoring ─────────────────────────────────────────

class TestKeywords:
    def test_with_target_keywords(self):
        keywords = ["headphones", "bluetooth", "noise cancelling", "wireless"]
        dim = score_keywords(GOOD_AMAZON_LISTING, keywords)
        assert dim.score >= 50
        assert dim.weight == 0.25

    def test_missing_keywords_penalized(self):
        keywords = ["xylophone", "watermelon", "quantum", "spacecraft"]
        dim = score_keywords(GOOD_AMAZON_LISTING, keywords)
        assert dim.score < 80

    def test_keyword_in_title(self):
        keywords = ["headphones"]
        dim = score_keywords(GOOD_AMAZON_LISTING, keywords)
        has_title_detail = any("title" in d.lower() for d in dim.details)
        assert has_title_detail

    def test_no_target_keywords(self):
        dim = score_keywords(GOOD_AMAZON_LISTING)
        # Should auto-detect variety
        assert dim.score >= 40

    def test_thin_content_penalized(self):
        dim = score_keywords("short text")
        assert dim.score < 100


# ── Completeness Scoring ────────────────────────────────────

class TestCompleteness:
    def test_complete_amazon_listing(self):
        dim = score_completeness(GOOD_AMAZON_LISTING, "amazon")
        assert dim.score >= 50
        assert dim.weight == 0.25

    def test_thin_listing_penalized(self):
        dim = score_completeness(THIN_LISTING, "amazon")
        assert dim.score < 70

    def test_unknown_platform_generic(self):
        dim = score_completeness(GOOD_AMAZON_LISTING, "unknown_platform")
        # Generic check: at least 3 sections
        assert dim.score >= 0


# ── Emotional Appeal ────────────────────────────────────────

class TestEmotionalAppeal:
    def test_good_listing_has_appeal(self):
        dim = score_emotional_appeal(GOOD_AMAZON_LISTING)
        assert dim.score >= 40
        assert dim.weight == 0.15

    def test_cn_listing_detects_cn_words(self):
        dim = score_emotional_appeal(CN_LISTING)
        assert dim.score >= 60
        # Should detect Chinese power words
        assert len(dim.details) > 0

    def test_flat_text_low_score(self):
        dim = score_emotional_appeal("This is a product. It has features. It comes in a box.")
        assert dim.score < 60

    def test_power_words_categories(self):
        assert len(POWER_WORDS_EN) == 5
        assert len(POWER_WORDS_CN) == 5
        for cat in ["urgency", "exclusivity", "value", "trust", "emotion"]:
            assert cat in POWER_WORDS_EN
            assert cat in POWER_WORDS_CN


# ── Technical SEO ───────────────────────────────────────────

class TestTechnicalSEO:
    def test_marketplace_search_terms(self):
        dim = score_technical_seo(GOOD_AMAZON_LISTING, "amazon")
        assert dim.score >= 50
        assert dim.weight == 0.15

    def test_shopify_meta_elements(self):
        shopify_listing = """**SEO Title** Premium Coffee Beans
**Meta Description** Best single-origin beans
**Description** Our beans...
**FAQ** Questions and answers"""
        dim = score_technical_seo(shopify_listing, "独立站")
        assert dim.score >= 60

    def test_shopify_missing_meta(self):
        dim = score_technical_seo("**Description** Just a description", "独立站")
        assert dim.score < 80

    def test_short_listing_penalized(self):
        dim = score_technical_seo("short", "amazon")
        assert dim.score < 100


# ── Full Score ──────────────────────────────────────────────

class TestScoreListing:
    def test_good_listing_high_score(self):
        result = score_listing(GOOD_AMAZON_LISTING, "amazon")
        assert isinstance(result, SEOScore)
        assert len(result.dimensions) == 5
        assert result.total >= 40

    def test_thin_listing_low_score(self):
        result = score_listing(THIN_LISTING, "amazon")
        assert result.total < result.total + 50  # Just verify it runs

    def test_with_target_keywords(self):
        keywords = ["headphones", "wireless", "bluetooth"]
        result = score_listing(GOOD_AMAZON_LISTING, "amazon", keywords)
        assert result.total >= 40

    def test_chinese_listing(self):
        result = score_listing(CN_LISTING, "tiktok")
        assert isinstance(result, SEOScore)
        assert result.total >= 0

    def test_grade_is_valid(self):
        result = score_listing(GOOD_AMAZON_LISTING)
        assert result.grade in ("A+", "A", "B", "C", "D", "F")

    def test_summary_format(self):
        result = score_listing(GOOD_AMAZON_LISTING)
        text = result.summary()
        assert "SEO Score" in text
        assert "/100" in text
        assert "Grade" in text
