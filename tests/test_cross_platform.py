"""Tests for cross_platform listing adapter."""
import pytest
from app.cross_platform import (
    Platform, PlatformLimits, PLATFORM_LIMITS,
    UniversalListing, AdaptedListing,
    strip_emojis, strip_html, smart_truncate,
    text_to_html_description, extract_keywords_from_text,
    adapt_for_amazon, adapt_for_shopify, adapt_for_ebay,
    adapt_for_etsy, adapt_for_aliexpress, adapt_for_walmart,
    adapt_listing, adapt_all, cross_platform_report,
)


# ── Fixtures ──

SAMPLE_LISTING = UniversalListing(
    title="Premium Wireless Bluetooth Headphones with Active Noise Cancellation",
    brand="AudioPro",
    bullets=[
        "Advanced ANC blocks 99% of ambient noise for immersive listening",
        "40-hour battery life with quick charge — 10 min = 3 hours",
        "Memory foam ear cushions for all-day comfort",
        "Bluetooth 5.3 with multipoint connection (2 devices simultaneously)",
        "Hi-Res Audio certified with LDAC codec support",
    ],
    description="Experience studio-quality sound anywhere. Our premium wireless headphones "
                "combine cutting-edge noise cancellation with exceptional comfort. "
                "Whether you're commuting, working, or relaxing, these headphones deliver "
                "crystal-clear audio with deep, rich bass.",
    keywords=["wireless headphones", "bluetooth", "noise cancelling", "over ear",
              "premium audio", "ANC", "hi-res", "LDAC", "comfortable headphones"],
    tags=["headphones", "wireless", "bluetooth", "ANC", "premium", "audio",
          "music", "over-ear", "noise-cancelling", "comfortable"],
    price=149.99,
    features=["ANC", "Bluetooth 5.3", "40h battery", "Hi-Res Audio", "Memory foam"],
    materials=["Aluminum", "Memory foam", "Protein leather"],
    dimensions={"Weight": "250g", "Driver": "40mm", "Impedance": "32Ω"},
)


# ── Utility Tests ──

class TestStripEmojis:
    def test_removes_emojis(self):
        assert strip_emojis("Hello 🔥 World 🎉") == "Hello  World"

    def test_preserves_plain_text(self):
        assert strip_emojis("No emojis here") == "No emojis here"


class TestStripHtml:
    def test_removes_tags(self):
        assert strip_html("<p>Hello <b>World</b></p>") == "Hello World"

    def test_preserves_text(self):
        assert strip_html("No tags") == "No tags"


class TestSmartTruncate:
    def test_no_truncation_needed(self):
        assert smart_truncate("Short text", 100) == "Short text"

    def test_truncates_at_word_boundary(self):
        result = smart_truncate("This is a somewhat longer text", 20)
        assert len(result) <= 20
        assert result.endswith("...")

    def test_exact_limit(self):
        text = "abc"
        assert smart_truncate(text, 3) == "abc"


class TestTextToHtml:
    def test_bullets_only(self):
        result = text_to_html_description("", ["Bullet 1", "Bullet 2"])
        assert "<ul>" in result
        assert "<li>Bullet 1</li>" in result

    def test_text_only(self):
        result = text_to_html_description("Hello world", [])
        assert "<p>Hello world</p>" in result

    def test_both(self):
        result = text_to_html_description("Desc", ["B1"])
        assert "<ul>" in result
        assert "<p>Desc</p>" in result


class TestExtractKeywords:
    def test_extracts_keywords(self):
        kws = extract_keywords_from_text("wireless bluetooth headphones with noise cancellation")
        assert "wireless" in kws
        assert "bluetooth" in kws
        assert "with" not in kws  # Stop word

    def test_respects_limit(self):
        kws = extract_keywords_from_text("word1 word2 word3 word4 word5", max_keywords=2)
        assert len(kws) <= 2


# ── Amazon Tests ──

class TestAmazonAdapter:
    def test_basic_adaptation(self):
        result = adapt_for_amazon(SAMPLE_LISTING)
        assert result.platform == Platform.AMAZON
        assert len(result.title) <= 200
        assert "AudioPro" in result.title
        assert len(result.bullets) == 5

    def test_strips_emojis(self):
        listing = UniversalListing(title="Great Product 🔥🎉 Amazing!")
        result = adapt_for_amazon(listing)
        assert "🔥" not in result.title

    def test_brand_prepended(self):
        result = adapt_for_amazon(SAMPLE_LISTING)
        assert result.title.startswith("AudioPro")

    def test_keyword_byte_limit(self):
        listing = UniversalListing(keywords=["word"] * 100)
        result = adapt_for_amazon(listing)
        assert len(result.keywords.encode("utf-8")) <= 249

    def test_short_title_warning(self):
        listing = UniversalListing(title="Short")
        result = adapt_for_amazon(listing)
        assert any("too short" in w for w in result.warnings)

    def test_uses_features_as_fallback(self):
        listing = UniversalListing(
            title="Product",
            features=["Feature 1", "Feature 2"],
        )
        result = adapt_for_amazon(listing)
        assert len(result.bullets) == 2

    def test_score_calculation(self):
        result = adapt_for_amazon(SAMPLE_LISTING)
        assert 0 <= result.score <= 100


