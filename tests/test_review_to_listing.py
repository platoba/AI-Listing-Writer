"""Tests for review_to_listing module."""
import pytest

from app.review_to_listing import (
    ExtractedBenefit,
    PainPoint,
    ReviewAnalysisResult,
    ReviewQuality,
    Sentiment,
    analyze_reviews,
    assess_review_quality,
    categorize_feature,
    classify_sentiment,
    cluster_benefits,
    cluster_pain_points,
    extract_benefit_phrases,
    extract_pain_points_from_text,
    extract_voc_keywords,
    generate_bullets_from_reviews,
    generate_description_from_reviews,
    score_sentiment,
)


# ── Sentiment Scoring ────────────────────────────────────────

class TestScoreSentiment:
    def test_positive_review(self):
        text = "I love this product, it's amazing and excellent quality"
        score = score_sentiment(text)
        assert score > 0.3

    def test_negative_review(self):
        text = "Terrible product, worst purchase, broke after one day"
        score = score_sentiment(text)
        assert score < -0.3

    def test_neutral_review(self):
        text = "The product arrived on time and looks as described"
        score = score_sentiment(text)
        assert -0.5 <= score <= 0.5

    def test_mixed_review(self):
        text = "Great quality but terrible shipping, very disappointed but love the design"
        score = score_sentiment(text)
        assert -1.0 <= score <= 1.0

    def test_empty_text(self):
        assert score_sentiment("") == 0.0

    def test_chinese_positive(self):
        text = "非常满意，质量很好，推荐购买"
        score = score_sentiment(text)
        assert score > 0

    def test_chinese_negative(self):
        text = "垃圾产品，退货了，太失望"
        score = score_sentiment(text)
        assert score < 0


class TestClassifySentiment:
    def test_positive(self):
        assert classify_sentiment(0.5) == Sentiment.POSITIVE

    def test_negative(self):
        assert classify_sentiment(-0.5) == Sentiment.NEGATIVE

    def test_neutral(self):
        assert classify_sentiment(0.05) == Sentiment.NEUTRAL

    def test_mixed(self):
        assert classify_sentiment(0.2) == Sentiment.MIXED

    def test_boundary_positive(self):
        assert classify_sentiment(0.31) == Sentiment.POSITIVE

    def test_boundary_negative(self):
        assert classify_sentiment(-0.31) == Sentiment.NEGATIVE


# ── Review Quality ───────────────────────────────────────────

class TestAssessReviewQuality:
    def test_high_quality(self):
        text = " ".join(["word"] * 60)
        assert assess_review_quality(text) == ReviewQuality.HIGH

    def test_medium_quality(self):
        text = " ".join(["word"] * 30)
        assert assess_review_quality(text) == ReviewQuality.MEDIUM

    def test_low_quality(self):
        assert assess_review_quality("good") == ReviewQuality.LOW

    def test_empty(self):
        assert assess_review_quality("") == ReviewQuality.LOW


# ── Feature Categorization ──────────────────────────────────

class TestCategorizeFeature:
    def test_quality(self):
        assert categorize_feature("excellent build quality") == "quality"

    def test_comfort(self):
        assert categorize_feature("very comfortable and soft") == "comfort"

    def test_value(self):
        assert categorize_feature("great price and value") == "value"

    def test_appearance(self):
        assert categorize_feature("beautiful design and color") == "appearance"

    def test_functionality(self):
        assert categorize_feature("easy to use and convenient") == "functionality"

    def test_shipping(self):
        assert categorize_feature("fast shipping and good packaging") == "shipping"

    def test_battery(self):
        assert categorize_feature("battery lasts 10 hours charging fast") == "battery"

    def test_unknown(self):
        assert categorize_feature("xyzzy foo bar") == "general"


# ── Benefit Extraction ──────────────────────────────────────

class TestExtractBenefitPhrases:
    def test_love_pattern(self):
        phrases = extract_benefit_phrases("I love the sound quality of these earbuds.")
        assert len(phrases) > 0

    def test_great_pattern(self):
        phrases = extract_benefit_phrases("The battery life is great and lasts all day.")
        assert len(phrases) > 0

    def test_no_benefits(self):
        phrases = extract_benefit_phrases("It arrived.")
        assert isinstance(phrases, list)

    def test_chinese_benefits(self):
        phrases = extract_benefit_phrases("非常好用，特别方便携带")
        assert len(phrases) > 0

    def test_multiple_benefits(self):
        text = "I love the design. The quality is amazing. Really comfortable to wear."
        phrases = extract_benefit_phrases(text)
        assert len(phrases) >= 2


