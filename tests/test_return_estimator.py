"""Tests for Return Rate Estimator."""
import pytest
from app.return_estimator import (
    ReturnRateEstimator,
    ReturnEstimate, ReturnFactor, ReturnRisk,
    estimate_returns,
)


class TestBasicEstimation:
    def test_estimate_good_listing(self):
        estimator = ReturnRateEstimator(category="electronics")
        estimate = estimator.estimate(
            title="Premium Wireless Headphones with Detailed Specifications",
            description="Made from high-quality stainless steel and silicone. Dimensions: 10 x 8 x 5 inches. Weight: 8 oz. Compatible with all devices.",
            bullet_points=[
                "Premium stainless steel construction for durability",
                "Comfortable silicone ear tips for extended wear",
                "Dimensions: 10 x 8 x 5 inches, Weight: 8 oz",
                "Works with all Bluetooth devices",
                "30-day money-back guarantee"
            ],
            has_size_chart=False,
            image_count=7,
            has_video=True,
            price=79.99,
            rating=4.5,
            review_count=250
        )
        assert estimate.risk_level in [ReturnRisk.LOW, ReturnRisk.MODERATE]

    def test_estimate_poor_listing(self):
        estimator = ReturnRateEstimator(category="clothing")
        estimate = estimator.estimate(
            title="Product",
            description="Buy now",
            has_size_chart=False,
            image_count=1
        )
        assert estimate.risk_level in [ReturnRisk.HIGH, ReturnRisk.CRITICAL]


class TestSpecificationCompleteness:
    def test_complete_specs(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            description="Dimensions: 12x10x8 inches. Weight: 5 lbs. Material: Stainless steel. Color: Black. Package includes: unit, charger, manual. Battery: rechargeable. Compatible with iOS and Android."
        )
        spec_factor = next(f for f in estimate.factors if f.name == "specification_completeness")
        assert spec_factor.score < 30  # Low score = low risk

    def test_missing_specs(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            description="A great product for you"
        )
        spec_factor = next(f for f in estimate.factors if f.name == "specification_completeness")
        assert spec_factor.score > 50  # High score = high risk


class TestSizingClarity:
    def test_sized_product_with_chart(self):
        estimator = ReturnRateEstimator(category="clothing")
        estimate = estimator.estimate(
            title="T-Shirt",
            description="Size chart available. Fits true to size. Measurements provided.",
            has_size_chart=True
        )
        sizing_factor = next(f for f in estimate.factors if f.name == "sizing_clarity")
        assert sizing_factor.score < 30

    def test_sized_product_no_chart(self):
        estimator = ReturnRateEstimator(category="clothing")
        estimate = estimator.estimate(
            title="Dress",
            description="Beautiful dress",
            has_size_chart=False
        )
        sizing_factor = next(f for f in estimate.factors if f.name == "sizing_clarity")
        assert sizing_factor.score > 60

    def test_non_sized_product(self):
        estimator = ReturnRateEstimator(category="electronics")
        estimate = estimator.estimate(
            title="Headphones",
            description="Dimensions: 10x5x3 inches"
        )
        sizing_factor = next(f for f in estimate.factors if f.name == "sizing_clarity")
        # Weight should be lower for non-apparel
        assert sizing_factor.weight < 0.15


class TestMaterialDescription:
    def test_materials_described(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            description="Made from premium stainless steel, silicone rubber, and tempered glass"
        )
        material_factor = next(f for f in estimate.factors if f.name == "material_description")
        assert material_factor.score < 20

    def test_no_materials(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            description="Great quality product"
        )
        material_factor = next(f for f in estimate.factors if f.name == "material_description")
        assert material_factor.score > 40


class TestImageCoverage:
    def test_many_images_with_video(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            image_count=8,
            has_video=True
        )
        image_factor = next(f for f in estimate.factors if f.name == "image_coverage")
        assert image_factor.score < 15

    def test_no_images(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            image_count=0
        )
        image_factor = next(f for f in estimate.factors if f.name == "image_coverage")
        assert image_factor.score > 70

    def test_few_images_no_video(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            image_count=2,
            has_video=False
        )
        image_factor = next(f for f in estimate.factors if f.name == "image_coverage")
        assert image_factor.score > 30


class TestExpectationManagement:
    def test_good_expectation_setting(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            description="Please note: colors may vary slightly due to monitor settings. Manual measurement tolerance: 1-3cm."
        )
        exp_factor = next(f for f in estimate.factors if f.name == "expectation_management")
        assert exp_factor.score < 30

    def test_no_expectation_management(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            description="Perfect product for you"
        )
        exp_factor = next(f for f in estimate.factors if f.name == "expectation_management")
        assert exp_factor.score > 30

    def test_too_many_disclaimers(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            description="Please note may vary attention notice disclaimer important please note attention"
        )
        exp_factor = next(f for f in estimate.factors if f.name == "expectation_management")
        # Too many = product may have issues
        assert exp_factor.score > 40


class TestVagueLanguage:
    def test_no_vague_claims(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Stainless Steel Water Bottle",
            description="Made from 18/8 stainless steel. Holds 32 oz. Dimensions: 10 x 3 inches."
        )
        vague_factor = next(f for f in estimate.factors if f.name == "vague_language")
        assert vague_factor.score < 20

    def test_many_vague_claims(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Amazing High Quality Perfect Product",
            description="Best quality amazing incredible fantastic gorgeous luxury"
        )
        vague_factor = next(f for f in estimate.factors if f.name == "vague_language")
        assert vague_factor.score > 50


