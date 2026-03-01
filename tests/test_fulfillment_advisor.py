"""Tests for Fulfillment Advisor."""
import pytest
import tempfile
import os
from app.fulfillment_advisor import (
    FulfillmentAdvisor,
    FBACalculator, FBMCalculator, ThreePLCalculator, ProfitCalculator,
    ProductDimensions, FulfillmentCost, ShippingStrategy, ProfitAnalysis,
    SizeTier, FulfillmentMethod, ShippingSpeed, StorageSeason, Marketplace,
    SizeTierClassifier, FulfillmentStore,
)


class TestProductDimensions:
    def test_basic_properties(self):
        dims = ProductDimensions(10, 8, 6, 16)  # 10x8x6 inches, 16 oz
        assert dims.length_inches == 10
        assert dims.weight_oz == 16
        assert dims.weight_lb == 1.0  # 16 oz = 1 lb

    def test_cubic_feet_calculation(self):
        dims = ProductDimensions(12, 12, 12, 16)  # 1 cubic foot
        assert abs(dims.cubic_feet - 1.0) < 0.01

    def test_girth_calculation(self):
        dims = ProductDimensions(20, 10, 5, 32)
        # Girth = longest + 2*(shorter + shortest) = 20 + 2*(10+5) = 50
        assert dims.girth == 50

    def test_dimensional_weight(self):
        dims = ProductDimensions(20, 20, 20, 16)  # large box, light weight
        # Dim weight = (20*20*20)/139 in lb = 57.55 lb = 920 oz
        assert dims.dimensional_weight_oz > dims.weight_oz

    def test_billable_weight(self):
        dims = ProductDimensions(12, 12, 12, 32)
        billable = dims.billable_weight_oz
        # Should be max of actual and dimensional
        assert billable >= dims.weight_oz
        assert billable >= dims.dimensional_weight_oz


class TestSizeTierClassifier:
    def test_small_standard(self):
        classifier = SizeTierClassifier()
        dims = ProductDimensions(10, 8, 0.5, 12)  # Small standard
        tier = classifier.classify(dims)
        assert tier == SizeTier.SMALL_STANDARD

    def test_large_standard(self):
        classifier = SizeTierClassifier()
        dims = ProductDimensions(15, 10, 5, 200)  # Large standard
        tier = classifier.classify(dims)
        assert tier == SizeTier.LARGE_STANDARD

    def test_small_oversize(self):
        classifier = SizeTierClassifier()
        dims = ProductDimensions(50, 20, 15, 800)  # Small oversize
        tier = classifier.classify(dims)
        assert tier == SizeTier.SMALL_OVERSIZE

    def test_medium_oversize(self):
        classifier = SizeTierClassifier()
        dims = ProductDimensions(80, 30, 25, 1500)
        tier = classifier.classify(dims)
        assert tier == SizeTier.MEDIUM_OVERSIZE

    def test_special_oversize(self):
        classifier = SizeTierClassifier()
        dims = ProductDimensions(120, 40, 30, 3000)  # Special oversize
        tier = classifier.classify(dims)
        assert tier == SizeTier.SPECIAL_OVERSIZE


