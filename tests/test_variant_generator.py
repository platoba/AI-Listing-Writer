"""Tests for variant_generator A/B testing module."""
import pytest
from app.variant_generator import (
    Variant, VariantType, ABTest, TestStatus, TestResult,
    variant_id, chi_square_test, is_significant, calculate_lift,
    min_sample_size, generate_title_variants, generate_bullet_variants,
    generate_report,
)


# ── Variant Tests ──

class TestVariant:
    def test_ctr_calculation(self):
        v = Variant(id="a", name="test", variant_type=VariantType.TITLE,
                    impressions=1000, clicks=50)
        assert v.ctr == 5.0

    def test_ctr_zero_impressions(self):
        v = Variant(id="a", name="test", variant_type=VariantType.TITLE)
        assert v.ctr == 0.0

    def test_conversion_rate(self):
        v = Variant(id="a", name="test", variant_type=VariantType.TITLE,
                    clicks=200, conversions=10)
        assert v.conversion_rate == 5.0

    def test_conversion_rate_zero_clicks(self):
        v = Variant(id="a", name="test", variant_type=VariantType.TITLE)
        assert v.conversion_rate == 0.0

    def test_revenue_per_click(self):
        v = Variant(id="a", name="test", variant_type=VariantType.TITLE,
                    clicks=100, revenue=500)
        assert v.revenue_per_click == 5.0

    def test_revenue_per_click_zero(self):
        v = Variant(id="a", name="test", variant_type=VariantType.TITLE)
        assert v.revenue_per_click == 0.0


# ── Variant ID ──

class TestVariantId:
    def test_deterministic(self):
        assert variant_id("hello") == variant_id("hello")

    def test_different_content(self):
        assert variant_id("hello") != variant_id("world")

    def test_length(self):
        assert len(variant_id("test")) == 8


# ── Chi-Square Test ──

class TestChiSquare:
    def test_identical_rates(self):
        chi2, p = chi_square_test(50, 1000, 50, 1000)
        assert p > 0.05  # Not significant

    def test_very_different_rates(self):
        chi2, p = chi_square_test(10, 1000, 100, 1000)
        assert p < 0.05  # Significant

    def test_zero_total(self):
        chi2, p = chi_square_test(0, 0, 0, 0)
        assert p == 1.0

    def test_zero_conversions(self):
        chi2, p = chi_square_test(0, 100, 0, 100)
        assert p == 1.0


# ── Significance ──

class TestSignificance:
    def test_significant_difference(self):
        control = Variant(id="c", name="control", variant_type=VariantType.TITLE,
                         clicks=1000, conversions=50)
        variant = Variant(id="v", name="variant", variant_type=VariantType.TITLE,
                         clicks=1000, conversions=100)
        assert is_significant(control, variant)

    def test_not_significant(self):
        control = Variant(id="c", name="control", variant_type=VariantType.TITLE,
                         clicks=100, conversions=5)
        variant = Variant(id="v", name="variant", variant_type=VariantType.TITLE,
                         clicks=100, conversions=6)
        assert not is_significant(control, variant)


# ── Lift Calculation ──

class TestLift:
    def test_positive_lift(self):
        control = Variant(id="c", name="c", variant_type=VariantType.TITLE,
                         clicks=100, conversions=5)
        variant = Variant(id="v", name="v", variant_type=VariantType.TITLE,
                         clicks=100, conversions=10)
        lift = calculate_lift(control, variant)
        assert lift == 100.0  # 100% lift

    def test_zero_baseline(self):
        control = Variant(id="c", name="c", variant_type=VariantType.TITLE,
                         clicks=0, conversions=0)
        variant = Variant(id="v", name="v", variant_type=VariantType.TITLE,
                         clicks=100, conversions=10)
        assert calculate_lift(control, variant) == 0.0


# ── Sample Size ──

class TestMinSampleSize:
    def test_reasonable_sample(self):
        n = min_sample_size(0.05, 0.1)
        assert n > 0
        assert n < 1_000_000

    def test_higher_baseline_smaller_sample(self):
        n1 = min_sample_size(0.02, 0.1)
        n2 = min_sample_size(0.10, 0.1)
        assert n2 < n1  # Higher baseline needs fewer samples

    def test_edge_cases(self):
        assert min_sample_size(0, 0.1) == 100
        assert min_sample_size(1, 0.1) == 100