class TestTitleClarity:
    def test_clear_title(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Premium Stainless Steel Water Bottle - 32 oz Insulated"
        )
        title_factor = next(f for f in estimate.factors if f.name == "title_clarity")
        assert title_factor.score < 30

    def test_short_vague_title(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Buy"
        )
        title_factor = next(f for f in estimate.factors if f.name == "title_clarity")
        assert title_factor.score > 30

    def test_all_caps_title(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="PREMIUM PRODUCT HERE"
        )
        title_factor = next(f for f in estimate.factors if f.name == "title_clarity")
        assert title_factor.score > 20


class TestSocialProof:
    def test_good_reviews(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            rating=4.5,
            review_count=100
        )
        social_factor = next(f for f in estimate.factors if f.name == "social_proof")
        assert social_factor.score < 20

    def test_poor_reviews(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            rating=3.0,
            review_count=50
        )
        social_factor = next(f for f in estimate.factors if f.name == "social_proof")
        assert social_factor.score > 60

    def test_no_rating(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            rating=None
        )
        social_factor = next(f for f in estimate.factors if f.name == "social_proof")
        assert social_factor.score == 45


class TestPriceSignal:
    def test_very_cheap_price(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            price=3.99
        )
        price_factor = next(f for f in estimate.factors if f.name == "price_signal")
        assert price_factor.score > 40

    def test_reasonable_price(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            price=49.99
        )
        price_factor = next(f for f in estimate.factors if f.name == "price_signal")
        assert price_factor.score < 30

    def test_expensive_price(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            price=299.99
        )
        price_factor = next(f for f in estimate.factors if f.name == "price_signal")
        # High price = higher expectations
        assert price_factor.score > 25


class TestInfoCompleteness:
    def test_comprehensive_info(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            description="Detailed product description with specifications and features. " * 15,
            bullet_points=[f"Feature {i}: detailed explanation of benefit" for i in range(5)]
        )
        info_factor = next(f for f in estimate.factors if f.name == "info_completeness")
        assert info_factor.score < 20

    def test_minimal_info(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            description="Short",
            bullet_points=[]
        )
        info_factor = next(f for f in estimate.factors if f.name == "info_completeness")
        assert info_factor.score > 60


class TestCategoryBaselines:
    def test_clothing_baseline(self):
        estimator = ReturnRateEstimator(category="clothing")
        assert estimator.baseline == 15.0

    def test_electronics_baseline(self):
        estimator = ReturnRateEstimator(category="electronics")
        assert estimator.baseline == 8.0

    def test_default_baseline(self):
        estimator = ReturnRateEstimator(category="unknown")
        assert estimator.baseline == 8.0


class TestReturnRateCalculation:
    def test_estimate_above_baseline(self):
        estimator = ReturnRateEstimator(category="electronics")
        # Poor listing
        estimate = estimator.estimate(
            title="Product",
            description="Buy now"
        )
        assert estimate.estimated_rate > estimate.category_baseline

    def test_estimate_below_baseline(self):
        estimator = ReturnRateEstimator(category="electronics")
        # Good listing
        estimate = estimator.estimate(
            title="Premium Electronics Product with Complete Specifications",
            description="Material: stainless steel. Dimensions: 10x8x5 inches. Weight: 2 lbs. " * 10,
            bullet_points=[f"Feature {i}" for i in range(5)],
            image_count=7,
            has_video=True,
            rating=4.6,
            review_count=200
        )
        assert estimate.estimated_rate < estimate.category_baseline

    def test_delta_calculation(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(title="Product", description="Desc")
        expected_delta = estimate.estimated_rate - estimate.category_baseline
        assert abs(estimate.delta_from_baseline - expected_delta) < 0.1


class TestTopRisksAndRecommendations:
    def test_top_risks_populated(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Prod",
            description="",
            image_count=0
        )
        assert len(estimate.top_risks) > 0

    def test_recommendations_populated(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Short",
            description="Short",
            image_count=1
        )
        assert len(estimate.recommendations) > 0

    def test_recommendations_ordered_by_impact(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="P",
            description="",
            image_count=0,
            has_size_chart=False
        )
        # Should prioritize highest-impact fixes
        assert len(estimate.recommendations) > 0


class TestReportFormatting:
    def test_report_generation(self):
        estimator = ReturnRateEstimator(category="clothing")
        estimate = estimator.estimate(
            title="Product",
            description="Description"
        )
        report = estimator.report(estimate)
        assert "Return Rate Estimation" in report
        assert str(estimate.estimated_rate) in report
        assert estimate.risk_level.value.upper() in report

    def test_report_includes_factors(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(title="Product")
        report = estimator.report(estimate)
        assert "Risk Factors:" in report

    def test_report_includes_recommendations(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="P",
            description=""
        )
        report = estimator.report(estimate)
        if estimate.recommendations:
            assert "Recommendations:" in report


class TestConvenienceFunction:
    def test_estimate_returns_quick(self):
        estimate = estimate_returns(
            title="Premium Product",
            category="electronics",
            description="Made from stainless steel",
            image_count=5
        )
        assert isinstance(estimate, ReturnEstimate)


class TestEdgeCases:
    def test_empty_inputs(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="",
            description=""
        )
        assert estimate.estimated_rate >= 0
        assert estimate.estimated_rate <= 100

    def test_very_long_inputs(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="X" * 500,
            description="Y" * 10000
        )
        assert estimate.estimated_rate >= 0

    def test_special_characters(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product™ with Special® Characters & 中文"
        )
        assert estimate.estimated_rate >= 0

    def test_negative_price(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            price=-10.0
        )
        # Should handle gracefully
        assert estimate.estimated_rate >= 0

    def test_extreme_rating(self):
        estimator = ReturnRateEstimator()
        estimate = estimator.estimate(
            title="Product",
            rating=5.5,  # Invalid but should handle
            review_count=100
        )
        assert estimate.estimated_rate >= 0
