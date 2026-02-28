"""Tests for review_analyzer module."""
import pytest
from datetime import datetime
from app.review_analyzer import (
    ReviewItem, ReviewAnalyzer, SentimentResult, PainPoint,
    FeatureRequest, BuyerKeyword, ReviewInsights,
    analyze_reviews, format_review_report,
)


# --- Fixtures ---

@pytest.fixture
def positive_reviews():
    return [
        ReviewItem(text="Amazing product! Love the quality, very sturdy and reliable.",
                   rating=5.0, verified=True, date="2025-11-15"),
        ReviewItem(text="Perfect gift for my wife. Beautiful design and excellent build.",
                   rating=5.0, verified=True, date="2025-11-20"),
        ReviewItem(text="Great value for the price. Recommend to everyone!",
                   rating=4.0, verified=True, date="2025-12-01"),
        ReviewItem(text="Fantastic! Best purchase I've made this year. Super happy.",
                   rating=5.0, verified=False, date="2025-12-05"),
    ]


@pytest.fixture
def negative_reviews():
    return [
        ReviewItem(text="Terrible quality. Broke after two days. Cheap plastic.",
                   rating=1.0, verified=True, date="2025-10-01"),
        ReviewItem(text="Arrived damaged. Missing parts. Very disappointing.",
                   rating=1.0, verified=True, date="2025-10-15"),
        ReviewItem(text="Overpriced for what you get. Not worth the money.",
                   rating=2.0, verified=True, date="2025-11-01"),
        ReviewItem(text="Too small, doesn't fit. Size is way off from description.",
                   rating=2.0, verified=False, date="2025-11-10"),
    ]


@pytest.fixture
def mixed_reviews(positive_reviews, negative_reviews):
    return positive_reviews + negative_reviews + [
        ReviewItem(text="It's okay. Nothing special but works.",
                   rating=3.0, verified=True, date="2025-12-10"),
        ReviewItem(text="Decent product for the price point.",
                   rating=3.0, verified=True, date="2025-12-15"),
    ]


@pytest.fixture
def reviews_with_features():
    return [
        ReviewItem(text="Wish it had a longer battery life. Otherwise great.",
                   rating=4.0),
        ReviewItem(text="Would be nice if it came with a carrying case.",
                   rating=4.0),
        ReviewItem(text="Should include a USB-C cable instead of micro USB.",
                   rating=3.0),
        ReviewItem(text="Needs a better manual. Instructions are confusing.",
                   rating=3.0),
        ReviewItem(text="Missing a power indicator LED. Hard to tell if it's on.",
                   rating=3.0),
    ]


# --- SentimentResult Tests ---

class TestSentimentResult:
    def test_positive_sentiment(self):
        s = SentimentResult(score=0.5, label="positive")
        assert s.is_positive is True
        assert s.is_negative is False

    def test_negative_sentiment(self):
        s = SentimentResult(score=-0.5, label="negative")
        assert s.is_negative is True
        assert s.is_positive is False

    def test_neutral_sentiment(self):
        s = SentimentResult(score=0.0, label="neutral")
        assert s.is_positive is False
        assert s.is_negative is False

    def test_boundary_positive(self):
        s = SentimentResult(score=0.11, label="positive")
        assert s.is_positive is True

    def test_boundary_negative(self):
        s = SentimentResult(score=-0.11, label="negative")
        assert s.is_negative is True


# --- PainPoint Tests ---

class TestPainPoint:
    def test_severity_critical(self):
        pp = PainPoint(category="quality", description="test", severity=0.8)
        assert pp.severity_label == "critical"

    def test_severity_moderate(self):
        pp = PainPoint(category="quality", description="test", severity=0.5)
        assert pp.severity_label == "moderate"

    def test_severity_minor(self):
        pp = PainPoint(category="quality", description="test", severity=0.2)
        assert pp.severity_label == "minor"

    def test_severity_boundary_critical(self):
        pp = PainPoint(category="quality", description="test", severity=0.7)
        assert pp.severity_label == "critical"

    def test_severity_boundary_moderate(self):
        pp = PainPoint(category="quality", description="test", severity=0.4)
        assert pp.severity_label == "moderate"


# --- ReviewInsights Tests ---

class TestReviewInsights:
    def test_empty_insights(self):
        ri = ReviewInsights()
        assert ri.satisfaction_rate == 0.0
        assert ri.complaint_rate == 0.0
        assert ri.has_quality_issues is False

    def test_satisfaction_rate(self):
        ri = ReviewInsights(
            total_reviews=10,
            sentiment_distribution={"positive": 7, "negative": 2, "neutral": 1},
        )
        assert ri.satisfaction_rate == 70.0

    def test_complaint_rate(self):
        ri = ReviewInsights(
            total_reviews=10,
            sentiment_distribution={"positive": 7, "negative": 2, "neutral": 1},
        )
        assert ri.complaint_rate == 20.0

    def test_has_quality_issues(self):
        ri = ReviewInsights(
            pain_points=[
                PainPoint(category="quality", description="test", severity=0.6),
            ]
        )
        assert ri.has_quality_issues is True

    def test_no_quality_issues(self):
        ri = ReviewInsights(
            pain_points=[
                PainPoint(category="sizing", description="test", severity=0.6),
            ]
        )
        assert ri.has_quality_issues is False


