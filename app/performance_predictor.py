"""
Listing Performance Predictor
=============================

Predict listing performance (CTR, conversion, visibility) by analyzing
title quality, keyword density, image signals, pricing, and competitive
factors.  Returns a composite score with per-dimension breakdown and
actionable improvement suggestions.

No external ML model required — uses a deterministic rule-engine weighted
across 12 quality signals, calibrated against marketplace best practices.
"""

from __future__ import annotations

import re
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Models ───────────────────────────────────────────────────

class PerformanceTier(str, Enum):
    EXCELLENT = "excellent"  # 85-100
    GOOD = "good"            # 70-84
    AVERAGE = "average"      # 50-69
    POOR = "poor"            # 30-49
    CRITICAL = "critical"    # 0-29


@dataclass
class SignalScore:
    """Score for a single quality signal."""
    name: str
    score: float          # 0-100
    weight: float         # relative weight
    detail: str = ""
    suggestions: list[str] = field(default_factory=list)


@dataclass
class PerformancePrediction:
    """Full performance prediction result."""
    overall_score: float          # 0-100
    tier: PerformanceTier
    ctr_estimate: str             # qualitative: "high" / "average" / "low"
    conversion_estimate: str
    visibility_estimate: str
    signals: list[SignalScore] = field(default_factory=list)
    top_improvements: list[str] = field(default_factory=list)
    competitive_position: str = ""  # "above average" / "average" / "below average"


# ── Signal Weights ───────────────────────────────────────────

SIGNAL_WEIGHTS = {
    "title_quality":       0.18,
    "keyword_coverage":    0.15,
    "description_depth":   0.12,
    "bullet_points":       0.10,
    "price_competitiveness": 0.10,
    "image_signals":       0.08,
    "brand_presence":      0.06,
    "mobile_readability":  0.06,
    "search_term_usage":   0.05,
    "feature_completeness": 0.04,
    "title_length_fit":    0.03,
    "special_characters":  0.03,
}

# ── Platform-specific ideal title lengths ────────────────────

IDEAL_TITLE_LENGTH = {
    "amazon": (80, 200),
    "ebay": (60, 80),
    "walmart": (50, 75),
    "shopee": (60, 120),
    "etsy": (60, 140),
    "aliexpress": (80, 128),
    "default": (60, 150),
}

# ── Power words that boost CTR ──────────────────────────────

POWER_WORDS = {
    "premium", "professional", "upgraded", "2024", "2025", "2026",
    "new", "latest", "advanced", "ultra", "pro", "heavy duty",
    "waterproof", "portable", "wireless", "rechargeable", "adjustable",
    "lightweight", "durable", "compact", "foldable", "multi-purpose",
    "eco-friendly", "organic", "natural", "bpa free", "non-toxic",
    "gift", "bundle", "set", "kit", "pack", "with", "includes",
}

# ── Spam / penalty patterns ─────────────────────────────────

SPAM_PATTERNS = [
    r'\b(buy|cheap|best|free shipping|limited time)\b',
    r'[!]{2,}',
    r'[A-Z]{5,}',  # excessive caps
    r'[★☆✓✔✗✘♥♡]{3,}',  # emoji spam
    r'(\b\w+\b)(\s+\1){2,}',  # word repetition
]


