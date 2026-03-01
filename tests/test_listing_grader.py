"""Tests for listing_grader module."""
import pytest

from app.listing_grader import (
    GradeDetail,
    ListingGrade,
    grade_bullets,
    grade_conversion_elements,
    grade_description,
    grade_listing,
    grade_mobile_readiness,
    grade_seo_compliance,
    grade_title,
)


GOOD_LISTING = """**Title:** Premium Wireless Bluetooth Earbuds with Active Noise Cancellation - 40H Battery, IPX7 Waterproof

**Bullet Points:**
- ✅ Crystal clear sound quality with advanced drivers for immersive audio experience
- ✅ 40-hour battery life ensures extended playtime with fast USB-C charging support
- ✅ Active noise cancellation blocks up to 35dB of ambient noise effectively
- ✅ IPX7 waterproof rating protects against sweat rain and moisture during workouts
- ✅ Ergonomic memory foam ear tips for all-day comfort in three sizes

**Description:**
Experience premium audio with our **Wireless Bluetooth Earbuds**. Designed for music lovers and athletes.

Our earbuds feature **40-hour battery life** and **fast USB-C charging**. The **active noise cancellation** technology blocks ambient noise.

Built with **IPX7 waterproof** rating. Join thousands of satisfied customers. Buy now with our money-back guarantee.

**Search Terms:** wireless earbuds bluetooth noise cancelling waterproof gym headphones
"""

POOR_LISTING = "earbuds"


class TestGradeTitle:
    def test_good_title(self):
        gd = grade_title(GOOD_LISTING, "amazon")
        assert isinstance(gd, GradeDetail)
        assert gd.criterion == "📝 Title Quality"
        assert gd.weight == 0.20
        assert gd.score >= 40

    def test_poor_title(self):
        gd = grade_title(POOR_LISTING, "amazon")
        assert gd.score < 50

    def test_no_title(self):
        gd = grade_title("", "amazon")
        assert gd.score <= 20

    def test_different_platforms(self):
        for platform in ("amazon", "ebay", "shopify", "walmart"):
            gd = grade_title(GOOD_LISTING, platform)
            assert 0 <= gd.score <= 100

    def test_weighted_score(self):
        gd = grade_title(GOOD_LISTING)
        assert gd.weighted_score == gd.score * gd.weight

    def test_has_notes(self):
        gd = grade_title(GOOD_LISTING)
        assert len(gd.notes) > 0


class TestGradeBullets:
    def test_good_bullets(self):
        gd = grade_bullets(GOOD_LISTING, "amazon")
        assert gd.criterion == "🔹 Bullet Points"
        assert gd.score >= 40

    def test_no_bullets(self):
        gd = grade_bullets("Just plain text no bullets.", "amazon")
        assert gd.score <= 20

    def test_few_bullets(self):
        text = "- Short one\n- Short two"
        gd = grade_bullets(text, "amazon")
        assert gd.score < 80

    def test_many_quality_bullets(self):
        text = "\n".join(
            f"- {chr(65+i)} This is a detailed bullet point with lots of great information about benefits"
            for i in range(6)
        )
        gd = grade_bullets(text, "amazon")
        assert gd.score >= 40


class TestGradeDescription:
    def test_good_description(self):
        gd = grade_description(GOOD_LISTING)
        assert gd.criterion == "📄 Description"
        assert gd.score >= 30

    def test_empty(self):
        gd = grade_description("")
        assert gd.score <= 20

    def test_short_description(self):
        gd = grade_description("**Description:** OK.")
        assert gd.score < 50


class TestGradeConversionElements:
    def test_good_conversion(self):
        gd = grade_conversion_elements(GOOD_LISTING)
        assert gd.criterion == "💰 Conversion Elements"
        assert gd.score >= 20

    def test_no_conversion_elements(self):
        gd = grade_conversion_elements("This is a plain product listing with no conversion triggers at all.")
        assert gd.score < 60

    def test_chinese_conversion(self):
        text = "立即购买，包邮，好评如潮，限时优惠，品质保障"
        gd = grade_conversion_elements(text)
        assert gd.score >= 20


class TestGradeMobileReadiness:
    def test_good_mobile(self):
        gd = grade_mobile_readiness(GOOD_LISTING)
        assert gd.criterion == "📱 Mobile Readiness"
        assert gd.score >= 50

    def test_very_long_lines(self):
        text = "A" * 200 + "\n" + "B" * 200
        gd = grade_mobile_readiness(text)
        assert gd.score < 80

    def test_with_emojis(self):
        text = "🎵 Music\n📱 Phone\n🎧 Audio\n✅ Check"
        gd = grade_mobile_readiness(text)
        assert gd.score >= 60


class TestGradeSeoCompliance:
    def test_good_seo(self):
        gd = grade_seo_compliance(GOOD_LISTING, "amazon")
        assert gd.criterion == "🔍 SEO Compliance"
        assert gd.score >= 40

    def test_no_search_terms(self):
        gd = grade_seo_compliance("Just a product with no keywords section.", "amazon")
        assert gd.score < 80

    def test_shopify_meta(self):
        text = "**Meta Description:** Great product for everyone.\n**Title:** Test"
        gd = grade_seo_compliance(text, "shopify")
        assert isinstance(gd.score, (int, float))


class TestGradeListing:
    def test_good_listing(self):
        result = grade_listing(GOOD_LISTING, "amazon")
        assert isinstance(result, ListingGrade)
        assert 0 <= result.total_score <= 100
        assert result.letter_grade in ("A+", "A", "B+", "B", "C", "D", "F")
        assert result.competitive_readiness in ("not ready", "almost", "ready", "strong")

    def test_poor_listing(self):
        result = grade_listing(POOR_LISTING, "amazon")
        assert result.total_score < 60
        assert result.letter_grade in ("C", "D", "F")

    def test_summary_output(self):
        result = grade_listing(GOOD_LISTING, "amazon")
        summary = result.summary()
        assert "Listing Grade" in summary
        assert result.letter_grade in summary

    def test_strengths_and_weaknesses(self):
        result = grade_listing(GOOD_LISTING, "amazon")
        assert isinstance(result.strengths, list)
        assert isinstance(result.weaknesses, list)
        assert isinstance(result.quick_wins, list)

    def test_criteria_list(self):
        result = grade_listing(GOOD_LISTING, "amazon")
        assert len(result.criteria) == 6
        for c in result.criteria:
            assert isinstance(c, GradeDetail)
            assert 0 <= c.score <= 100

    def test_different_platforms(self):
        for platform in ("amazon", "ebay", "shopify", "walmart"):
            result = grade_listing(GOOD_LISTING, platform)
            assert 0 <= result.total_score <= 100

    def test_empty_listing(self):
        result = grade_listing("", "amazon")
        assert result.total_score < 40
