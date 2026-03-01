"""Tests for Performance Predictor."""
import pytest
from app.performance_predictor import (
    PerformancePredictor,
    PerformancePrediction, SignalScore, PerformanceTier,
    predict_performance,
)


class TestBasicPrediction:
    def test_predict_good_listing(self):
        predictor = PerformancePredictor()
        prediction = predictor.predict(
            title="Premium Wireless Bluetooth Headphones with Noise Cancelling Technology - 30 Hour Battery",
            description="Enjoy superior sound quality with these premium wireless headphones. Features advanced noise cancelling technology, ergonomic design, and long-lasting 30-hour battery life. Perfect for music lovers and commuters.",
            bullet_points=[
                "Advanced noise cancelling blocks out ambient noise",
                "Premium sound quality with deep bass",
                "30-hour battery life for all-day listening",
                "Comfortable ergonomic design for extended wear",
                "Bluetooth 5.0 connectivity with extended range"
            ],
            keywords=["wireless", "bluetooth", "headphones", "noise cancelling"],
            price=79.99,
            competitor_prices=[69.99, 89.99, 99.99],
            image_count=7,
            brand="AudioPro"
        )
        assert prediction.overall_score >= 70
        assert prediction.tier in [PerformanceTier.GOOD, PerformanceTier.EXCELLENT]

    def test_predict_poor_listing(self):
        predictor = PerformancePredictor()
        prediction = predictor.predict(
            title="Product",
            description="Buy now",
            price=10.0
        )
        assert prediction.overall_score < 50
        assert prediction.tier in [PerformanceTier.POOR, PerformanceTier.CRITICAL]

    def test_signals_populated(self):
        predictor = PerformancePredictor()
        prediction = predictor.predict(
            title="Test Product"
        )
        assert len(prediction.signals) >= 10  # Should have multiple signals

    def test_top_improvements(self):
        predictor = PerformancePredictor()
        prediction = predictor.predict(
            title="Short"
        )
        assert len(prediction.top_improvements) > 0