class TestFBACalculator:
    def test_small_standard_fee(self):
        calc = FBACalculator()
        dims = ProductDimensions(8, 6, 0.5, 4)  # 4 oz small standard
        fee = calc.fulfillment_fee(dims)
        assert fee > 0
        assert fee < 10  # Reasonable range

    def test_large_standard_fee(self):
        calc = FBACalculator()
        dims = ProductDimensions(15, 10, 5, 160)  # 10 lbs
        fee = calc.fulfillment_fee(dims)
        assert fee > 3
        assert fee < 15

    def test_oversize_fee(self):
        calc = FBACalculator()
        dims = ProductDimensions(60, 25, 20, 1000)  # Oversize
        fee = calc.fulfillment_fee(dims)
        assert fee > 8  # Oversize fees are higher

    def test_marketplace_multiplier(self):
        calc = FBACalculator()
        dims = ProductDimensions(10, 8, 5, 100)
        us_fee = calc.fulfillment_fee(dims, Marketplace.US)
        uk_fee = calc.fulfillment_fee(dims, Marketplace.UK)
        # UK should have a multiplier applied
        assert uk_fee != us_fee

    def test_storage_fee_standard_season(self):
        calc = FBACalculator()
        dims = ProductDimensions(12, 12, 12, 100)
        fee = calc.storage_fee(dims, StorageSeason.STANDARD, units=100, days_in_storage=30)
        assert fee > 0

    def test_storage_fee_peak_season(self):
        calc = FBACalculator()
        dims = ProductDimensions(12, 12, 12, 100)
        peak_fee = calc.storage_fee(dims, StorageSeason.PEAK, units=100, days_in_storage=30)
        standard_fee = calc.storage_fee(dims, StorageSeason.STANDARD, units=100, days_in_storage=30)
        # Peak should be more expensive
        assert peak_fee > standard_fee

    def test_long_term_storage_surcharge(self):
        calc = FBACalculator()
        dims = ProductDimensions(12, 12, 12, 100)
        long_term_fee = calc.storage_fee(dims, StorageSeason.STANDARD, units=10, days_in_storage=400)
        # Long-term storage (>365 days) should have surcharge
        assert long_term_fee > 0

    def test_estimate_complete(self):
        calc = FBACalculator()
        dims = ProductDimensions(12, 10, 8, 160)
        estimate = calc.estimate(dims, monthly_units=100)
        assert isinstance(estimate, FulfillmentCost)
        assert estimate.method == FulfillmentMethod.FBA
        assert estimate.fulfillment_fee > 0
        assert estimate.total_per_unit > 0
        assert "tier" in estimate.breakdown


class TestFBMCalculator:
    def test_shipping_cost_standard(self):
        calc = FBMCalculator()
        dims = ProductDimensions(10, 8, 5, 160)  # 10 lbs
        cost = calc.shipping_cost(dims, ShippingSpeed.STANDARD, zone=5)
        assert cost > 0
        assert cost < 50  # Reasonable range

    def test_shipping_cost_priority(self):
        calc = FBMCalculator()
        dims = ProductDimensions(10, 8, 5, 160)
        priority = calc.shipping_cost(dims, ShippingSpeed.PRIORITY, zone=5)
        standard = calc.shipping_cost(dims, ShippingSpeed.STANDARD, zone=5)
        # Priority should cost more
        assert priority > standard

    def test_zone_impact(self):
        calc = FBMCalculator()
        dims = ProductDimensions(8, 6, 4, 80)
        zone1 = calc.shipping_cost(dims, ShippingSpeed.STANDARD, zone=1)
        zone8 = calc.shipping_cost(dims, ShippingSpeed.STANDARD, zone=8)
        # Higher zone = higher cost
        assert zone8 > zone1

    def test_estimate_complete(self):
        calc = FBMCalculator(packaging_cost=0.75, labor_cost_per_min=0.25)
        dims = ProductDimensions(10, 8, 5, 100)
        estimate = calc.estimate(dims, monthly_units=50)
        assert isinstance(estimate, FulfillmentCost)
        assert estimate.method == FulfillmentMethod.FBM
        assert estimate.fulfillment_fee > 0  # packaging + labor
        assert estimate.shipping_fee > 0
        assert "packaging" in estimate.breakdown
        assert "labor" in estimate.breakdown