# ── Title Variants ──

class TestTitleVariants:
    def test_generates_variants(self):
        variants = generate_title_variants(
            "Wireless Bluetooth Headphones",
            keywords=["Headphones", "Wireless"],
            count=3,
        )
        assert len(variants) > 0
        assert all(isinstance(v, Variant) for v in variants)

    def test_keyword_first(self):
        variants = generate_title_variants(
            "Premium Wireless Headphones Bluetooth",
            keywords=["Bluetooth"],
        )
        kw_first = [v for v in variants if v.name == "keyword_first"]
        if kw_first:
            assert kw_first[0].content["title"].startswith("Bluetooth")

    def test_benefit_led(self):
        variants = generate_title_variants("Basic Headphones")
        benefit = [v for v in variants if v.name == "benefit_led"]
        assert len(benefit) > 0

    def test_concise_variant(self):
        variants = generate_title_variants(
            "The Best Wireless Bluetooth Headphones for the Active Lifestyle"
        )
        concise = [v for v in variants if v.name == "concise"]
        if concise:
            assert len(concise[0].content["title"]) < len(
                "The Best Wireless Bluetooth Headphones for the Active Lifestyle"
            )

    def test_hypotheses(self):
        variants = generate_title_variants("Test Product", keywords=["Test"])
        for v in variants:
            assert v.hypothesis  # Every variant has a hypothesis


# ── Bullet Variants ──

class TestBulletVariants:
    def test_generates_reversed(self):
        bullets = ["First point", "Second point", "Third point"]
        variants = generate_bullet_variants(bullets)
        assert len(variants) > 0
        reversed_v = [v for v in variants if v.name == "reversed_order"]
        assert len(reversed_v) == 1
        assert reversed_v[0].content["bullets"][0] == "Third point"

    def test_too_few_bullets(self):
        assert generate_bullet_variants(["Only one"]) == []

    def test_shuffled(self):
        bullets = ["A", "B", "C", "D", "E"]
        variants = generate_bullet_variants(bullets)
        shuffled = [v for v in variants if v.name == "shuffled"]
        assert len(shuffled) > 0


# ── ABTest ──

class TestABTest:
    def test_all_variants(self):
        control = Variant(id="c", name="control", variant_type=VariantType.TITLE)
        v1 = Variant(id="v1", name="variant1", variant_type=VariantType.TITLE)
        test = ABTest(test_id="t1", name="Test", control=control, variants=[v1])
        assert len(test.all_variants) == 2

    def test_winner_requires_completed(self):
        control = Variant(id="c", name="control", variant_type=VariantType.TITLE)
        test = ABTest(test_id="t1", name="Test", control=control,
                     status=TestStatus.RUNNING)
        assert test.winner() is None

    def test_winner_with_significant_result(self):
        control = Variant(id="c", name="control", variant_type=VariantType.TITLE,
                         clicks=1000, conversions=50)
        variant = Variant(id="v", name="variant", variant_type=VariantType.TITLE,
                         clicks=1000, conversions=100)
        test = ABTest(test_id="t1", name="Test", control=control,
                     variants=[variant], status=TestStatus.COMPLETED)
        winner = test.winner()
        assert winner is not None
        assert winner.name == "variant"

    def test_no_winner_when_no_variants(self):
        control = Variant(id="c", name="control", variant_type=VariantType.TITLE)
        test = ABTest(test_id="t1", name="Test", control=control,
                     status=TestStatus.COMPLETED)
        assert test.winner() is None


# ── Report ──

class TestReport:
    def test_report_generation(self):
        control = Variant(id="c", name="control", variant_type=VariantType.TITLE,
                         impressions=10000, clicks=500, conversions=25, revenue=1250)
        variant = Variant(id="v", name="keyword_first", variant_type=VariantType.TITLE,
                         impressions=10000, clicks=600, conversions=36, revenue=1800)
        test = ABTest(test_id="t1", name="Title Test", control=control,
                     variants=[variant], status=TestStatus.COMPLETED)
        report = generate_report(test)
        assert "Title Test" in report
        assert "control" in report
        assert "keyword_first" in report