class PerformancePredictor:
    """Predict listing performance based on multi-signal analysis."""

    def __init__(self, platform: str = "amazon"):
        self.platform = platform.lower()
        self._weights = dict(SIGNAL_WEIGHTS)

    def predict(
        self,
        title: str,
        description: str = "",
        bullet_points: list[str] | None = None,
        keywords: list[str] | None = None,
        price: float | None = None,
        competitor_prices: list[float] | None = None,
        image_count: int = 0,
        brand: str = "",
        backend_keywords: str = "",
    ) -> PerformancePrediction:
        """Run full performance prediction."""
        signals = []
        bullets = bullet_points or []
        kws = [k.lower() for k in (keywords or [])]
        text_all = f"{title} {description} {' '.join(bullets)}".lower()

        # 1. Title quality
        signals.append(self._score_title_quality(title))

        # 2. Keyword coverage
        signals.append(self._score_keyword_coverage(kws, text_all, title.lower()))

        # 3. Description depth
        signals.append(self._score_description(description))

        # 4. Bullet points
        signals.append(self._score_bullets(bullets))

        # 5. Price competitiveness
        signals.append(self._score_price(price, competitor_prices))

        # 6. Image signals
        signals.append(self._score_images(image_count))

        # 7. Brand presence
        signals.append(self._score_brand(brand, title))

        # 8. Mobile readability
        signals.append(self._score_mobile(title, bullets))

        # 9. Search term / backend keyword usage
        signals.append(self._score_search_terms(backend_keywords, kws))

        # 10. Feature completeness
        signals.append(self._score_features(text_all))

        # 11. Title length fit
        signals.append(self._score_title_length(title))

        # 12. Special character / spam check
        signals.append(self._score_spam(title, description))

        # Weighted aggregate
        overall = sum(s.score * s.weight for s in signals)
        overall = max(0.0, min(100.0, overall))

        tier = self._classify_tier(overall)
        ctr = "high" if overall >= 75 else ("average" if overall >= 50 else "low")
        conv = "high" if overall >= 80 else ("average" if overall >= 55 else "low")
        vis = "high" if overall >= 70 else ("average" if overall >= 45 else "low")

        # Gather top improvement suggestions (sorted by impact)
        improvements = []
        for s in sorted(signals, key=lambda x: x.score):
            improvements.extend(s.suggestions)
        top_improvements = improvements[:5]

        comp = "above average" if overall >= 70 else ("average" if overall >= 50 else "below average")

        return PerformancePrediction(
            overall_score=round(overall, 1),
            tier=tier,
            ctr_estimate=ctr,
            conversion_estimate=conv,
            visibility_estimate=vis,
            signals=signals,
            top_improvements=top_improvements,
            competitive_position=comp,
        )

    # ── Individual Signal Scorers ────────────────────────────

    def _score_title_quality(self, title: str) -> SignalScore:
        score = 0
        suggestions = []

        words = title.split()
        word_count = len(words)

        # Word count bonus (sweet spot: 8-20 words)
        if 8 <= word_count <= 20:
            score += 40
        elif 5 <= word_count < 8:
            score += 25
        elif word_count > 20:
            score += 20
            suggestions.append("Title may be too long — keep under 20 words for readability")
        else:
            score += 10
            suggestions.append("Title is too short — aim for 8-20 words")

        # Power words
        title_lower = title.lower()
        power_count = sum(1 for pw in POWER_WORDS if pw in title_lower)
        score += min(power_count * 10, 30)
        if power_count == 0:
            suggestions.append("Add power words (e.g. 'Premium', 'Upgraded', 'Professional') to boost CTR")

        # Starts with brand or key feature
        if words and words[0][0].isupper():
            score += 10

        # Proper capitalization (Title Case)
        title_case_ratio = sum(1 for w in words if w[0:1].isupper()) / max(word_count, 1)
        if title_case_ratio >= 0.5:
            score += 10
        else:
            suggestions.append("Use Title Case capitalization for professional appearance")

        # Commas / pipes for readability
        if ',' in title or '|' in title or '-' in title:
            score += 10

        return SignalScore("title_quality", min(score, 100), self._weights["title_quality"],
                          f"{word_count} words, {power_count} power words", suggestions)

    def _score_keyword_coverage(self, keywords: list[str], text: str, title: str) -> SignalScore:
        if not keywords:
            return SignalScore("keyword_coverage", 50, self._weights["keyword_coverage"],
                             "No keywords provided", ["Provide target keywords for accurate scoring"])

        in_title = sum(1 for kw in keywords if kw in title)
        in_text = sum(1 for kw in keywords if kw in text)
        title_ratio = in_title / len(keywords)
        text_ratio = in_text / len(keywords)

        score = title_ratio * 60 + text_ratio * 40
        suggestions = []
        missing_title = [kw for kw in keywords if kw not in title]
        if missing_title:
            top_missing = missing_title[:3]
            suggestions.append(f"Add missing keywords to title: {', '.join(top_missing)}")

        return SignalScore("keyword_coverage", min(score, 100), self._weights["keyword_coverage"],
                          f"{in_title}/{len(keywords)} in title, {in_text}/{len(keywords)} in listing",
                          suggestions)

    def _score_description(self, description: str) -> SignalScore:
        if not description:
            return SignalScore("description_depth", 0, self._weights["description_depth"],
                             "No description", ["Add a detailed product description (150+ words)"])

        word_count = len(description.split())
        score = 0
        suggestions = []

        if word_count >= 200:
            score += 50
        elif word_count >= 100:
            score += 35
        elif word_count >= 50:
            score += 20
        else:
            score += 10
            suggestions.append(f"Description too short ({word_count} words) — aim for 150-300 words")

        # Formatting signals
        has_html = bool(re.search(r'<[a-z]', description, re.I))
        has_bullets = bool(re.search(r'[-•*]\s', description))
        has_paragraphs = description.count('\n\n') >= 1

        if has_html or has_bullets:
            score += 20
        if has_paragraphs:
            score += 15
        else:
            suggestions.append("Break description into paragraphs for readability")

        # Benefit-oriented language
        benefit_words = {"benefit", "feature", "perfect for", "ideal for", "designed for",
                        "compatible with", "works with", "includes", "comes with"}
        benefit_count = sum(1 for bw in benefit_words if bw in description.lower())
        score += min(benefit_count * 5, 15)

        return SignalScore("description_depth", min(score, 100), self._weights["description_depth"],
                          f"{word_count} words", suggestions)

    def _score_bullets(self, bullets: list[str]) -> SignalScore:
        if not bullets:
            return SignalScore("bullet_points", 0, self._weights["bullet_points"],
                             "No bullet points", ["Add 5 bullet points highlighting key features and benefits"])

        count = len(bullets)
        score = 0
        suggestions = []

        # Ideal: 5 bullets
        if count >= 5:
            score += 40
        elif count >= 3:
            score += 25
        else:
            score += 10
            suggestions.append(f"Only {count} bullet(s) — add more (aim for 5)")

        # Average bullet length (ideal: 100-200 chars)
        avg_len = sum(len(b) for b in bullets) / max(count, 1)
        if 80 <= avg_len <= 250:
            score += 30
        elif avg_len < 80:
            score += 15
            suggestions.append("Bullet points are too short — expand with details and benefits")
        else:
            score += 20
            suggestions.append("Some bullets may be too long — keep each under 250 characters")

        # Starts with capital / feature keyword
        caps_start = sum(1 for b in bullets if b and b[0].isupper())
        if caps_start == count:
            score += 15

        # Contains benefit language
        benefit_count = sum(1 for b in bullets
                          if any(w in b.lower() for w in ("perfect", "ideal", "great", "easy", "includes")))
        score += min(benefit_count * 5, 15)

        return SignalScore("bullet_points", min(score, 100), self._weights["bullet_points"],
                          f"{count} bullets, avg {avg_len:.0f} chars", suggestions)

    def _score_price(self, price: float | None, competitors: list[float] | None) -> SignalScore:
        if price is None:
            return SignalScore("price_competitiveness", 50, self._weights["price_competitiveness"],
                             "No price provided", [])

        if not competitors:
            return SignalScore("price_competitiveness", 50, self._weights["price_competitiveness"],
                             f"${price:.2f} (no competitor data)", ["Provide competitor prices for positioning analysis"])

        avg_comp = sum(competitors) / len(competitors)
        ratio = price / avg_comp if avg_comp > 0 else 1.0

        suggestions = []
        if ratio <= 0.85:
            score = 90  # significantly cheaper
            detail = "well below market"
        elif ratio <= 1.0:
            score = 80
            detail = "below market average"
        elif ratio <= 1.1:
            score = 65
            detail = "near market average"
        elif ratio <= 1.3:
            score = 40
            detail = "above market"
            suggestions.append("Price is above market average — highlight premium features to justify")
        else:
            score = 20
            detail = "significantly above market"
            suggestions.append("Price is significantly above competitors — consider adjusting or emphasizing unique value")

        return SignalScore("price_competitiveness", score, self._weights["price_competitiveness"],
                          f"${price:.2f} vs avg ${avg_comp:.2f} ({detail})", suggestions)

    def _score_images(self, count: int) -> SignalScore:
        suggestions = []
        if count == 0:
            return SignalScore("image_signals", 0, self._weights["image_signals"],
                             "No images", ["Add at least 5 product images (main + lifestyle + detail)"])

        # Amazon ideal: 7-9 images
        if count >= 7:
            score = 100
        elif count >= 5:
            score = 75
        elif count >= 3:
            score = 50
        else:
            score = 25
            suggestions.append(f"Only {count} image(s) — add more (7+ recommended)")

        return SignalScore("image_signals", score, self._weights["image_signals"],
                          f"{count} images", suggestions)

    def _score_brand(self, brand: str, title: str) -> SignalScore:
        if not brand:
            return SignalScore("brand_presence", 30, self._weights["brand_presence"],
                             "No brand specified", ["Register a brand for better trust and A+ Content access"])

        score = 50
        suggestions = []
        if brand.lower() in title.lower():
            score += 30
        else:
            suggestions.append("Add brand name to the beginning of the title")

        if len(brand) <= 20:
            score += 20

        return SignalScore("brand_presence", min(score, 100), self._weights["brand_presence"],
                          f"Brand: {brand}", suggestions)

    def _score_mobile(self, title: str, bullets: list[str]) -> SignalScore:
        score = 50
        suggestions = []

        # Mobile title truncation (~80 chars on most apps)
        if len(title) <= 80:
            score += 30
        elif len(title) <= 120:
            score += 15
        else:
            suggestions.append("Title exceeds 80 chars — key info may be cut off on mobile")

        # Short bullet points work better on mobile
        if bullets:
            long_bullets = sum(1 for b in bullets if len(b) > 200)
            if long_bullets == 0:
                score += 20
            else:
                suggestions.append(f"{long_bullets} bullet(s) exceed 200 chars — shorten for mobile readability")

        return SignalScore("mobile_readability", min(score, 100), self._weights["mobile_readability"],
                          f"Title: {len(title)} chars", suggestions)

    def _score_search_terms(self, backend: str, keywords: list[str]) -> SignalScore:
        if not backend and not keywords:
            return SignalScore("search_term_usage", 30, self._weights["search_term_usage"],
                             "No search terms", ["Add backend search terms (up to 250 bytes on Amazon)"])

        score = 50
        suggestions = []

        if backend:
            byte_len = len(backend.encode('utf-8'))
            if byte_len <= 250:
                score += 30
            else:
                score += 15
                suggestions.append(f"Backend keywords ({byte_len} bytes) exceed 250-byte limit — trim to avoid indexing issues")

            # No duplicate words from title
            score += 20
        else:
            suggestions.append("Use backend search terms for additional keyword coverage")

        return SignalScore("search_term_usage", min(score, 100), self._weights["search_term_usage"],
                          f"{len(backend)} chars backend", suggestions)

    def _score_features(self, text: str) -> SignalScore:
        feature_patterns = [
            r'(?:material|made of|constructed)',
            r'(?:size|dimension|measure)',
            r'(?:weight|weighs)',
            r'(?:color|colour)',
            r'(?:compatible|works with|fits)',
            r'(?:warranty|guarantee)',
            r'(?:package|includes|comes with)',
            r'(?:battery|power|charge)',
        ]

        found = sum(1 for p in feature_patterns if re.search(p, text, re.I))
        score = min((found / len(feature_patterns)) * 100, 100)
        suggestions = []
        if found < 4:
            suggestions.append("Add more product specifications (dimensions, material, compatibility, warranty)")

        return SignalScore("feature_completeness", round(score, 1), self._weights["feature_completeness"],
                          f"{found}/{len(feature_patterns)} feature types mentioned", suggestions)

    def _score_title_length(self, title: str) -> SignalScore:
        lo, hi = IDEAL_TITLE_LENGTH.get(self.platform, IDEAL_TITLE_LENGTH["default"])
        length = len(title)
        suggestions = []

        if lo <= length <= hi:
            score = 100
        elif length < lo:
            score = max(0, 100 - (lo - length) * 3)
            suggestions.append(f"Title too short ({length} chars) — aim for {lo}-{hi} chars on {self.platform}")
        else:
            score = max(0, 100 - (length - hi) * 2)
            suggestions.append(f"Title too long ({length} chars) — keep under {hi} chars on {self.platform}")

        return SignalScore("title_length_fit", score, self._weights["title_length_fit"],
                          f"{length} chars (ideal: {lo}-{hi})", suggestions)

    def _score_spam(self, title: str, description: str) -> SignalScore:
        text = f"{title} {description}"
        penalties = 0
        suggestions = []

        for pattern in SPAM_PATTERNS:
            matches = re.findall(pattern, text, re.I)
            if matches:
                penalties += len(matches)

        if penalties == 0:
            score = 100
        elif penalties <= 2:
            score = 70
            suggestions.append("Minor spam signals detected — remove excessive punctuation or caps")
        else:
            score = max(0, 100 - penalties * 15)
            suggestions.append("Multiple spam signals detected — clean up title and description to avoid suppression")

        return SignalScore("special_characters", score, self._weights["special_characters"],
                          f"{penalties} spam signals", suggestions)

    @staticmethod
    def _classify_tier(score: float) -> PerformanceTier:
        if score >= 85:
            return PerformanceTier.EXCELLENT
        elif score >= 70:
            return PerformanceTier.GOOD
        elif score >= 50:
            return PerformanceTier.AVERAGE
        elif score >= 30:
            return PerformanceTier.POOR
        return PerformanceTier.CRITICAL

    # ── Comparison ───────────────────────────────────────────

    def compare(self, listings: list[dict]) -> list[PerformancePrediction]:
        """Compare multiple listings and return sorted predictions."""
        results = []
        for listing in listings:
            pred = self.predict(**listing)
            results.append(pred)
        return sorted(results, key=lambda p: -p.overall_score)

    # ── Report ───────────────────────────────────────────────

    def report(self, prediction: PerformancePrediction) -> str:
        """Generate human-readable performance report."""
        lines = [
            f"📊 Listing Performance Prediction",
            f"{'=' * 50}",
            f"Overall Score: {prediction.overall_score}/100 ({prediction.tier.value.upper()})",
            f"",
            f"Estimates:",
            f"  CTR:        {prediction.ctr_estimate}",
            f"  Conversion: {prediction.conversion_estimate}",
            f"  Visibility: {prediction.visibility_estimate}",
            f"  Position:   {prediction.competitive_position}",
            f"",
            f"Signal Breakdown:",
        ]

        for s in sorted(prediction.signals, key=lambda x: -x.score * x.weight):
            bar = "█" * int(s.score / 10) + "░" * (10 - int(s.score / 10))
            lines.append(f"  {s.name:25s} {bar} {s.score:5.1f} (×{s.weight:.2f})")

        if prediction.top_improvements:
            lines.append(f"\n💡 Top Improvements:")
            for i, imp in enumerate(prediction.top_improvements, 1):
                lines.append(f"  {i}. {imp}")

        return "\n".join(lines)


# ── Module-level convenience ─────────────────────────────────

def predict_performance(title: str, platform: str = "amazon", **kwargs) -> PerformancePrediction:
    """Quick performance prediction."""
    predictor = PerformancePredictor(platform)
    return predictor.predict(title=title, **kwargs)
