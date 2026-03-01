"""Tests for quality_score module."""
import pytest

from app.quality_score import (
    DEFAULT_WEIGHTS,
    DimensionScore,
    ImprovementItem,
    PLATFORM_WEIGHTS,
    QualityReport,
    QualityTier,
    compare_scores,
    compute_quality_score,
    score_bullets_quality,
    score_completeness,
    score_compliance,
    score_conversion,
    score_description_quality,
    score_readability,
    score_seo,
    score_title_quality,
)


GOOD_LISTING = """**Title:** Premium Wireless Bluetooth Earbuds with Active Noise Cancellation - 40H Battery, IPX7 Waterproof, Comfortable Fit for Gym and Travel

**Bullet Points:**
- ✅ Crystal Clear Sound — Advanced drivers deliver rich bass and crisp highs for an immersive audio experience that helps you focus
- ✅ 40-Hour Battery Life — Extended playtime ensures you never run out of music; fast charging provides 2 hours from a 10-min charge
- ✅ Active Noise Cancellation — Block out distractions with industry-leading ANC technology; includes transparency mode
- ✅ IPX7 Waterproof — Sweat-proof and rain-resistant design protects against moisture during intense workouts
- ✅ Ergonomic Comfort — 3 sizes of memory foam ear tips ensure a secure, comfortable fit for all-day wear

**Description:**
Experience premium audio with our **Wireless Bluetooth Earbuds**. Designed for music lovers, professionals, and athletes alike.

Our earbuds feature **40-hour battery life** and **fast USB-C charging**, so you're always ready to go. The **active noise cancellation** technology blocks up to 35dB of ambient noise, while the transparency mode lets you stay aware of your surroundings.

Built with an **IPX7 waterproof** rating, these earbuds withstand rain, sweat, and splashes. The ergonomic design with memory foam tips ensures a comfortable, secure fit during workouts, commutes, and long listening sessions.

Join thousands of satisfied customers who rate us 4.8/5 stars. Buy now with our 30-day money-back guarantee and 1-year warranty.

**Search Terms:** wireless earbuds bluetooth noise cancelling waterproof gym earbuds workout headphones long battery life comfortable earbuds
"""

MINIMAL_LISTING = "Earbuds. Good quality."


# ── Title Quality ───────────────────────────────────────────

class TestScoreTitleQuality:
    def test_good_title(self):
        ds = score_title_quality(GOOD_LISTING)
        assert ds.score >= 50
        assert ds.name == "Title"
        assert ds.icon == "📝"

    def test_minimal_title(self):
        ds = score_title_quality(MINIMAL_LISTING)
        assert ds.score < 50

    def test_no_title(self):
        ds = score_title_quality("")
        assert ds.score <= 20

    def test_long_title(self):
        title = "**Title:** " + "Keyword " * 50
        ds = score_title_quality(title)
        assert isinstance(ds.score, (int, float))

    def test_bar_property(self):
        ds = score_title_quality(GOOD_LISTING)
        assert len(ds.bar) == 10
        assert "█" in ds.bar or "░" in ds.bar


# ── Bullets Quality ─────────────────────────────────────────

class TestScoreBulletsQuality:
    def test_good_bullets(self):
        ds = score_bullets_quality(GOOD_LISTING)
        assert ds.score >= 50
        assert ds.name == "Bullets"

    def test_no_bullets(self):
        ds = score_bullets_quality("Just a plain text description with no bullets.")
        assert ds.score <= 20

    def test_few_bullets(self):
        text = "- Short bullet one\n- Short bullet two"
        ds = score_bullets_quality(text)
        assert ds.score < 80

    def test_many_detailed_bullets(self):
        text = "\n".join(
            f"- {chr(65+i)} detailed bullet point with lots of useful product information and benefits for the customer"
            for i in range(7)
        )
        ds = score_bullets_quality(text)
        assert ds.score >= 40


# ── Description Quality ─────────────────────────────────────

class TestScoreDescriptionQuality:
    def test_good_description(self):
        ds = score_description_quality(GOOD_LISTING)
        assert ds.score >= 40
        assert ds.name == "Description"

    def test_empty_description(self):
        ds = score_description_quality("")
        assert ds.score <= 30

    def test_short_description(self):
        ds = score_description_quality("**Description:** Short text.")
        assert ds.score < 60