# --- ReviewAnalyzer Tests ---

class TestReviewAnalyzerSentiment:
    def test_positive_sentiment(self):
        reviews = [ReviewItem(text="Amazing and excellent product! Love it!")]
        analyzer = ReviewAnalyzer(reviews)
        result = analyzer.analyze()
        assert result.sentiment_distribution["positive"] == 1

    def test_negative_sentiment(self):
        reviews = [ReviewItem(text="Terrible awful product. Worst purchase ever.")]
        analyzer = ReviewAnalyzer(reviews)
        result = analyzer.analyze()
        assert result.sentiment_distribution["negative"] == 1

    def test_neutral_sentiment(self):
        reviews = [ReviewItem(text="I received the package yesterday.")]
        analyzer = ReviewAnalyzer(reviews)
        result = analyzer.analyze()
        assert result.sentiment_distribution["neutral"] == 1

    def test_negation_flips_sentiment(self):
        reviews = [ReviewItem(text="Not great. Not amazing. Not perfect.")]
        analyzer = ReviewAnalyzer(reviews)
        result = analyzer.analyze()
        # Negated positive words should count as negative
        assert result.sentiment_distribution["negative"] >= 1

    def test_intensifier_boosts_sentiment(self):
        analyzer = ReviewAnalyzer([])
        sent = analyzer._analyze_sentiment("Very amazing product")
        assert sent.is_positive

    def test_empty_text_sentiment(self):
        analyzer = ReviewAnalyzer([])
        sent = analyzer._analyze_sentiment("")
        assert sent.label == "neutral"
        assert sent.score == 0.0

    def test_chinese_positive(self):
        reviews = [ReviewItem(text="非常好，满意，推荐购买")]
        analyzer = ReviewAnalyzer(reviews)
        result = analyzer.analyze()
        assert result.sentiment_distribution["positive"] == 1

    def test_chinese_negative(self):
        reviews = [ReviewItem(text="垃圾产品，差，退货退款")]
        analyzer = ReviewAnalyzer(reviews)
        result = analyzer.analyze()
        assert result.sentiment_distribution["negative"] == 1

    def test_mixed_sentiments(self, mixed_reviews):
        analyzer = ReviewAnalyzer(mixed_reviews)
        result = analyzer.analyze()
        assert result.sentiment_distribution["positive"] > 0
        assert result.sentiment_distribution["negative"] > 0
        assert result.total_reviews == len(mixed_reviews)


class TestReviewAnalyzerRatings:
    def test_rating_distribution(self, mixed_reviews):
        analyzer = ReviewAnalyzer(mixed_reviews)
        result = analyzer.analyze()
        assert 5 in result.rating_distribution
        assert 1 in result.rating_distribution
        total = sum(result.rating_distribution.values())
        assert total == len(mixed_reviews)

    def test_avg_rating(self, positive_reviews):
        analyzer = ReviewAnalyzer(positive_reviews)
        result = analyzer.analyze()
        assert result.avg_rating > 4.0

    def test_no_ratings(self):
        reviews = [ReviewItem(text="Some text")]
        analyzer = ReviewAnalyzer(reviews)
        result = analyzer.analyze()
        assert result.avg_rating == 0.0
        assert result.rating_distribution == {}

    def test_clamp_ratings(self):
        reviews = [
            ReviewItem(text="test", rating=0),
            ReviewItem(text="test", rating=6),
        ]
        analyzer = ReviewAnalyzer(reviews)
        result = analyzer.analyze()
        assert 1 in result.rating_distribution
        assert 5 in result.rating_distribution