class TestTitleQualityScoring:
    def test_good_title_length(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Premium Wireless Bluetooth Headphones with Noise Cancelling"
        )
        title_signal = next(s for s in pred.signals if s.name == "title_quality")
        assert title_signal.score >= 50

    def test_short_title_penalty(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(title="Short")
        title_signal = next(s for s in pred.signals if s.name == "title_quality")
        assert title_signal.score < 50

    def test_power_words_bonus(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Premium Professional Upgraded Wireless Headphones 2024"
        )
        title_signal = next(s for s in pred.signals if s.name == "title_quality")
        # Should score higher due to power words
        assert title_signal.score >= 60

    def test_title_case_bonus(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Premium Wireless Bluetooth Headphones"
        )
        title_signal = next(s for s in pred.signals if s.name == "title_quality")
        assert title_signal.score > 0


class TestKeywordCoverage:
    def test_keywords_in_title_and_text(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Wireless Bluetooth Headphones",
            description="Premium wireless bluetooth audio device",
            keywords=["wireless", "bluetooth", "headphones"]
        )
        kw_signal = next(s for s in pred.signals if s.name == "keyword_coverage")
        assert kw_signal.score >= 80

    def test_missing_keywords(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Generic Product",
            description="Simple description",
            keywords=["wireless", "bluetooth", "premium"]
        )
        kw_signal = next(s for s in pred.signals if s.name == "keyword_coverage")
        assert kw_signal.score < 60

    def test_no_keywords_provided(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(title="Product")
        kw_signal = next(s for s in pred.signals if s.name == "keyword_coverage")
        assert len(kw_signal.suggestions) > 0


class TestDescriptionDepth:
    def test_long_description(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Product",
            description="Detailed product description. " * 50  # 200+ words
        )
        desc_signal = next(s for s in pred.signals if s.name == "description_depth")
        assert desc_signal.score >= 50

    def test_short_description(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Product",
            description="Short"
        )
        desc_signal = next(s for s in pred.signals if s.name == "description_depth")
        assert desc_signal.score < 30

    def test_no_description(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(title="Product", description="")
        desc_signal = next(s for s in pred.signals if s.name == "description_depth")
        assert desc_signal.score == 0


class TestBulletPoints:
    def test_ideal_bullet_count(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Product",
            bullet_points=[f"Feature {i}: detailed description of benefit" for i in range(5)]
        )
        bullet_signal = next(s for s in pred.signals if s.name == "bullet_points")
        assert bullet_signal.score >= 70

    def test_no_bullets(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(title="Product")
        bullet_signal = next(s for s in pred.signals if s.name == "bullet_points")
        assert bullet_signal.score == 0

    def test_few_bullets(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Product",
            bullet_points=["One", "Two"]
        )
        bullet_signal = next(s for s in pred.signals if s.name == "bullet_points")
        assert bullet_signal.score < 40


class TestPriceCompetitiveness:
    def test_below_market_price(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Product",
            price=50.0,
            competitor_prices=[60.0, 70.0, 80.0]
        )
        price_signal = next(s for s in pred.signals if s.name == "price_competitiveness")
        assert price_signal.score >= 70

    def test_above_market_price(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Product",
            price=100.0,
            competitor_prices=[50.0, 60.0, 70.0]
        )
        price_signal = next(s for s in pred.signals if s.name == "price_competitiveness")
        assert price_signal.score < 60

    def test_no_competitor_data(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(title="Product", price=50.0)
        price_signal = next(s for s in pred.signals if s.name == "price_competitiveness")
        assert price_signal.score == 50  # Neutral score


class TestImageSignals:
    def test_ideal_image_count(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(title="Product", image_count=8)
        img_signal = next(s for s in pred.signals if s.name == "image_signals")
        assert img_signal.score >= 90

    def test_no_images(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(title="Product", image_count=0)
        img_signal = next(s for s in pred.signals if s.name == "image_signals")
        assert img_signal.score == 0

    def test_few_images(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(title="Product", image_count=3)
        img_signal = next(s for s in pred.signals if s.name == "image_signals")
        assert 25 <= img_signal.score <= 75


class TestBrandPresence:
    def test_brand_in_title(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="AudioPro Wireless Headphones",
            brand="AudioPro"
        )
        brand_signal = next(s for s in pred.signals if s.name == "brand_presence")
        assert brand_signal.score >= 70

    def test_no_brand(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(title="Product")
        brand_signal = next(s for s in pred.signals if s.name == "brand_presence")
        assert brand_signal.score < 50


class TestMobileReadability:
    def test_short_mobile_friendly_title(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Premium Wireless Headphones",
            bullet_points=["Short bullet 1", "Short bullet 2"]
        )
        mobile_signal = next(s for s in pred.signals if s.name == "mobile_readability")
        assert mobile_signal.score >= 70

    def test_long_title_mobile_penalty(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="A" * 150  # Very long title
        )
        mobile_signal = next(s for s in pred.signals if s.name == "mobile_readability")
        assert mobile_signal.score < 80


class TestSpamDetection:
    def test_clean_listing(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Premium Wireless Headphones",
            description="Professional audio device"
        )
        spam_signal = next(s for s in pred.signals if s.name == "special_characters")
        assert spam_signal.score >= 90

    def test_spam_patterns(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="BEST!!! CHEAP!!! FREE SHIPPING!!!",
            description="BUY BUY BUY NOW NOW NOW"
        )
        spam_signal = next(s for s in pred.signals if s.name == "special_characters")
        assert spam_signal.score < 50


class TestComparisonAndReporting:
    def test_compare_multiple_listings(self):
        predictor = PerformancePredictor()
        listings = [
            {"title": "Premium Wireless Bluetooth Headphones" * 2, "price": 79.99, "image_count": 7},
            {"title": "Basic Product", "price": 10.0, "image_count": 1},
            {"title": "Mid-Range Product Name Here", "price": 29.99, "image_count": 4}
        ]
        results = predictor.compare(listings)
        assert len(results) == 3
        # Should be sorted by score
        assert results[0].overall_score >= results[1].overall_score

    def test_report_formatting(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Test Product Name Here",
            description="Description" * 20,
            price=49.99,
            image_count=5
        )
        report = predictor.report(pred)
        assert "Performance Prediction" in report
        assert "Overall Score" in report
        assert str(pred.overall_score) in report

    def test_signal_breakdown_in_report(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(title="Product")
        report = predictor.report(pred)
        assert "Signal Breakdown" in report
        # Should have visual bars
        assert "█" in report or "░" in report


class TestPlatformSpecifics:
    def test_amazon_title_length(self):
        predictor = PerformancePredictor(platform="amazon")
        pred = predictor.predict(title="A" * 100)
        length_signal = next(s for s in pred.signals if s.name == "title_length_fit")
        assert length_signal.score > 0

    def test_ebay_title_length(self):
        predictor = PerformancePredictor(platform="ebay")
        pred = predictor.predict(title="A" * 85)  # Over eBay's 80 char
        length_signal = next(s for s in pred.signals if s.name == "title_length_fit")
        assert length_signal.score < 100


class TestEstimates:
    def test_ctr_estimate(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(title="Premium Product " * 8, image_count=7)
        assert pred.ctr_estimate in ["low", "average", "high"]

    def test_conversion_estimate(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(title="Product")
        assert pred.conversion_estimate in ["low", "average", "high"]

    def test_visibility_estimate(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(title="Product")
        assert pred.visibility_estimate in ["low", "average", "high"]


class TestConvenienceFunction:
    def test_predict_performance_quick(self):
        pred = predict_performance(
            title="Wireless Headphones",
            platform="amazon",
            description="Great headphones",
            price=49.99
        )
        assert isinstance(pred, PerformancePrediction)
        assert pred.overall_score >= 0


class TestEdgeCases:
    def test_empty_inputs(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(title="")
        assert pred.overall_score >= 0
        assert pred.overall_score <= 100

    def test_very_long_inputs(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="X" * 1000,
            description="Y" * 10000
        )
        assert pred.overall_score >= 0

    def test_special_characters(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Product™ with Special® Characters & 中文"
        )
        assert pred.overall_score >= 0

    def test_none_values(self):
        predictor = PerformancePredictor()
        pred = predictor.predict(
            title="Product",
            price=None,
            brand=None,
            competitor_prices=None
        )
        assert pred.overall_score >= 0
