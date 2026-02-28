"""A/B Test Variant Generator for Product Listings.

Generate multiple listing variants for split testing with
data-driven hypothesis tracking and statistical significance helpers.

Features:
- Title variant generation (word reordering, keyword emphasis)
- Bullet point reordering and rephrasing
- Description structure variation (features-first vs benefits-first)
- Hypothesis tagging per variant
- Statistical significance calculator (chi-square)
- Test result tracker with winner detection
"""
import re
import math
import random
import hashlib
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class VariantType(str, Enum):
    TITLE = "title"
    BULLETS = "bullets"
    DESCRIPTION = "description"
    PRICE = "price"
    IMAGE_ORDER = "image_order"
    FULL_LISTING = "full_listing"


class TestStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Variant:
    """A single test variant."""
    id: str
    name: str
    variant_type: VariantType
    content: dict = field(default_factory=dict)
    hypothesis: str = ""
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0

    @property
    def ctr(self) -> float:
        return (self.clicks / self.impressions * 100) if self.impressions > 0 else 0.0

    @property
    def conversion_rate(self) -> float:
        return (self.conversions / self.clicks * 100) if self.clicks > 0 else 0.0

    @property
    def revenue_per_click(self) -> float:
        return self.revenue / self.clicks if self.clicks > 0 else 0.0


@dataclass
class ABTest:
    """An A/B test with control and variants."""
    test_id: str
    name: str
    control: Variant
    variants: list[Variant] = field(default_factory=list)
    status: TestStatus = TestStatus.DRAFT
    min_sample_size: int = 100
    confidence_level: float = 0.95

    @property
    def all_variants(self) -> list[Variant]:
        return [self.control] + self.variants

    def winner(self) -> Optional[Variant]:
        """Determine winner based on conversion rate with significance check."""
        if self.status != TestStatus.COMPLETED:
            return None
        if not self.variants:
            return None

        best = self.control
        for v in self.variants:
            if v.conversion_rate > best.conversion_rate:
                if is_significant(best, v, self.confidence_level):
                    best = v
        return best if best != self.control else None


@dataclass
class TestResult:
    """Statistical test result."""
    is_significant: bool
    p_value: float
    confidence: float
    lift: float  # Percentage improvement
    winner: str
    sample_sizes: dict = field(default_factory=dict)


def variant_id(content: str) -> str:
    """Generate a deterministic variant ID from content."""
    return hashlib.md5(content.encode()).hexdigest()[:8]


def chi_square_test(control_conv: int, control_total: int,
                    variant_conv: int, variant_total: int) -> tuple[float, float]:
    """Simple chi-square test for two proportions.

    Returns (chi_square_statistic, p_value_approximation).
    """
    if control_total == 0 or variant_total == 0:
        return 0.0, 1.0

    total = control_total + variant_total
    total_conv = control_conv + variant_conv
    total_no_conv = total - total_conv

    if total_conv == 0 or total_no_conv == 0:
        return 0.0, 1.0

    # Expected values
    e_cc = control_total * total_conv / total
    e_cn = control_total * total_no_conv / total
    e_vc = variant_total * total_conv / total
    e_vn = variant_total * total_no_conv / total

    # Chi-square statistic
    chi2 = 0.0
    for observed, expected in [
        (control_conv, e_cc), (control_total - control_conv, e_cn),
        (variant_conv, e_vc), (variant_total - variant_conv, e_vn),
    ]:
        if expected > 0:
            chi2 += (observed - expected) ** 2 / expected

    # Approximate p-value using survival function approximation (1 DOF)
    # P(X > chi2) ≈ erfc(sqrt(chi2/2)) for chi-square with 1 DOF
    p_value = math.erfc(math.sqrt(chi2 / 2))
    return chi2, p_value


def is_significant(control: Variant, variant: Variant,
                   confidence: float = 0.95) -> bool:
    """Check if variant is statistically significantly different from control."""
    _, p_value = chi_square_test(
        control.conversions, control.clicks,
        variant.conversions, variant.clicks,
    )
    return p_value < (1 - confidence)


def calculate_lift(control: Variant, variant: Variant) -> float:
    """Calculate percentage lift of variant over control."""
    if control.conversion_rate == 0:
        return 0.0
    return ((variant.conversion_rate - control.conversion_rate) /
            control.conversion_rate * 100)