class TestReviewAnalyzerPainPoints:
    def test_quality_pain_point(self, negative_reviews):
        analyzer = ReviewAnalyzer(negative_reviews)
        result = analyzer.analyze()
        categories = [pp.category for pp in result.pain_points]
        assert "quality" in categories

    def test_sizing_pain_point(self, negative_reviews):
        analyzer = ReviewAnalyzer(negative_reviews)
        result = analyzer.analyze()
        categories = [pp.category for pp in result.pain_points]
        assert "sizing" in categories

    def test_pain_points_sorted_by_severity(self, negative_reviews):
        analyzer = ReviewAnalyzer(negative_reviews)
        result = analyzer.analyze()
        if len(result.pain_points) >= 2:
            assert result.pain_points[0].severity >= result.pain_points[1].severity

    def test_pain_point_has_quotes(self, negative_reviews):
        analyzer = ReviewAnalyzer(negative_reviews)
        result = analyzer.analyze()
        for pp in result.pain_points:
            if pp.frequency > 0:
                assert len(pp.sample_quotes) > 0

    def test_no_pain_points_from_positive(self, positive_reviews):
        analyzer = ReviewAnalyzer(positive_reviews)
        result = analyzer.analyze()
        # Positive reviews shouldn't generate many pain points
        critical = [pp for pp in result.pain_points if pp.severity >= 0.5]
        assert len(critical) == 0

    def test_delivery_pain_point(self):
        reviews = [
            ReviewItem(text="Arrived damaged. Slow shipping and wrong item sent.",
                       rating=1.0),
        ]
        analyzer = ReviewAnalyzer(reviews)
        result = analyzer.analyze()
        categories = [pp.category for pp in result.pain_points]
        assert "delivery" in categories

    def test_value_pain_point(self):
        reviews = [
            ReviewItem(text="Overpriced. Not worth the money at all.",
                       rating=2.0),
        ]
        analyzer = ReviewAnalyzer(reviews)
        result = analyzer.analyze()
        categories = [pp.category for pp in result.pain_points]
        assert "value" in categories


class TestReviewAnalyzerFeatureRequests:
    def test_extract_wish_pattern(self, reviews_with_features):
        analyzer = ReviewAnalyzer(reviews_with_features)
        result = analyzer.analyze()
        assert len(result.feature_requests) > 0

    def test_feature_request_text(self, reviews_with_features):
        analyzer = ReviewAnalyzer(reviews_with_features)
        result = analyzer.analyze()
        all_text = " ".join(fr.text for fr in result.feature_requests)
        # At least some of these should be captured
        assert len(all_text) > 0

    def test_feature_requests_sorted_by_frequency(self, reviews_with_features):
        analyzer = ReviewAnalyzer(reviews_with_features)
        result = analyzer.analyze()
        if len(result.feature_requests) >= 2:
            assert result.feature_requests[0].frequency >= result.feature_requests[1].frequency

    def test_no_feature_requests_from_simple_reviews(self):
        reviews = [
            ReviewItem(text="Great product. Works well."),
            ReviewItem(text="Love it!"),
        ]
        analyzer = ReviewAnalyzer(reviews)
        result = analyzer.analyze()
        assert len(result.feature_requests) == 0


class TestReviewAnalyzerKeywords:
    def test_extract_keywords(self, mixed_reviews):
        analyzer = ReviewAnalyzer(mixed_reviews)
        result = analyzer.analyze()
        assert len(result.buyer_keywords) > 0

    def test_keyword_has_context(self, mixed_reviews):
        analyzer = ReviewAnalyzer(mixed_reviews)
        result = analyzer.analyze()
        for kw in result.buyer_keywords:
            assert kw.context in ("positive", "negative", "mixed")

    def test_keywords_sorted_by_frequency(self, mixed_reviews):
        analyzer = ReviewAnalyzer(mixed_reviews)
        result = analyzer.analyze()
        if len(result.buyer_keywords) >= 2:
            assert result.buyer_keywords[0].frequency >= result.buyer_keywords[1].frequency

    def test_keywords_max_25(self):
        # Create many reviews with diverse words
        reviews = [
            ReviewItem(text=f"Word{i} is great and amazing product quality " * 5)
            for i in range(50)
        ]
        analyzer = ReviewAnalyzer(reviews)
        result = analyzer.analyze()
        assert len(result.buyer_keywords) <= 25


class TestReviewAnalyzerThemes:
    def test_positive_themes(self, positive_reviews):
        analyzer = ReviewAnalyzer(positive_reviews)
        result = analyzer.analyze()
        # Should have some positive themes
        assert isinstance(result.top_positive_themes, list)

    def test_negative_themes(self, negative_reviews):
        analyzer = ReviewAnalyzer(negative_reviews)
        result = analyzer.analyze()
        assert isinstance(result.top_negative_themes, list)


class TestReviewQuality:
    def test_quality_score_range(self, mixed_reviews):
        analyzer = ReviewAnalyzer(mixed_reviews)
        result = analyzer.analyze()
        assert 0 <= result.review_quality_score <= 100

    def test_empty_quality(self):
        analyzer = ReviewAnalyzer([])
        result = analyzer.analyze()
        assert result.review_quality_score == 0.0

    def test_verified_reviews_boost_quality(self):
        verified = [
            ReviewItem(text="Great!", rating=5.0, verified=True),
            ReviewItem(text="Bad!", rating=1.0, verified=True),
        ]
        unverified = [
            ReviewItem(text="Great!", rating=5.0, verified=False),
            ReviewItem(text="Bad!", rating=1.0, verified=False),
        ]
        a1 = ReviewAnalyzer(verified).analyze()
        a2 = ReviewAnalyzer(unverified).analyze()
        assert a1.review_quality_score >= a2.review_quality_score


