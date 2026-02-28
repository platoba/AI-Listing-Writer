"""A/B testing variant generator.

Generates multiple listing variants with different angles, tones,
and structures for split testing and conversion optimization.
"""
import re
import json
from dataclasses import dataclass, field
from typing import Optional

from app.ai_engine import call_ai


class VariantAngle:
    """Predefined angles for variant generation."""
    BENEFIT_FOCUSED = "benefit"
    FEATURE_FOCUSED = "feature"
    PROBLEM_SOLUTION = "problem_solution"
    STORYTELLING = "storytelling"
    SOCIAL_PROOF = "social_proof"
    URGENCY = "urgency"
    COMPARISON = "comparison"
    MINIMALIST = "minimalist"

    ALL = [
        BENEFIT_FOCUSED,
        FEATURE_FOCUSED,
        PROBLEM_SOLUTION,
        STORYTELLING,
        SOCIAL_PROOF,
        URGENCY,
        COMPARISON,
        MINIMALIST,
    ]


ANGLE_PROMPTS = {
    VariantAngle.BENEFIT_FOCUSED: (
        "Focus on customer BENEFITS. Every sentence should answer "
        "'What's in it for me?' Lead with outcomes, not features."
    ),
    VariantAngle.FEATURE_FOCUSED: (
        "Focus on FEATURES and SPECIFICATIONS. Be technical and detailed. "
        "Include exact measurements, materials, and capabilities."
    ),
    VariantAngle.PROBLEM_SOLUTION: (
        "Use PROBLEM → SOLUTION structure. Start with the customer's pain point, "
        "then show how this product solves it perfectly."
    ),
    VariantAngle.STORYTELLING: (
        "Use STORYTELLING approach. Paint a picture of life with this product. "
        "Create a mini narrative that resonates emotionally."
    ),
    VariantAngle.SOCIAL_PROOF: (
        "Lead with SOCIAL PROOF. Reference reviews, ratings, awards, "
        "'trusted by X customers', expert endorsements, media mentions."
    ),
    VariantAngle.URGENCY: (
        "Create URGENCY. Use time-sensitive language, limited availability, "
        "seasonal relevance, trending status. Make them act NOW."
    ),
    VariantAngle.COMPARISON: (
        "Use COMPARISON approach. Position against competitors (without naming them). "
        "Show why this is the better/smarter choice."
    ),
    VariantAngle.MINIMALIST: (
        "Use MINIMALIST style. Short sentences. Bold claims. "
        "White space. Let the product speak for itself."
    ),
}


@dataclass
class Variant:
    angle: str
    title: str
    listing: str
    hypothesis: str  # Why this variant might win


@dataclass
class ABTestPlan:
    product: str
    platform: str
    variants: list[Variant] = field(default_factory=list)
    recommendations: str = ""

    def summary(self) -> str:
        lines = [
            f"🔬 A/B Test Plan: {self.product}",
            f"   Platform: {self.platform}",
            f"   Variants: {len(self.variants)}",
            "",
        ]
        for i, v in enumerate(self.variants, 1):
            lines.append(f"--- Variant {i}: {v.angle.upper()} ---")
            lines.append(f"📝 Title: {v.title}")
            lines.append(f"💡 Hypothesis: {v.hypothesis}")
            lines.append(f"📄 Preview: {v.listing[:200]}...")
            lines.append("")
        if self.recommendations:
            lines.append("📊 Recommendations:")
            lines.append(self.recommendations)
        return "\n".join(lines)


def generate_variant(
    product: str,
    platform: str,
    angle: str,
    language: str = "English",
) -> Variant:
    """Generate a single listing variant with a specific angle.

    Args:
        product: Product name/description.
        platform: Target platform.
        angle: One of VariantAngle constants.
        language: Output language.

    Returns:
        Variant with listing text and hypothesis.
    """
    angle_instruction = ANGLE_PROMPTS.get(angle, ANGLE_PROMPTS[VariantAngle.BENEFIT_FOCUSED])

    prompt = f"""Generate a product listing variant for A/B testing.

Product: {product}
Platform: {platform}
Language: {language}
Angle: {angle.upper()}

ANGLE INSTRUCTION: {angle_instruction}

Output format:
1. First line: The listing TITLE only
2. Then the full listing (following {platform} format)
3. Last paragraph: "HYPOTHESIS: [Why this variant might convert better]"

Make it genuinely different from a standard listing — not just rephrased."""

    result = call_ai(prompt)

    # Parse result
    lines = result.strip().split("\n")
    title = lines[0].strip() if lines else product

    # Extract hypothesis
    hypothesis = ""
    listing_lines = []
    for line in lines[1:]:
        if line.strip().upper().startswith("HYPOTHESIS:"):
            hypothesis = line.split(":", 1)[1].strip() if ":" in line else line
        else:
            listing_lines.append(line)

    if not hypothesis:
        hypothesis = f"The {angle} approach may resonate with {platform} shoppers"

    return Variant(
        angle=angle,
        title=title,
        listing="\n".join(listing_lines).strip(),
        hypothesis=hypothesis,
    )