# ── Pain Point Extraction ───────────────────────────────────

class TestExtractPainPoints:
    def test_bad_quality(self):
        points = extract_pain_points_from_text("The battery life is terrible and dies fast")
        assert len(points) > 0

    def test_wish_pattern(self):
        points = extract_pain_points_from_text("I wish it had better battery life")
        assert len(points) > 0

    def test_problem_pattern(self):
        points = extract_pain_points_from_text("Problem: the zipper breaks easily")
        assert len(points) > 0

    def test_no_pain_points(self):
        points = extract_pain_points_from_text("It's fine.")
        assert isinstance(points, list)

    def test_chinese_pain_points(self):
        points = extract_pain_points_from_text("质量太差了，不好用")
        assert len(points) > 0


# ── VOC Keywords ────────────────────────────────────────────

class TestExtractVocKeywords:
    def test_basic(self):
        reviews = [
            "Great battery life and sound quality",
            "The battery life is amazing, sound is clear",
            "Battery lasts all day, quality sound output",
        ]
        keywords = extract_voc_keywords(reviews, top_n=5)
        assert len(keywords) > 0
        # Battery and sound should be top keywords
        top_words = [kw for kw, _ in keywords]
        assert any("battery" in w for w in top_words)

    def test_empty_reviews(self):
        assert extract_voc_keywords([], top_n=5) == []

    def test_single_review(self):
        keywords = extract_voc_keywords(["Great product quality"], top_n=3)
        assert len(keywords) > 0

    def test_top_n_limit(self):
        reviews = ["word " * 50] * 5
        keywords = extract_voc_keywords(reviews, top_n=3)
        assert len(keywords) <= 3


# ── Clustering ──────────────────────────────────────────────

class TestClusterBenefits:
    def test_basic_clustering(self):
        reviews = [
            "I love the sound quality, it's amazing",
            "The sound quality is great, really love it",
            "Amazing sound quality and battery life",
        ]
        benefits = cluster_benefits(reviews, min_frequency=2)
        assert isinstance(benefits, list)

    def test_empty_reviews(self):
        assert cluster_benefits([], min_frequency=1) == []

    def test_min_frequency_filter(self):
        reviews = [
            "I love the design",
            "Great design and quality",
            "Unique one-time mention feature",
        ]
        benefits = cluster_benefits(reviews, min_frequency=2)
        # Only items mentioned 2+ times should appear
        for b in benefits:
            assert b.frequency >= 2


class TestClusterPainPoints:
    def test_basic(self):
        reviews = [
            "The build quality is terrible, broke after a week",
            "Terrible quality, it broke so easily",
            "Broke within days, awful product",
        ]
        points = cluster_pain_points(reviews, min_frequency=1)
        assert isinstance(points, list)

    def test_skips_positive_reviews(self):
        reviews = [
            "I love everything about this amazing wonderful product",
            "Perfect, excellent, great quality, love it",
        ]
        points = cluster_pain_points(reviews, min_frequency=1)
        # Should skip these since they're positive
        assert isinstance(points, list)


# ── Bullet Generation ───────────────────────────────────────

class TestGenerateBullets:
    def test_basic_generation(self):
        benefits = [
            ExtractedBenefit("great sound quality", 10, Sentiment.POSITIVE, 0.8, category="quality"),
            ExtractedBenefit("comfortable fit", 8, Sentiment.POSITIVE, 0.7, category="comfort"),
            ExtractedBenefit("long battery life", 6, Sentiment.POSITIVE, 0.6, category="battery"),
        ]
        pain_points = [
            PainPoint("charging cable too short", 5, 0.5),
        ]
        bullets = generate_bullets_from_reviews(benefits, pain_points, max_bullets=5)
        assert len(bullets) <= 5
        assert len(bullets) > 0
        assert any("✅" in b for b in bullets)

    def test_empty_input(self):
        bullets = generate_bullets_from_reviews([], [], max_bullets=5)
        assert bullets == []

    def test_respects_max(self):
        benefits = [
            ExtractedBenefit(f"benefit {i}", 5, Sentiment.POSITIVE, 0.5, category=f"cat{i}")
            for i in range(10)
        ]
        bullets = generate_bullets_from_reviews(benefits, [], max_bullets=3)
        assert len(bullets) <= 3

    def test_includes_pain_point_bullets(self):
        benefits = [
            ExtractedBenefit("good quality", 5, Sentiment.POSITIVE, 0.5, category="quality"),
        ]
        pain_points = [
            PainPoint("short battery", 3, 0.5),
        ]
        bullets = generate_bullets_from_reviews(benefits, pain_points, max_bullets=5)
        has_pain_bullet = any("🔧" in b or "concern" in b.lower() for b in bullets)
        assert has_pain_bullet