class TestSentimentTrend:
    def test_trend_by_month(self):
        reviews = [
            ReviewItem(text="Great!", rating=5.0, date="2025-10-01"),
            ReviewItem(text="Terrible!", rating=1.0, date="2025-11-01"),
            ReviewItem(text="Okay", rating=3.0, date="2025-12-01"),
        ]
        result = ReviewAnalyzer(reviews).analyze()
        assert len(result.sentiment_trend) >= 2  # at least 2 months

    def test_trend_has_fields(self):
        reviews = [
            ReviewItem(text="Great!", rating=5.0, date="2025-10-15"),
        ]
        result = ReviewAnalyzer(reviews).analyze()
        if result.sentiment_trend:
            t = result.sentiment_trend[0]
            assert "month" in t
            assert "positive_pct" in t
            assert "negative_pct" in t
            assert "count" in t

    def test_no_date_skipped(self):
        reviews = [ReviewItem(text="Great!", rating=5.0)]
        result = ReviewAnalyzer(reviews).analyze()
        assert len(result.sentiment_trend) == 0  # No date → no trend


class TestSuggestions:
    def test_suggestions_for_pain_points(self, negative_reviews):
        result = ReviewAnalyzer(negative_reviews).analyze()
        assert len(result.listing_suggestions) > 0

    def test_high_satisfaction_suggestion(self, positive_reviews):
        result = ReviewAnalyzer(positive_reviews).analyze()
        has_green = any("🟢" in s for s in result.listing_suggestions)
        assert has_green is True

    def test_low_satisfaction_suggestion(self, negative_reviews):
        result = ReviewAnalyzer(negative_reviews).analyze()
        has_red = any("🔴" in s for s in result.listing_suggestions)
        assert has_red is True


class TestConvenienceFunction:
    def test_analyze_reviews_dict(self):
        reviews = [
            {"text": "Love it!", "rating": 5.0, "verified": True},
            {"text": "Terrible!", "rating": 1.0, "verified": False},
        ]
        result = analyze_reviews(reviews)
        assert result.total_reviews == 2
        assert result.avg_rating == 3.0

    def test_analyze_reviews_empty(self):
        result = analyze_reviews([])
        assert result.total_reviews == 0

    def test_analyze_reviews_minimal(self):
        result = analyze_reviews([{"text": "OK"}])
        assert result.total_reviews == 1


class TestFormatReport:
    def test_format_report_structure(self, mixed_reviews):
        result = ReviewAnalyzer(mixed_reviews).analyze()
        report = format_review_report(result)
        assert "REVIEW ANALYSIS REPORT" in report
        assert "Rating Distribution" in report
        assert "Sentiment Distribution" in report

    def test_format_empty_report(self):
        result = ReviewInsights()
        report = format_review_report(result)
        assert "Total Reviews: 0" in report

    def test_format_report_has_pain_points(self, negative_reviews):
        result = ReviewAnalyzer(negative_reviews).analyze()
        report = format_review_report(result)
        if result.pain_points:
            assert "Pain Points" in report

    def test_format_report_has_suggestions(self, mixed_reviews):
        result = ReviewAnalyzer(mixed_reviews).analyze()
        report = format_review_report(result)
        if result.listing_suggestions:
            assert "Listing Optimization Suggestions" in report


class TestEdgeCases:
    def test_single_review(self):
        result = ReviewAnalyzer([ReviewItem(text="OK", rating=3.0)]).analyze()
        assert result.total_reviews == 1

    def test_all_same_rating(self):
        reviews = [ReviewItem(text="Good", rating=5.0) for _ in range(10)]
        result = ReviewAnalyzer(reviews).analyze()
        assert result.avg_rating == 5.0

    def test_very_long_review(self):
        long_text = "Great " * 1000
        reviews = [ReviewItem(text=long_text, rating=5.0)]
        result = ReviewAnalyzer(reviews).analyze()
        assert result.total_reviews == 1

    def test_special_characters(self):
        reviews = [ReviewItem(text="★★★★★ 5/5!!! @#$% <br> &amp;", rating=5.0)]
        result = ReviewAnalyzer(reviews).analyze()
        assert result.total_reviews == 1

    def test_unicode_text(self):
        reviews = [ReviewItem(text="素晴らしい製品です！", rating=5.0)]
        result = ReviewAnalyzer(reviews).analyze()
        assert result.total_reviews == 1

    def test_invalid_date(self):
        reviews = [ReviewItem(text="Good", date="not-a-date", rating=4.0)]
        result = ReviewAnalyzer(reviews).analyze()
        assert result.total_reviews == 1
        assert len(result.sentiment_trend) == 0