# ── SEO ─────────────────────────────────────────────────────

class TestScoreSeo:
    def test_good_seo(self):
        ds = score_seo(GOOD_LISTING)
        assert ds.score >= 50
        assert ds.name == "SEO"

    def test_no_keywords_section(self):
        ds = score_seo("Just a product without any keyword section.")
        assert ds.score < 80

    def test_keyword_stuffing(self):
        text = ("earbuds " * 100) + "\n**Search Terms:** earbuds"
        ds = score_seo(text)
        # Should detect stuffing
        assert isinstance(ds.score, (int, float))


# ── Conversion ──────────────────────────────────────────────

class TestScoreConversion:
    def test_good_conversion(self):
        ds = score_conversion(GOOD_LISTING)
        assert ds.score >= 40
        assert ds.name == "Conversion"

    def test_no_cta(self):
        ds = score_conversion("Nice product with good features.")
        assert ds.score < 80

    def test_with_trust_signals(self):
        text = "Buy now with our money-back guarantee and free shipping! 4.8 stars from 1000 reviews."
        ds = score_conversion(text)
        assert ds.score >= 40

    def test_chinese_conversion(self):
        text = "立即购买，包邮，好评如潮，限时优惠，品质保障"
        ds = score_conversion(text)
        assert ds.score >= 30


# ── Readability ─────────────────────────────────────────────

class TestScoreReadability:
    def test_good_readability(self):
        ds = score_readability(GOOD_LISTING)
        assert ds.score >= 40
        assert ds.name == "Readability"

    def test_empty_text(self):
        ds = score_readability("")
        assert ds.score <= 40

    def test_wall_of_text(self):
        text = "Word " * 500  # No formatting, no breaks
        ds = score_readability(text)
        assert ds.score < 80

    def test_well_formatted(self):
        text = "**Header**\n\nShort sentence here.\n\n- Bullet one\n- Bullet two\n\n🎵 Emoji section."
        ds = score_readability(text)
        assert ds.score >= 40


# ── Compliance ──────────────────────────────────────────────

class TestScoreCompliance:
    def test_clean_listing(self):
        ds = score_compliance(GOOD_LISTING)
        assert ds.score >= 50
        assert ds.name == "Compliance"

    def test_health_claims(self):
        text = "This product can cure headaches and prevent cancer. FDA approved treatment."
        ds = score_compliance(text)
        assert ds.score < 70

    def test_contact_info(self):
        text = "Call us at 555-123-4567 or email support@example.com"
        ds = score_compliance(text)
        assert ds.score < 70

    def test_external_urls(self):
        text = "Visit our website at https://mystore.com for more info"
        ds = score_compliance(text)
        assert ds.score < 70

    def test_all_caps_abuse(self):
        text = "THIS PRODUCT IS THE BEST EVER MADE GUARANTEED BEST QUALITY AMAZING"
        ds = score_compliance(text)
        assert ds.score < 70


# ── Completeness ────────────────────────────────────────────

class TestScoreCompleteness:
    def test_complete_listing(self):
        ds = score_completeness(GOOD_LISTING)
        assert ds.score >= 60
        assert ds.name == "Completeness"

    def test_empty_listing(self):
        ds = score_completeness("")
        assert ds.score == 0

    def test_partial_listing(self):
        text = "**Title:** My Product\n\n**Description:** Good stuff."
        ds = score_completeness(text)
        assert 0 < ds.score < 100


# ── DimensionScore ──────────────────────────────────────────

class TestDimensionScore:
    def test_weighted_property(self):
        ds = DimensionScore(name="Test", score=80, weight=0.5, icon="📊")
        assert ds.weighted == 40.0

    def test_bar_full(self):
        ds = DimensionScore(name="Test", score=100, weight=0.5, icon="📊")
        assert ds.bar == "██████████"

    def test_bar_empty(self):
        ds = DimensionScore(name="Test", score=0, weight=0.5, icon="📊")
        assert ds.bar == "░░░░░░░░░░"

    def test_bar_half(self):
        ds = DimensionScore(name="Test", score=50, weight=0.5, icon="📊")
        assert "█" in ds.bar
        assert "░" in ds.bar


# ── ImprovementItem ─────────────────────────────────────────