# ── Description Generation ──────────────────────────────────

class TestGenerateDescription:
    def test_basic(self):
        benefits = [
            ExtractedBenefit("sound quality", 10, Sentiment.POSITIVE, 0.8),
        ]
        pain_points = [PainPoint("short cable", 5, 0.5)]
        voc = [("sound", 20), ("quality", 15), ("battery", 10)]

        desc = generate_description_from_reviews(benefits, pain_points, voc, "TestEarbuds")
        assert len(desc) > 0
        assert "TestEarbuds" in desc

    def test_empty_input(self):
        desc = generate_description_from_reviews([], [], [], "Product")
        assert "Product" in desc

    def test_contains_voc(self):
        voc = [("durability", 10), ("comfort", 8)]
        desc = generate_description_from_reviews([], [], voc, "Product")
        assert "durability" in desc.lower() or "comfort" in desc.lower()


# ── Full Pipeline ───────────────────────────────────────────

class TestAnalyzeReviews:
    def test_basic_analysis(self):
        reviews = [
            "I absolutely love these wireless earbuds! The sound quality is amazing and the battery lasts all day long.",
            "Great sound quality and comfortable fit. Love the battery life too.",
            "The sound quality is excellent but the charging cable is too short.",
            "Terrible build quality, broke after one week. Very disappointed.",
            "Amazing product, great sound quality. Would recommend to anyone.",
        ]
        result = analyze_reviews(reviews, product_name="TestBuds", platform="amazon")

        assert isinstance(result, ReviewAnalysisResult)
        assert result.total_reviews == 5
        assert -1.0 <= result.avg_sentiment_score <= 1.0
        assert result.overall_sentiment in Sentiment
        assert isinstance(result.generated_bullets, list)
        assert isinstance(result.generated_description, str)
        assert isinstance(result.quality_distribution, dict)

    def test_empty_reviews(self):
        result = analyze_reviews([])
        assert result.total_reviews == 0
        assert result.overall_sentiment == Sentiment.NEUTRAL
        assert result.generated_bullets == []

    def test_all_positive(self):
        reviews = [
            "Love it! Amazing product, excellent quality!",
            "Perfect! Great design, wonderful experience!",
            "Best purchase ever, fantastic and brilliant!",
        ]
        result = analyze_reviews(reviews)
        assert result.avg_sentiment_score > 0

    def test_all_negative(self):
        reviews = [
            "Terrible, worst product ever, complete waste",
            "Awful quality, broke immediately, very disappointed",
            "Horrible, defective, returned it right away",
        ]
        result = analyze_reviews(reviews)
        assert result.avg_sentiment_score < 0

    def test_summary_method(self):
        reviews = ["Great product, love the quality"] * 5
        result = analyze_reviews(reviews, product_name="TestProduct")
        summary = result.summary()
        assert "Review Analysis" in summary
        assert isinstance(summary, str)

    def test_quality_distribution(self):
        reviews = [
            "Good",  # low
            "This is a decent product with some nice features and works well for the price",  # medium
            " ".join(["This is a very detailed review"] * 10),  # high
        ]
        result = analyze_reviews(reviews, min_frequency=1)
        assert result.quality_distribution["high"] >= 0
        assert result.quality_distribution["medium"] >= 0
        assert result.quality_distribution["low"] >= 0
        total = sum(result.quality_distribution.values())
        assert total == 3

    def test_chinese_reviews(self):
        reviews = [
            "非常喜欢这个产品，质量很好，推荐购买",
            "质量很好，用起来很方便，非常满意",
            "垃圾产品，退货了，太差了",
        ]
        result = analyze_reviews(reviews, min_frequency=1)
        assert result.total_reviews == 3
        assert isinstance(result.overall_sentiment, Sentiment)

    def test_min_frequency_param(self):
        reviews = [
            "I love the sound quality",
            "Sound quality is great",
        ]
        result1 = analyze_reviews(reviews, min_frequency=1)
        result2 = analyze_reviews(reviews, min_frequency=10)
        # Higher min_frequency should produce fewer benefits
        assert len(result2.benefits) <= len(result1.benefits)