def generate_ab_plan(
    product: str,
    platform: str,
    angles: Optional[list[str]] = None,
    num_variants: int = 3,
    language: str = "English",
) -> ABTestPlan:
    """Generate a complete A/B test plan with multiple variants.

    Args:
        product: Product name/description.
        platform: Target platform.
        angles: Specific angles to use (or auto-select).
        num_variants: Number of variants (2-8).
        language: Output language.

    Returns:
        ABTestPlan with variants and recommendations.
    """
    num_variants = max(2, min(8, num_variants))

    if angles:
        selected_angles = angles[:num_variants]
    else:
        # Auto-select best angles for the platform
        selected_angles = _select_angles(platform, num_variants)

    plan = ABTestPlan(product=product, platform=platform)

    for angle in selected_angles:
        variant = generate_variant(product, platform, angle, language)
        plan.variants.append(variant)

    # Generate test recommendations
    plan.recommendations = _generate_recommendations(plan)

    return plan


def _select_angles(platform: str, count: int) -> list[str]:
    """Select best angles for a platform."""
    platform_priorities = {
        "amazon": [
            VariantAngle.BENEFIT_FOCUSED,
            VariantAngle.FEATURE_FOCUSED,
            VariantAngle.SOCIAL_PROOF,
            VariantAngle.PROBLEM_SOLUTION,
        ],
        "shopee": [
            VariantAngle.URGENCY,
            VariantAngle.SOCIAL_PROOF,
            VariantAngle.BENEFIT_FOCUSED,
            VariantAngle.MINIMALIST,
        ],
        "tiktok": [
            VariantAngle.STORYTELLING,
            VariantAngle.URGENCY,
            VariantAngle.SOCIAL_PROOF,
            VariantAngle.MINIMALIST,
        ],
        "ebay": [
            VariantAngle.FEATURE_FOCUSED,
            VariantAngle.COMPARISON,
            VariantAngle.BENEFIT_FOCUSED,
            VariantAngle.SOCIAL_PROOF,
        ],
        "独立站": [
            VariantAngle.STORYTELLING,
            VariantAngle.BENEFIT_FOCUSED,
            VariantAngle.SOCIAL_PROOF,
            VariantAngle.MINIMALIST,
        ],
    }
    angles = platform_priorities.get(platform.lower(), VariantAngle.ALL[:count])
    # If platform list is shorter than requested, fill from ALL angles
    if len(angles) < count:
        remaining = [a for a in VariantAngle.ALL if a not in angles]
        angles = angles + remaining[:count - len(angles)]
    return angles[:count]


def _generate_recommendations(plan: ABTestPlan) -> str:
    """Generate test execution recommendations."""
    lines = [
        f"1. Run each variant for minimum 7 days or 1000 impressions",
        f"2. Measure: CTR, conversion rate, and average order value",
        f"3. Statistical significance threshold: 95% confidence",
        f"4. Test one element at a time when possible",
        f"5. Primary metric: conversion rate",
    ]
    if len(plan.variants) > 3:
        lines.append("6. Consider sequential testing (champion vs challenger)")
    return "\n".join(lines)


def compare_variants(variants: list[Variant]) -> str:
    """Generate a comparison analysis of variants."""
    if len(variants) < 2:
        return "Need at least 2 variants to compare."

    prompt = f"""Compare these {len(variants)} listing variants and analyze:
1. Which is likely to have the HIGHEST click-through rate (CTR)?
2. Which is likely to have the HIGHEST conversion rate?
3. What audience segment would each appeal to?
4. Rank them overall with brief reasoning.

"""
    for i, v in enumerate(variants, 1):
        prompt += f"\n--- Variant {i} ({v.angle}) ---\n{v.listing[:500]}\n"

    return call_ai(prompt)