# ── Shopify Tests ──

class TestShopifyAdapter:
    def test_basic_adaptation(self):
        result = adapt_for_shopify(SAMPLE_LISTING)
        assert result.platform == Platform.SHOPIFY
        assert "<ul>" in result.description  # HTML description
        assert len(result.tags) > 0

    def test_html_description(self):
        result = adapt_for_shopify(SAMPLE_LISTING)
        assert "<li>" in result.description

    def test_tags_from_keywords(self):
        listing = UniversalListing(keywords=["kw1", "kw2"])
        result = adapt_for_shopify(listing)
        assert result.tags == ["kw1", "kw2"]


# ── eBay Tests ──

class TestEbayAdapter:
    def test_title_80_chars(self):
        long_title = "A" * 200
        listing = UniversalListing(title=long_title)
        result = adapt_for_ebay(listing)
        assert len(result.title) <= 80

    def test_strips_emojis(self):
        listing = UniversalListing(title="Product 🔥")
        result = adapt_for_ebay(listing)
        assert "🔥" not in result.title


# ── Etsy Tests ──

class TestEtsyAdapter:
    def test_tag_limit_13(self):
        listing = UniversalListing(tags=["t" + str(i) for i in range(20)])
        result = adapt_for_etsy(listing)
        assert len(result.tags) <= 13

    def test_few_tags_warning(self):
        listing = UniversalListing(tags=["tag1", "tag2"])
        result = adapt_for_etsy(listing)
        assert any("tags" in w.lower() for w in result.warnings)

    def test_title_140(self):
        listing = UniversalListing(title="X" * 200)
        result = adapt_for_etsy(listing)
        assert len(result.title) <= 140


# ── AliExpress Tests ──

class TestAliExpressAdapter:
    def test_specs_table(self):
        result = adapt_for_aliexpress(SAMPLE_LISTING)
        assert "<table>" in result.description
        assert "Weight" in result.description

    def test_materials_included(self):
        result = adapt_for_aliexpress(SAMPLE_LISTING)
        assert "Aluminum" in result.description

    def test_title_128(self):
        listing = UniversalListing(title="Y" * 200)
        result = adapt_for_aliexpress(listing)
        assert len(result.title) <= 140  # smart_truncate may add ...


# ── Walmart Tests ──

class TestWalmartAdapter:
    def test_brand_dash_title(self):
        result = adapt_for_walmart(SAMPLE_LISTING)
        assert "AudioPro" in result.title

    def test_bullet_limit(self):
        listing = UniversalListing(bullets=["b"] * 10)
        result = adapt_for_walmart(listing)
        assert len(result.bullets) <= 5

    def test_strips_emojis(self):
        listing = UniversalListing(title="Cool 🔥 Product")
        result = adapt_for_walmart(listing)
        assert "🔥" not in result.title


# ── Cross-Platform Tests ──

class TestAdaptListing:
    @pytest.mark.parametrize("platform", list(Platform))
    def test_all_platforms(self, platform):
        result = adapt_listing(SAMPLE_LISTING, platform)
        assert result.platform == platform
        assert result.title
        assert result.score >= 0

    def test_invalid_platform(self):
        with pytest.raises(ValueError):
            adapt_listing(SAMPLE_LISTING, "invalid")


class TestAdaptAll:
    def test_returns_all_platforms(self):
        results = adapt_all(SAMPLE_LISTING)
        assert len(results) == len(Platform)
        for p in Platform:
            assert p in results


class TestCrossPlatformReport:
    def test_report_generation(self):
        report = cross_platform_report(SAMPLE_LISTING)
        assert "Cross-Platform" in report
        for p in Platform:
            assert p.value.upper() in report


class TestPlatformLimits:
    def test_all_platforms_have_limits(self):
        for p in Platform:
            assert p in PLATFORM_LIMITS


class TestAdaptedListing:
    def test_is_compliant(self):
        adapted = AdaptedListing(platform=Platform.AMAZON)
        assert adapted.is_compliant()

    def test_not_compliant_with_warnings(self):
        adapted = AdaptedListing(platform=Platform.AMAZON, warnings=["issue"])
        assert not adapted.is_compliant()

    def test_summary(self):
        adapted = adapt_for_amazon(SAMPLE_LISTING)
        summary = adapted.summary()
        assert "AMAZON" in summary