class TestThreePLCalculator:
    def test_small_item_estimate(self):
        calc = ThreePLCalculator()
        dims = ProductDimensions(6, 4, 2, 32)  # Small item
        estimate = calc.estimate(dims, monthly_units=100, monthly_orders=80)
        assert isinstance(estimate, FulfillmentCost)
        assert estimate.method == FulfillmentMethod.THREE_PL
        assert estimate.fulfillment_fee > 0
        assert "pick_and_pack" in estimate.breakdown

    def test_large_item_estimate(self):
        calc = ThreePLCalculator()
        dims = ProductDimensions(24, 18, 12, 400)  # Large item (>1 cubic ft)
        estimate = calc.estimate(dims, monthly_units=50)
        assert estimate.storage_monthly > 0
        assert "storage_total" in estimate.breakdown

    def test_custom_rates(self):
        custom = {"pick_and_pack": 2.50, "storage_per_bin": 6.00}
        calc = ThreePLCalculator(custom_rates=custom)
        dims = ProductDimensions(8, 6, 4, 50)
        estimate = calc.estimate(dims, monthly_units=100)
        # Should use custom rates
        assert estimate.breakdown["pick_and_pack"] == 2.50


class TestProfitCalculator:
    def test_basic_profit_calculation(self):
        calc = ProfitCalculator()
        analysis = calc.calculate(
            selling_price=50.0,
            cost_of_goods=20.0,
            fulfillment_cost=5.0,
            category="general"
        )
        assert isinstance(analysis, ProfitAnalysis)
        assert analysis.profit > 0
        assert analysis.margin_pct > 0
        assert analysis.roi_pct > 0

    def test_referral_fee_calculation(self):
        calc = ProfitCalculator()
        analysis = calc.calculate(
            selling_price=100.0,
            cost_of_goods=40.0,
            fulfillment_cost=10.0,
            category="general"  # 15% referral
        )
        assert abs(analysis.referral_fee - 15.0) < 0.01  # 15% of 100

    def test_category_referral_rates(self):
        calc = ProfitCalculator()
        electronics = calc.calculate(100, 50, 5, "electronics")  # 8%
        clothing = calc.calculate(100, 50, 5, "clothing")  # 17%
        # Electronics should have lower referral fee
        assert electronics.referral_fee < clothing.referral_fee

    def test_negative_profit(self):
        calc = ProfitCalculator()
        analysis = calc.calculate(
            selling_price=20.0,
            cost_of_goods=30.0,
            fulfillment_cost=5.0,
            category="general"
        )
        assert analysis.profit < 0
        assert analysis.margin_pct < 0

    def test_break_even_units(self):
        calc = ProfitCalculator()
        analysis = calc.calculate(50, 20, 5, "general")
        assert analysis.break_even_units > 0


