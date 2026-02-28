"""Tests for A/B testing variant generator."""
import pytest
from unittest.mock import patch, MagicMock
from app.ab_testing import (
    VariantAngle,
    Variant,
    ABTestPlan,
    generate_variant,
    generate_ab_plan,
    compare_variants,
    ANGLE_PROMPTS,
    _select_angles,
    _generate_recommendations,
)


# ── VariantAngle Constants ──────────────────────────────────

class TestVariantAngles:
    def test_all_angles_defined(self):
        assert len(VariantAngle.ALL) == 8

    def test_all_angles_have_prompts(self):
        for angle in VariantAngle.ALL:
            assert angle in ANGLE_PROMPTS, f"Missing prompt for {angle}"

    def test_angle_values(self):
        assert VariantAngle.BENEFIT_FOCUSED == "benefit"
        assert VariantAngle.STORYTELLING == "storytelling"
        assert VariantAngle.MINIMALIST == "minimalist"


# ── Angle Selection ─────────────────────────────────────────

class TestAngleSelection:
    def test_amazon_priorities(self):
        angles = _select_angles("amazon", 3)
        assert len(angles) == 3
        assert VariantAngle.BENEFIT_FOCUSED in angles

    def test_tiktok_priorities(self):
        angles = _select_angles("tiktok", 3)
        assert len(angles) == 3
        assert VariantAngle.STORYTELLING in angles

    def test_shopee_priorities(self):
        angles = _select_angles("shopee", 2)
        assert len(angles) == 2

    def test_unknown_platform_fallback(self):
        angles = _select_angles("unknown", 3)
        assert len(angles) == 3

    def test_count_respected(self):
        angles = _select_angles("amazon", 1)
        assert len(angles) == 1


# ── Variant Data Class ──────────────────────────────────────

class TestVariantDataClass:
    def test_variant_creation(self):
        v = Variant(
            angle="benefit",
            title="Test Title",
            listing="Test listing content",
            hypothesis="Benefits resonate with buyers",
        )
        assert v.angle == "benefit"
        assert v.title == "Test Title"


# ── ABTestPlan ──────────────────────────────────────────────

class TestABTestPlan:
    def test_plan_summary(self):
        plan = ABTestPlan(
            product="Headphones",
            platform="amazon",
            variants=[
                Variant("benefit", "Title A", "Listing A...", "Hypothesis A"),
                Variant("feature", "Title B", "Listing B...", "Hypothesis B"),
            ],
            recommendations="Test for 7 days",
        )
        summary = plan.summary()
        assert "Headphones" in summary
        assert "Variant 1" in summary
        assert "Variant 2" in summary
        assert "BENEFIT" in summary
        assert "Recommendations" in summary

    def test_empty_plan(self):
        plan = ABTestPlan(product="Test", platform="amazon")
        summary = plan.summary()
        assert "Variants: 0" in summary


# ── Generate Variant (with mock AI) ────────────────────────

class TestGenerateVariant:
    @patch("app.ab_testing.call_ai")
    def test_generates_variant(self, mock_ai):
        mock_ai.return_value = """Premium Wireless Headphones - Ultimate Sound
**Bullet Points** Amazing sound quality
More listing content here
HYPOTHESIS: Benefit-focused approach appeals to value-conscious buyers"""

        variant = generate_variant("Headphones", "amazon", "benefit")
        assert isinstance(variant, Variant)
        assert variant.angle == "benefit"
        assert variant.title != ""
        assert "value-conscious" in variant.hypothesis.lower() or len(variant.hypothesis) > 0

    @patch("app.ab_testing.call_ai")
    def test_missing_hypothesis_gets_default(self, mock_ai):
        mock_ai.return_value = "Simple Title\nSimple listing without hypothesis"

        variant = generate_variant("Product", "amazon", "benefit")
        assert variant.hypothesis != ""  # Should have a default

    @patch("app.ab_testing.call_ai")
    def test_chinese_language(self, mock_ai):
        mock_ai.return_value = "蓝牙耳机标题\n产品描述内容\nHYPOTHESIS: 中文卖点更吸引"

        variant = generate_variant("蓝牙耳机", "shopee", "urgency", "中文")
        assert isinstance(variant, Variant)
        mock_ai.assert_called_once()


# ── Generate AB Plan ────────────────────────────────────────

class TestGenerateABPlan:
    @patch("app.ab_testing.call_ai")
    def test_generates_plan(self, mock_ai):
        mock_ai.return_value = "Title\nListing content\nHYPOTHESIS: Test hypothesis"

        plan = generate_ab_plan("Headphones", "amazon", num_variants=2)
        assert isinstance(plan, ABTestPlan)
        assert len(plan.variants) == 2
        assert plan.recommendations != ""

    @patch("app.ab_testing.call_ai")
    def test_custom_angles(self, mock_ai):
        mock_ai.return_value = "Title\nContent\nHYPOTHESIS: Test"

        plan = generate_ab_plan(
            "Headphones", "amazon",
            angles=["benefit", "urgency"],
            num_variants=2,
        )
        assert len(plan.variants) == 2
        assert plan.variants[0].angle == "benefit"
        assert plan.variants[1].angle == "urgency"

    @patch("app.ab_testing.call_ai")
    def test_clamps_variant_count(self, mock_ai):
        mock_ai.return_value = "Title\nContent\nHYPOTHESIS: Test"

        plan = generate_ab_plan("Test", "amazon", num_variants=1)  # min is 2
        assert len(plan.variants) == 2

        plan = generate_ab_plan("Test", "amazon", num_variants=10)  # max is 8
        assert len(plan.variants) == 8


# ── Recommendations ─────────────────────────────────────────

class TestRecommendations:
    def test_basic_recommendations(self):
        plan = ABTestPlan(
            product="Test", platform="amazon",
            variants=[Variant("a", "t", "l", "h"), Variant("b", "t", "l", "h")],
        )
        recs = _generate_recommendations(plan)
        assert "7 days" in recs
        assert "conversion" in recs.lower()

    def test_many_variants_sequential_advice(self):
        variants = [Variant(f"a{i}", "t", "l", "h") for i in range(5)]
        plan = ABTestPlan(product="Test", platform="amazon", variants=variants)
        recs = _generate_recommendations(plan)
        assert "sequential" in recs.lower()


# ── Compare Variants ────────────────────────────────────────

class TestCompareVariants:
    def test_needs_two_variants(self):
        result = compare_variants([Variant("a", "t", "l", "h")])
        assert "Need at least 2" in result

    @patch("app.ab_testing.call_ai")
    def test_comparison_calls_ai(self, mock_ai):
        mock_ai.return_value = "Variant 1 wins for CTR..."
        variants = [
            Variant("benefit", "Title A", "Listing A" * 100, "H1"),
            Variant("feature", "Title B", "Listing B" * 100, "H2"),
        ]
        result = compare_variants(variants)
        assert mock_ai.called
        assert isinstance(result, str)
