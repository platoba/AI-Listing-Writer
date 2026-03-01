"""
Return Rate Estimator
=====================

Estimate potential return rates based on listing quality signals.
Analyzes title clarity, specification completeness, image coverage,
sizing info, material descriptions, and expectation-setting language
to predict if a listing will lead to returns.

High return rates eat profits — this module catches common listing
quality issues that correlate with buyer dissatisfaction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ReturnRisk(str, Enum):
    LOW = "low"           # < 3% estimated
    MODERATE = "moderate"  # 3-8%
    HIGH = "high"         # 8-15%
    CRITICAL = "critical"  # 15%+


@dataclass
class ReturnFactor:
    """Individual factor contributing to return risk."""
    name: str
    risk_level: ReturnRisk
    score: float          # 0-100 (higher = worse / more risky)
    weight: float
    detail: str = ""
    fix: str = ""


@dataclass
class ReturnEstimate:
    """Full return rate estimation result."""
    estimated_rate: float          # 0-100 percentage
    risk_level: ReturnRisk
    factors: list[ReturnFactor] = field(default_factory=list)
    category_baseline: float = 0.0  # baseline return rate for category
    delta_from_baseline: float = 0.0
    top_risks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ── Category baselines (industry averages) ───────────────────

CATEGORY_BASELINES = {
    "clothing": 15.0,
    "shoes": 18.0,
    "electronics": 8.0,
    "home": 6.0,
    "kitchen": 7.0,
    "beauty": 5.0,
    "toys": 4.0,
    "sports": 7.0,
    "outdoor": 6.0,
    "pet": 5.0,
    "office": 4.0,
    "automotive": 8.0,
    "jewelry": 12.0,
    "furniture": 10.0,
    "default": 8.0,
}

# ── Risk patterns ────────────────────────────────────────────

SIZING_KEYWORDS = {
    "size", "sizing", "dimensions", "measurement", "fit", "fits",
    "length", "width", "height", "diameter", "inches", "cm", "mm",
    "small", "medium", "large", "xl", "xxl", "one size",
}

MATERIAL_KEYWORDS = {
    "material", "made of", "fabric", "cotton", "polyester", "nylon",
    "leather", "stainless steel", "aluminum", "plastic", "silicone",
    "wood", "bamboo", "ceramic", "glass", "rubber", "metal",
}

EXPECTATION_SETTERS = {
    "please note", "important", "attention", "notice", "disclaimer",
    "may vary", "slight difference", "actual color", "monitor",
    "manual measurement", "1-3cm", "tolerance",
}

VAGUE_WORDS = {
    "high quality", "best quality", "top quality", "luxury",
    "amazing", "incredible", "fantastic", "awesome", "perfect",
    "beautiful", "gorgeous", "stunning", "elegant",
}


class ReturnRateEstimator:
    """Estimate return rates based on listing quality analysis."""

    def __init__(self, category: str = "default"):
        self.category = category.lower()
        self.baseline = CATEGORY_BASELINES.get(self.category, CATEGORY_BASELINES["default"])

    def estimate(
        self,
        title: str,
        description: str = "",
        bullet_points: list[str] | None = None,
        has_size_chart: bool = False,
        image_count: int = 0,
        has_video: bool = False,
        price: float | None = None,
        rating: float | None = None,
        review_count: int = 0,
    ) -> ReturnEstimate:
        """Estimate return rate based on listing signals."""
        factors = []
        bullets = bullet_points or []
        text_all = f"{title} {description} {' '.join(bullets)}".lower()

        # 1. Specification completeness
        factors.append(self._check_specs(text_all))

        # 2. Size/dimension clarity
        factors.append(self._check_sizing(text_all, has_size_chart))

        # 3. Material description
        factors.append(self._check_materials(text_all))

        # 4. Image coverage
        factors.append(self._check_images(image_count, has_video))

        # 5. Expectation management
        factors.append(self._check_expectations(text_all))

        # 6. Vague/overpromise language
        factors.append(self._check_vagueness(text_all))

        # 7. Title clarity
        factors.append(self._check_title_clarity(title))

        # 8. Social proof signals
        factors.append(self._check_social_proof(rating, review_count))

        # 9. Price positioning
        factors.append(self._check_price_signal(price))

        # 10. Description completeness
        factors.append(self._check_description_quality(description, bullets))

        # Calculate weighted risk score
        total_risk = sum(f.score * f.weight for f in factors)
        total_risk = max(0.0, min(100.0, total_risk))

        # Map risk score to estimated return rate
        # Risk 0 → baseline * 0.5, Risk 100 → baseline * 3.0
        multiplier = 0.5 + (total_risk / 100) * 2.5
        estimated_rate = round(self.baseline * multiplier, 1)
        estimated_rate = min(estimated_rate, 40.0)  # cap at 40%

        risk_level = self._classify_risk(estimated_rate)
        delta = round(estimated_rate - self.baseline, 1)

        # Top risks and recommendations
        risky = sorted(factors, key=lambda f: -f.score)
        top_risks = [f"{f.name}: {f.detail}" for f in risky[:3] if f.score > 40]
        recommendations = [f.fix for f in risky[:5] if f.fix and f.score > 30]

        return ReturnEstimate(
            estimated_rate=estimated_rate,
            risk_level=risk_level,
            factors=factors,
            category_baseline=self.baseline,
            delta_from_baseline=delta,
            top_risks=top_risks,
            recommendations=recommendations,
        )

    # ── Factor Checkers ──────────────────────────────────────

    def _check_specs(self, text: str) -> ReturnFactor:
        spec_patterns = [
            r'(?:dimension|size|measure)',
            r'(?:weight|weighs|grams?|lbs?|kg)',
            r'(?:material|made of|fabric)',
            r'(?:color|colour)',
            r'(?:package|includes|comes with)',
            r'(?:voltage|wattage|power|battery)',
            r'(?:compatible|fits|works with)',
        ]
        found = sum(1 for p in spec_patterns if re.search(p, text))
        coverage = found / len(spec_patterns)

        if coverage >= 0.7:
            risk = 10
            detail = f"{found}/{len(spec_patterns)} spec types covered"
        elif coverage >= 0.4:
            risk = 40
            detail = f"Only {found}/{len(spec_patterns)} spec types"
        else:
            risk = 75
            detail = f"Missing most specifications ({found}/{len(spec_patterns)})"

        return ReturnFactor(
            "specification_completeness", self._risk_from_score(risk),
            risk, 0.18, detail,
            "Add complete product specifications — dimensions, weight, material, compatibility"
            if risk > 30 else ""
        )

    def _check_sizing(self, text: str, has_chart: bool) -> ReturnFactor:
        sizing_hits = sum(1 for kw in SIZING_KEYWORDS if kw in text)
        is_sized = self.category in ("clothing", "shoes", "jewelry")

        if is_sized:
            if has_chart and sizing_hits >= 3:
                risk = 10
                detail = "Size chart provided with detailed measurements"
            elif has_chart:
                risk = 25
                detail = "Size chart present but sizing details limited"
            elif sizing_hits >= 2:
                risk = 50
                detail = "Some sizing info but no size chart"
            else:
                risk = 85
                detail = "No sizing information for sized product"
            weight = 0.20
        else:
            if sizing_hits >= 2:
                risk = 5
                detail = "Dimensions provided"
            elif sizing_hits >= 1:
                risk = 25
                detail = "Minimal dimension info"
            else:
                risk = 45
                detail = "No dimension information"
            weight = 0.10

        return ReturnFactor(
            "sizing_clarity", self._risk_from_score(risk),
            risk, weight, detail,
            "Add a size chart and detailed measurements to reduce size-related returns"
            if risk > 30 else ""
        )

    def _check_materials(self, text: str) -> ReturnFactor:
        hits = sum(1 for kw in MATERIAL_KEYWORDS if kw in text)

        if hits >= 3:
            risk = 5
            detail = f"{hits} material descriptors"
        elif hits >= 1:
            risk = 30
            detail = f"Only {hits} material mention(s)"
        else:
            risk = 60
            detail = "No material information"

        return ReturnFactor(
            "material_description", self._risk_from_score(risk),
            risk, 0.12, detail,
            "Describe materials clearly — buyers return products that don't feel as expected"
            if risk > 30 else ""
        )

    def _check_images(self, count: int, has_video: bool) -> ReturnFactor:
        score_base = 0

        if count >= 7:
            score_base = 5
        elif count >= 5:
            score_base = 15
        elif count >= 3:
            score_base = 35
        elif count >= 1:
            score_base = 55
        else:
            score_base = 80

        if has_video:
            score_base = max(0, score_base - 15)

        detail = f"{count} images" + (" + video" if has_video else "")

        return ReturnFactor(
            "image_coverage", self._risk_from_score(score_base),
            score_base, 0.12, detail,
            "Add more product images from multiple angles — buyers return items that look different than expected"
            if score_base > 30 else ""
        )

    def _check_expectations(self, text: str) -> ReturnFactor:
        hits = sum(1 for kw in EXPECTATION_SETTERS if kw in text)

        # Having disclaimers is a double-edged sword:
        # Some is good (honest), too many = product has issues
        if 1 <= hits <= 3:
            risk = 15
            detail = f"{hits} expectation-setting notes (good)"
        elif hits == 0:
            risk = 40
            detail = "No expectation management"
        else:
            risk = 55
            detail = f"{hits} disclaimers (may indicate known issues)"

        return ReturnFactor(
            "expectation_management", self._risk_from_score(risk),
            risk, 0.08, detail,
            "Add clear 'please note' sections about color variation, sizing tolerance, etc."
            if risk > 30 else ""
        )

    def _check_vagueness(self, text: str) -> ReturnFactor:
        hits = sum(1 for vw in VAGUE_WORDS if vw in text)

        if hits == 0:
            risk = 5
            detail = "No vague/overpromise language"
        elif hits <= 2:
            risk = 25
            detail = f"{hits} vague claim(s)"
        else:
            risk = 60
            detail = f"{hits} vague/overpromise terms"

        return ReturnFactor(
            "vague_language", self._risk_from_score(risk),
            risk, 0.08, detail,
            "Replace vague claims ('high quality', 'amazing') with specific facts and measurements"
            if risk > 30 else ""
        )

    def _check_title_clarity(self, title: str) -> ReturnFactor:
        words = title.split()
        score = 0

        # Too short = ambiguous
        if len(words) < 4:
            score += 40

        # All caps = suspicious
        if title == title.upper() and len(title) > 10:
            score += 30

        # Keyword stuffing
        if len(words) > 25:
            score += 25

        # Contradictory signals (e.g. "cheap premium")
        if ("cheap" in title.lower() and "premium" in title.lower()):
            score += 35

        risk = min(score, 100)
        detail = f"{len(words)} words"

        return ReturnFactor(
            "title_clarity", self._risk_from_score(risk),
            risk, 0.06, detail,
            "Make title clear and descriptive — avoid keyword stuffing or contradictory claims"
            if risk > 30 else ""
        )

    def _check_social_proof(self, rating: float | None, review_count: int) -> ReturnFactor:
        if rating is None:
            return ReturnFactor(
                "social_proof", ReturnRisk.MODERATE,
                45, 0.08, "No rating data",
                "New listings without reviews have higher return risk — consider early reviewer programs"
            )

        if rating >= 4.3 and review_count >= 50:
            risk = 5
            detail = f"★{rating} ({review_count} reviews)"
        elif rating >= 4.0:
            risk = 20
            detail = f"★{rating} ({review_count} reviews)"
        elif rating >= 3.5:
            risk = 45
            detail = f"★{rating} — below average ({review_count} reviews)"
        else:
            risk = 75
            detail = f"★{rating} — poor rating ({review_count} reviews)"

        return ReturnFactor(
            "social_proof", self._risk_from_score(risk),
            risk, 0.08, detail,
            "Address common complaints in reviews to reduce return-triggering issues"
            if risk > 30 else ""
        )

    def _check_price_signal(self, price: float | None) -> ReturnFactor:
        if price is None:
            return ReturnFactor("price_signal", ReturnRisk.MODERATE, 40, 0.04, "No price data")

        # Very cheap items often have quality perception issues
        if price < 5:
            risk = 55
            detail = f"${price:.2f} — very low price may signal quality issues"
        elif price < 15:
            risk = 30
            detail = f"${price:.2f} — budget range"
        elif price > 200:
            risk = 35
            detail = f"${price:.2f} — high price = higher buyer expectations"
        else:
            risk = 15
            detail = f"${price:.2f} — standard range"

        return ReturnFactor(
            "price_signal", self._risk_from_score(risk),
            risk, 0.04, detail,
            "Ensure product quality matches price expectations"
            if risk > 30 else ""
        )

    def _check_description_quality(self, description: str, bullets: list[str]) -> ReturnFactor:
        word_count = len(description.split()) if description else 0
        bullet_count = len(bullets)
        total_info = word_count + sum(len(b.split()) for b in bullets)

        if total_info >= 200 and bullet_count >= 5:
            risk = 5
            detail = f"{total_info} words of product info"
        elif total_info >= 100:
            risk = 25
            detail = f"{total_info} words (could be more detailed)"
        elif total_info >= 50:
            risk = 45
            detail = f"Only {total_info} words of info"
        else:
            risk = 70
            detail = f"Minimal info ({total_info} words)"

        return ReturnFactor(
            "info_completeness", self._risk_from_score(risk),
            risk, 0.14, detail,
            "Add comprehensive product information — incomplete listings lead to wrong-expectation purchases"
            if risk > 30 else ""
        )

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _risk_from_score(score: float) -> ReturnRisk:
        if score < 20:
            return ReturnRisk.LOW
        elif score < 45:
            return ReturnRisk.MODERATE
        elif score < 70:
            return ReturnRisk.HIGH
        return ReturnRisk.CRITICAL

    @staticmethod
    def _classify_risk(rate: float) -> ReturnRisk:
        if rate < 3:
            return ReturnRisk.LOW
        elif rate < 8:
            return ReturnRisk.MODERATE
        elif rate < 15:
            return ReturnRisk.HIGH
        return ReturnRisk.CRITICAL

    # ── Report ───────────────────────────────────────────────

    def report(self, estimate: ReturnEstimate) -> str:
        """Generate human-readable return rate report."""
        lines = [
            f"📦 Return Rate Estimation",
            f"{'=' * 50}",
            f"Estimated Return Rate: {estimate.estimated_rate}% ({estimate.risk_level.value.upper()})",
            f"Category Baseline:     {estimate.category_baseline}%",
            f"Delta:                 {'+' if estimate.delta_from_baseline > 0 else ''}{estimate.delta_from_baseline}%",
            f"",
            f"Risk Factors:",
        ]

        for f in sorted(estimate.factors, key=lambda x: -x.score):
            icon = "🔴" if f.risk_level == ReturnRisk.CRITICAL else \
                   "🟠" if f.risk_level == ReturnRisk.HIGH else \
                   "🟡" if f.risk_level == ReturnRisk.MODERATE else "🟢"
            lines.append(f"  {icon} {f.name:28s} risk={f.score:5.1f}  {f.detail}")

        if estimate.recommendations:
            lines.append(f"\n💡 Recommendations:")
            for i, rec in enumerate(estimate.recommendations, 1):
                lines.append(f"  {i}. {rec}")

        return "\n".join(lines)


# ── Module-level convenience ─────────────────────────────────

def estimate_returns(title: str, category: str = "default", **kwargs) -> ReturnEstimate:
    """Quick return rate estimation."""
    estimator = ReturnRateEstimator(category)
    return estimator.estimate(title=title, **kwargs)