def min_sample_size(baseline_rate: float, min_detectable_effect: float = 0.1,
                    power: float = 0.8, alpha: float = 0.05) -> int:
    """Calculate minimum sample size per variant for an A/B test.

    Args:
        baseline_rate: Current conversion rate (e.g. 0.05 for 5%)
        min_detectable_effect: Relative MDE (e.g. 0.1 for 10% lift)
        power: Statistical power (default 0.8)
        alpha: Significance level (default 0.05)
    """
    if baseline_rate <= 0 or baseline_rate >= 1:
        return 100
    p1 = baseline_rate
    p2 = p1 * (1 + min_detectable_effect)
    if p2 >= 1:
        p2 = 0.99

    # Normal approximation
    z_alpha = 1.96 if alpha == 0.05 else 2.576  # 95% or 99%
    z_beta = 0.84 if power == 0.8 else 1.28  # 80% or 90%

    p_avg = (p1 + p2) / 2
    numerator = (z_alpha * math.sqrt(2 * p_avg * (1 - p_avg)) +
                 z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    denominator = (p2 - p1) ** 2

    return max(100, math.ceil(numerator / denominator))


# ── Title Variant Generators ──

def generate_title_variants(title: str, keywords: list[str] = None,
                            count: int = 3) -> list[Variant]:
    """Generate title variants for A/B testing."""
    variants = []
    words = title.split()

    # Variant 1: Keyword-first reorder
    if keywords:
        kw_first = title
        for kw in keywords[:2]:
            if kw.lower() in title.lower() and not title.lower().startswith(kw.lower()):
                pattern = re.compile(re.escape(kw), re.IGNORECASE)
                kw_first = pattern.sub("", kw_first).strip()
                kw_first = f"{kw} {kw_first}"
                break
        if kw_first != title:
            variants.append(Variant(
                id=variant_id(kw_first),
                name="keyword_first",
                variant_type=VariantType.TITLE,
                content={"title": kw_first},
                hypothesis="Leading with primary keyword improves search ranking CTR",
            ))

    # Variant 2: Benefit-led title
    benefit_words = ["Premium", "Professional", "Ultra", "Advanced", "High-Quality"]
    for bw in benefit_words:
        if bw.lower() not in title.lower():
            benefit_title = f"{bw} {title}"
            if len(benefit_title) <= 200:
                variants.append(Variant(
                    id=variant_id(benefit_title),
                    name="benefit_led",
                    variant_type=VariantType.TITLE,
                    content={"title": benefit_title},
                    hypothesis="Adding quality qualifier increases perceived value and CTR",
                ))
                break

    # Variant 3: Concise title (remove filler words)
    filler = {"the", "a", "an", "and", "or", "for", "with", "in", "on", "at"}
    concise = " ".join(w for w in words if w.lower() not in filler)
    if concise != title and len(concise) >= 20:
        variants.append(Variant(
            id=variant_id(concise),
            name="concise",
            variant_type=VariantType.TITLE,
            content={"title": concise},
            hypothesis="Shorter titles with key terms only improve scan-ability",
        ))

    return variants[:count]


def generate_bullet_variants(bullets: list[str], count: int = 2) -> list[Variant]:
    """Generate bullet point order variants."""
    if len(bullets) < 2:
        return []

    variants = []

    # Variant 1: Reverse order (benefits first if features were first)
    reversed_bullets = list(reversed(bullets))
    variants.append(Variant(
        id=variant_id(str(reversed_bullets)),
        name="reversed_order",
        variant_type=VariantType.BULLETS,
        content={"bullets": reversed_bullets},
        hypothesis="Reordering bullets with most compelling point first increases engagement",
    ))

    # Variant 2: Shuffle with seed for reproducibility
    if len(bullets) >= 3:
        shuffled = bullets[:]
        rng = random.Random(42)
        rng.shuffle(shuffled)
        if shuffled != bullets:
            variants.append(Variant(
                id=variant_id(str(shuffled)),
                name="shuffled",
                variant_type=VariantType.BULLETS,
                content={"bullets": shuffled},
                hypothesis="Different bullet order may surface overlooked features",
            ))

    return variants[:count]


def generate_report(test: ABTest) -> str:
    """Generate a human-readable test report."""
    lines = [
        f"A/B Test: {test.name}",
        f"Status: {test.status.value}",
        f"Confidence: {test.confidence_level*100:.0f}%",
        "",
        f"{'Variant':<20} {'Impressions':>12} {'Clicks':>8} {'CTR':>8} {'Conv':>6} {'CVR':>8} {'Rev':>10}",
        "-" * 80,
    ]

    for v in test.all_variants:
        label = f"[C] {v.name}" if v == test.control else f"    {v.name}"
        lines.append(
            f"{label:<20} {v.impressions:>12,} {v.clicks:>8,} "
            f"{v.ctr:>7.2f}% {v.conversions:>6,} "
            f"{v.conversion_rate:>7.2f}% ${v.revenue:>9,.2f}"
        )

    # Winner
    winner = test.winner()
    if winner:
        lift = calculate_lift(test.control, winner)
        lines.append(f"\n🏆 Winner: {winner.name} (+{lift:.1f}% lift)")
    elif test.status == TestStatus.COMPLETED:
        lines.append("\nNo statistically significant winner found.")

    return "\n".join(lines)