class TestImprovementItem:
    def test_roi_low_effort(self):
        item = ImprovementItem("Title", "Fix title", 10, "low", 1)
        assert item.roi == 30.0

    def test_roi_high_effort(self):
        item = ImprovementItem("Title", "Major rewrite", 10, "high", 1)
        assert item.roi == 5.0

    def test_roi_medium_effort(self):
        item = ImprovementItem("Title", "Tweak", 10, "medium", 1)
        assert item.roi == 15.0


# ── Composite Quality Score ─────────────────────────────────

class TestComputeQualityScore:
    def test_good_listing(self):
        report = compute_quality_score(GOOD_LISTING, platform="amazon", listing_id="B001")
        assert isinstance(report, QualityReport)
        assert 0 <= report.total_score <= 100
        assert report.tier in QualityTier
        assert report.platform == "amazon"
        assert report.listing_id == "B001"
        assert len(report.dimensions) == 8

    def test_minimal_listing(self):
        report = compute_quality_score(MINIMAL_LISTING)
        assert report.total_score < 50
        assert report.tier in (QualityTier.IRON, QualityTier.BRONZE)

    def test_tiers(self):
        # Good listing should be at least silver
        report = compute_quality_score(GOOD_LISTING)
        assert report.tier in (QualityTier.PLATINUM, QualityTier.GOLD,
                               QualityTier.SILVER)

    def test_improvements_generated(self):
        report = compute_quality_score(MINIMAL_LISTING)
        assert len(report.improvements) > 0

    def test_improvements_sorted_by_roi(self):
        report = compute_quality_score(MINIMAL_LISTING)
        if len(report.improvements) >= 2:
            for i in range(len(report.improvements) - 1):
                assert report.improvements[i].roi >= report.improvements[i + 1].roi

    def test_benchmark_included(self):
        report = compute_quality_score(GOOD_LISTING, platform="amazon")
        assert report.benchmark is not None
        assert "avg" in report.benchmark

    def test_different_platforms(self):
        for platform in ("amazon", "ebay", "shopify", "walmart", "etsy"):
            report = compute_quality_score(GOOD_LISTING, platform=platform)
            assert report.platform == platform
            assert 0 <= report.total_score <= 100

    def test_weights_sum_to_1(self):
        for platform, weights in PLATFORM_WEIGHTS.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.01, f"{platform} weights sum to {total}"

    def test_default_weights_sum_to_1(self):
        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01

    def test_unknown_platform_uses_defaults(self):
        report = compute_quality_score(GOOD_LISTING, platform="unknown_store")
        assert report is not None
        assert 0 <= report.total_score <= 100

    def test_card_output(self):
        report = compute_quality_score(GOOD_LISTING, platform="amazon", listing_id="B001")
        card = report.card()
        assert "QUALITY SCORE" in card
        assert "B001" in card
        assert isinstance(card, str)

    def test_card_contains_dimensions(self):
        report = compute_quality_score(GOOD_LISTING)
        card = report.card()
        assert "Title" in card
        assert "SEO" in card

    def test_card_contains_benchmark(self):
        report = compute_quality_score(GOOD_LISTING, platform="amazon")
        card = report.card()
        assert "Benchmark" in card

    def test_empty_listing(self):
        report = compute_quality_score("")
        assert report.total_score <= 30
        assert report.tier in (QualityTier.IRON, QualityTier.BRONZE)


# ── Compare Scores ──────────────────────────────────────────

class TestCompareScores:
    def test_empty_reports(self):
        result = compare_scores([])
        assert "No reports" in result

    def test_single_report(self):
        report = compute_quality_score(GOOD_LISTING, platform="amazon", listing_id="B001")
        result = compare_scores([report])
        assert "B001" in result

    def test_multiple_reports(self):
        r1 = compute_quality_score(GOOD_LISTING, platform="amazon", listing_id="B001")
        r2 = compute_quality_score(MINIMAL_LISTING, platform="ebay", listing_id="B002")
        result = compare_scores([r1, r2])
        assert "B001" in result
        assert "B002" in result
        assert "Dimension Breakdown" in result

    def test_sorted_by_score(self):
        r1 = compute_quality_score(MINIMAL_LISTING, listing_id="LOW")
        r2 = compute_quality_score(GOOD_LISTING, listing_id="HIGH")
        result = compare_scores([r1, r2])
        # HIGH should appear before LOW in output
        high_pos = result.index("HIGH")
        low_pos = result.index("LOW")
        assert high_pos < low_pos