class TestFulfillmentAdvisor:
    def test_compare_methods(self):
        advisor = FulfillmentAdvisor()
        dims = ProductDimensions(12, 10, 6, 200)
        strategy = advisor.compare_methods(dims, monthly_units=100)
        assert isinstance(strategy, ShippingStrategy)
        assert strategy.recommended in [FulfillmentMethod.FBA, FulfillmentMethod.FBM, FulfillmentMethod.THREE_PL]
        assert len(strategy.costs) == 3  # FBA, FBM, 3PL

    def test_strategy_savings_calculation(self):
        advisor = FulfillmentAdvisor()
        dims = ProductDimensions(10, 8, 5, 150)
        strategy = advisor.compare_methods(dims)
        # Savings should be difference between best and worst
        costs = [c.total_per_unit for c in strategy.costs]
        expected_savings = max(costs) - min(costs)
        assert abs(strategy.savings_vs_worst - expected_savings) < 0.01

    def test_oversize_warning(self):
        advisor = FulfillmentAdvisor()
        dims = ProductDimensions(70, 35, 25, 2000)  # Large oversize
        strategy = advisor.compare_methods(dims)
        # Should have warning about oversize
        warning_found = any("oversize" in w.lower() for w in strategy.warnings)
        assert warning_found

    def test_low_volume_warning(self):
        advisor = FulfillmentAdvisor()
        dims = ProductDimensions(10, 8, 5, 100)
        strategy = advisor.compare_methods(dims, monthly_units=15)
        # Should warn about low volume
        warning_found = any("volume" in w.lower() or "ipi" in w.lower() for w in strategy.warnings)
        assert warning_found

    def test_peak_season_warning(self):
        advisor = FulfillmentAdvisor()
        dims = ProductDimensions(10, 8, 5, 100)
        strategy = advisor.compare_methods(dims, season=StorageSeason.PEAK)
        # Should warn about peak season fees
        warning_found = any("peak" in w.lower() for w in strategy.warnings)
        assert warning_found

    def test_profit_analysis_fba(self):
        advisor = FulfillmentAdvisor()
        dims = ProductDimensions(10, 8, 5, 150)
        analysis = advisor.profit_analysis(
            dims, selling_price=50, cost_of_goods=20,
            method=FulfillmentMethod.FBA
        )
        assert isinstance(analysis, ProfitAnalysis)
        assert analysis.fulfillment_cost > 0

    def test_profit_analysis_fbm(self):
        advisor = FulfillmentAdvisor()
        dims = ProductDimensions(10, 8, 5, 150)
        analysis = advisor.profit_analysis(
            dims, selling_price=50, cost_of_goods=20,
            method=FulfillmentMethod.FBM
        )
        assert analysis.fulfillment_cost > 0

    def test_report_formatting(self):
        advisor = FulfillmentAdvisor()
        dims = ProductDimensions(12, 10, 6, 200)
        strategy = advisor.compare_methods(dims)
        report = advisor.report(strategy)
        assert "FULFILLMENT STRATEGY REPORT" in report
        assert strategy.recommended.value.upper() in report
        assert str(strategy.savings_vs_worst) in report

    def test_profit_report_formatting(self):
        advisor = FulfillmentAdvisor()
        dims = ProductDimensions(10, 8, 5, 150)
        analysis = advisor.profit_analysis(dims, 50, 20)
        report = advisor.profit_report(analysis)
        assert "PROFIT ANALYSIS" in report
        assert str(analysis.selling_price) in report
        assert str(analysis.profit) in report


class TestFulfillmentStore:
    def test_save_and_retrieve(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            store = FulfillmentStore(db_path)
            cost = FulfillmentCost(
                method=FulfillmentMethod.FBA,
                fulfillment_fee=5.0,
                shipping_fee=0.0,
                storage_monthly=1.0,
                total_per_unit=6.0,
                breakdown={"tier": "large_standard"}
            )
            row_id = store.save("PROD123", cost)
            assert row_id > 0

            history = store.history("PROD123")
            assert len(history) == 1
            assert history[0]["method"] == "fba"
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_cheapest_method(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            store = FulfillmentStore(db_path)
            # Save different methods
            store.save("PROD1", FulfillmentCost(FulfillmentMethod.FBA, 8, 0, 1, 9))
            store.save("PROD1", FulfillmentCost(FulfillmentMethod.FBM, 5, 3, 0.5, 8.5))
            store.save("PROD1", FulfillmentCost(FulfillmentMethod.THREE_PL, 6, 0, 1, 7))

            cheapest = store.cheapest_method("PROD1")
            assert cheapest is not None
            assert cheapest["method"] == "3pl"  # lowest total cost
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_empty_history(self):
        store = FulfillmentStore(":memory:")
        history = store.history("NONEXISTENT")
        assert history == []


class TestEdgeCases:
    def test_zero_weight_product(self):
        calc = FBACalculator()
        dims = ProductDimensions(5, 5, 5, 0.1)  # Very light
        fee = calc.fulfillment_fee(dims)
        assert fee > 0  # Should still have a minimum fee

    def test_very_heavy_product(self):
        calc = FBACalculator()
        dims = ProductDimensions(40, 30, 20, 2500)  # >150 lbs
        tier = SizeTierClassifier().classify(dims)
        assert tier == SizeTier.SPECIAL_OVERSIZE

    def test_zero_monthly_units(self):
        calc = FBACalculator()
        dims = ProductDimensions(10, 8, 5, 100)
        estimate = calc.estimate(dims, monthly_units=0)
        # Should handle gracefully
        assert estimate.total_per_unit >= 0
