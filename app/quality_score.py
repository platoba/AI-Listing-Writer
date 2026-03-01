"""
Unified Quality Score Engine
=============================

Combines all quality dimensions (grader, SEO density, performance prediction,
return risk, readability, compliance) into a single composite Quality Score
with weighted breakdown, trend tracking, and competitive benchmarking.

Features:
- Composite 0-100 quality score from 8 dimensions
- Platform-specific weight profiles
- Score trend tracking over time
- Competitive benchmark comparison
- Priority-ranked improvement roadmap
- Score card with visual breakdown
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ── Models ───────────────────────────────────────────────────

class QualityTier(str, Enum):
    PLATINUM = "platinum"  # 90-100
    GOLD = "gold"          # 75-89
    SILVER = "silver"      # 60-74
    BRONZE = "bronze"      # 40-59
    IRON = "iron"          # 0-39


@dataclass
class DimensionScore:
    """Score for a single quality dimension."""
    name: str
    score: float        # 0-100
    weight: float       # 0-1
    icon: str
    details: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    @property
    def weighted(self) -> float:
        return self.score * self.weight

    @property
    def bar(self) -> str:
        filled = int(self.score / 10)
        return "█" * filled + "░" * (10 - filled)


@dataclass
class ImprovementItem:
    """Single improvement recommendation."""
    dimension: str
    action: str
    impact: float       # expected score increase 0-20
    effort: str         # "low", "medium", "high"
    priority: int       # 1 = highest priority

    @property
    def roi(self) -> float:
        effort_map = {"low": 3.0, "medium": 1.5, "high": 0.5}
        return self.impact * effort_map.get(self.effort, 1.0)


@dataclass
class ScoreSnapshot:
    """Point-in-time quality score record."""
    score: float
    tier: QualityTier
    timestamp: datetime
    dimensions: dict[str, float]


@dataclass
class QualityReport:
    """Full quality score report."""
    total_score: float
    tier: QualityTier
    dimensions: list[DimensionScore]
    improvements: list[ImprovementItem]
    platform: str
    listing_id: str
    scored_at: datetime
    benchmark: Optional[dict] = None  # {avg: float, top10: float}
    trend: list[ScoreSnapshot] = field(default_factory=list)

    def card(self) -> str:
        """Generate text score card."""
        lines = [
            f"{'═' * 50}",
            f"  🏆 QUALITY SCORE: {self.total_score:.0f}/100 [{self.tier.value.upper()}]",
            f"  📦 Platform: {self.platform}  |  🆔 {self.listing_id}",
            f"  📅 {self.scored_at:%Y-%m-%d %H:%M}",
            f"{'═' * 50}",
            "",
        ]

        # Dimensions
        lines.append("📊 Score Breakdown:")
        for d in sorted(self.dimensions, key=lambda x: x.weighted, reverse=True):
            status = "✅" if d.score >= 70 else "⚠️" if d.score >= 50 else "❌"
            lines.append(
                f"  {status} {d.icon} {d.name}: {d.score:.0f}/100 "
                f"[{d.bar}] (×{d.weight:.0%})"
            )
            for detail in d.details[:2]:
                lines.append(f"       {detail}")

        # Benchmark
        if self.benchmark:
            lines.append("")
            avg = self.benchmark.get("avg", 0)
            top10 = self.benchmark.get("top10", 0)
            diff = self.total_score - avg
            arrow = "↑" if diff > 0 else "↓" if diff < 0 else "→"
            lines.append(
                f"📈 Benchmark: You {self.total_score:.0f} vs "
                f"Avg {avg:.0f} ({arrow}{abs(diff):.0f}) | "
                f"Top 10%: {top10:.0f}"
            )

        # Improvements
        if self.improvements:
            lines.append("")
            lines.append("🚀 Top Improvements (highest ROI first):")
            for i, imp in enumerate(self.improvements[:5], 1):
                effort_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(
                    imp.effort, "⚪"
                )
                lines.append(
                    f"  {i}. {effort_icon} {imp.action} "
                    f"(+{imp.impact:.0f} pts, effort: {imp.effort})"
                )

        lines.append(f"\n{'═' * 50}")
        return "\n".join(lines)


# ── Platform Weight Profiles ────────────────────────────────

PLATFORM_WEIGHTS = {
    "amazon": {
        "title": 0.18,
        "bullets": 0.16,
        "description": 0.10,
        "seo": 0.18,
        "conversion": 0.15,
        "readability": 0.08,
        "compliance": 0.08,
        "completeness": 0.07,
    },
    "ebay": {
        "title": 0.20,
        "bullets": 0.10,
        "description": 0.15,
        "seo": 0.15,
        "conversion": 0.15,
        "readability": 0.10,
        "compliance": 0.08,
        "completeness": 0.07,
    },
    "shopify": {
        "title": 0.15,
        "bullets": 0.10,
        "description": 0.18,
        "seo": 0.20,
        "conversion": 0.15,
        "readability": 0.10,
        "compliance": 0.05,
        "completeness": 0.07,
    },
    "aliexpress": {
        "title": 0.18,
        "bullets": 0.12,
        "description": 0.12,
        "seo": 0.15,
        "conversion": 0.18,
        "readability": 0.08,
        "compliance": 0.10,
        "completeness": 0.07,
    },
    "walmart": {
        "title": 0.18,
        "bullets": 0.15,
        "description": 0.12,
        "seo": 0.18,
        "conversion": 0.12,
        "readability": 0.10,
        "compliance": 0.08,
        "completeness": 0.07,
    },
    "etsy": {
        "title": 0.15,
        "bullets": 0.10,
        "description": 0.20,
        "seo": 0.15,
        "conversion": 0.12,
        "readability": 0.12,
        "compliance": 0.08,
        "completeness": 0.08,
    },
}

# Default weights for unknown platforms
DEFAULT_WEIGHTS = {
    "title": 0.16,
    "bullets": 0.14,
    "description": 0.14,
    "seo": 0.16,
    "conversion": 0.14,
    "readability": 0.10,
    "compliance": 0.08,
    "completeness": 0.08,
}

# ── Benchmark Data (industry averages) ─────────────────────

BENCHMARKS = {
    "amazon": {"avg": 62, "top10": 85, "top1": 95},
    "ebay": {"avg": 55, "top10": 78, "top1": 90},
    "shopify": {"avg": 58, "top10": 80, "top1": 92},
    "aliexpress": {"avg": 50, "top10": 75, "top1": 88},
    "walmart": {"avg": 60, "top10": 82, "top1": 93},
    "etsy": {"avg": 57, "top10": 79, "top1": 91},
}


# ── Scoring Functions ───────────────────────────────────────

def _detect_lang(text: str) -> str:
    cn = len(re.findall(r'[\u4e00-\u9fff]', text))
    en = len(re.findall(r'[a-zA-Z]', text))
    return "cn" if cn > en else "en"


def score_title_quality(text: str, platform: str = "amazon") -> DimensionScore:
    """Score title quality."""
    ds = DimensionScore(name="Title", score=0, weight=0, icon="📝")

    # Extract title
    title_match = re.search(
        r'\*\*(?:title|标题|product\s*name|seo\s*title)\*\*\s*[:：]?\s*(.+?)(?:\n|$)',
        text, re.IGNORECASE
    )
    title = title_match.group(1).strip() if title_match else text.split("\n")[0].strip()

    if not title or len(title) < 10:
        ds.score = 15
        ds.details.append("No substantial title found")
        ds.suggestions.append("Add a keyword-rich product title")
        return ds

    score = 0
    title_len = len(title)

    # Length scoring
    if 80 <= title_len <= 200:
        score += 30
        ds.details.append(f"Good length ({title_len} chars)")
    elif 40 <= title_len < 80:
        score += 20
        ds.suggestions.append(f"Title could be longer ({title_len} chars, aim 80-200)")
    elif title_len > 200:
        score += 15
        ds.suggestions.append(f"Title too long ({title_len} chars)")
    else:
        score += 10
        ds.suggestions.append(f"Title too short ({title_len} chars)")

    # Word count
    words = title.split()
    if 8 <= len(words) <= 25:
        score += 20
        ds.details.append(f"{len(words)} words — optimal range")
    else:
        score += 10

    # Keyword separators
    seps = len(re.findall(r'[|,\-–—/]', title))
    if 1 <= seps <= 4:
        score += 15
        ds.details.append("Good separator usage")
    elif seps == 0:
        score += 5
        ds.suggestions.append("Add separators (|, -, /) for readability")
    else:
        score += 8

    # Brand check
    if re.match(r'^[A-Z]', title):
        score += 15
        ds.details.append("Starts with uppercase/brand")
    else:
        score += 5

    # Feature words
    features = ["with", "for", "includes", "pack", "set", "compatible"]
    found = sum(1 for f in features if f.lower() in title.lower())
    score += min(20, found * 7)
    if found >= 2:
        ds.details.append(f"{found} feature descriptors found")

    ds.score = min(100, score)
    return ds


def score_bullets_quality(text: str) -> DimensionScore:
    """Score bullet point quality."""
    ds = DimensionScore(name="Bullets", score=0, weight=0, icon="🔹")

    bullets = re.findall(r'^\s*[-•*✅✓→►]\s*(.+)', text, re.MULTILINE)
    if not bullets:
        bullets = re.findall(r'^\s*\d+[.)]\s*(.+)', text, re.MULTILINE)

    if not bullets:
        ds.score = 10
        ds.details.append("No bullets detected")
        ds.suggestions.append("Add 5+ benefit-led bullet points")
        return ds

    score = 0

    # Count
    if len(bullets) >= 5:
        score += 25
        ds.details.append(f"{len(bullets)} bullets ✓")
    elif len(bullets) >= 3:
        score += 15
    else:
        score += 8
        ds.suggestions.append(f"Only {len(bullets)} bullets — add more")

    # Length
    avg_len = sum(len(b) for b in bullets) / len(bullets)
    if avg_len >= 80:
        score += 25
        ds.details.append(f"Good detail ({avg_len:.0f} avg chars)")
    elif avg_len >= 40:
        score += 15
    else:
        score += 8
        ds.suggestions.append("Expand bullets with more detail")

    # Variety
    starts = [b[:15].lower() for b in bullets]
    unique = len(set(starts)) / max(len(starts), 1)
    if unique > 0.8:
        score += 25
        ds.details.append("Good variety")
    elif unique > 0.5:
        score += 15
    else:
        score += 5
        ds.suggestions.append("Diversify bullet openings")

    # Benefits language
    benefit_words = ["helps", "provides", "ensures", "protects", "saves",
                     "features", "includes", "delivers", "offers"]
    all_bullet_text = " ".join(bullets).lower()
    found = sum(1 for bw in benefit_words if bw in all_bullet_text)
    score += min(25, found * 5)

    ds.score = min(100, score)
    return ds


def score_description_quality(text: str) -> DimensionScore:
    """Score description quality."""
    ds = DimensionScore(name="Description", score=0, weight=0, icon="📄")

    desc_match = re.search(
        r'\*\*(?:description|描述|product\s*description)\*\*\s*[:：]?\s*(.*?)(?=\*\*[^*]|\Z)',
        text, re.IGNORECASE | re.DOTALL
    )
    desc = desc_match.group(1).strip() if desc_match else text

    words = re.findall(r'[\w\u4e00-\u9fff]+', desc)
    score = 0

    if len(words) >= 200:
        score += 25
    elif len(words) >= 100:
        score += 15
    else:
        score += 5
        ds.suggestions.append("Expand description (aim for 200+ words)")

    # Formatting
    has_bold = bool(re.search(r'\*\*.+?\*\*', desc))
    has_bullets = bool(re.search(r'^\s*[-•*]\s', desc, re.MULTILINE))
    has_headers = bool(re.search(r'^\s*#{1,3}\s', desc, re.MULTILINE))
    fmt_count = sum([has_bold, has_bullets, has_headers])
    score += min(25, fmt_count * 10)

    # Paragraph structure
    paras = [p for p in desc.split("\n\n") if p.strip()]
    if len(paras) >= 3:
        score += 20
    elif len(paras) >= 2:
        score += 10
    else:
        score += 5
        ds.suggestions.append("Break into multiple paragraphs")

    # Persuasive language
    conv_words = ["guarantee", "free", "save", "premium", "exclusive",
                  "limited", "proven", "trusted", "certified"]
    found = sum(1 for cw in conv_words if cw in desc.lower())
    score += min(20, found * 5)

    # Sentence variety
    sentences = re.split(r'[.!?。]+', desc)
    sentences = [s for s in sentences if len(s.strip()) > 5]
    if len(sentences) >= 5:
        score += 10

    ds.score = min(100, score)
    return ds


def score_seo(text: str, platform: str = "amazon") -> DimensionScore:
    """Score SEO optimization."""
    ds = DimensionScore(name="SEO", score=0, weight=0, icon="🔍")
    score = 0

    # Search terms section
    if re.search(r'\*\*(?:search\s*terms?|backend\s*keywords?|标签|关键词)\*\*',
                 text, re.IGNORECASE):
        score += 25
        ds.details.append("Keywords section present")
    else:
        ds.suggestions.append("Add backend keywords/search terms section")

    # Keyword stuffing check
    words = re.findall(r'[\w\u4e00-\u9fff]+', text.lower())
    if words:
        from collections import Counter
        freq = Counter(words)
        top_word, top_count = freq.most_common(1)[0]
        density = top_count / len(words) * 100
        if density < 4:
            score += 25
            ds.details.append("No keyword stuffing detected")
        elif density < 6:
            score += 15
        else:
            score += 5
            ds.suggestions.append(f"'{top_word}' at {density:.1f}% — reduce repetition")

    # Content depth
    if len(words) >= 300:
        score += 25
    elif len(words) >= 150:
        score += 15
    else:
        score += 5
        ds.suggestions.append("Add more content for better SEO coverage")

    # Unique words ratio
    if words:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio > 0.5:
            score += 25
            ds.details.append(f"High vocabulary diversity ({unique_ratio:.0%})")
        elif unique_ratio > 0.3:
            score += 15
        else:
            score += 5

    ds.score = min(100, score)
    return ds


def score_conversion(text: str) -> DimensionScore:
    """Score conversion optimization."""
    ds = DimensionScore(name="Conversion", score=0, weight=0, icon="💰")
    score = 0
    text_lower = text.lower()

    # CTA
    ctas = [r'buy\s+now', r'add\s+to\s+cart', r'order\s+today', r'shop\s+now',
            r'立即购买', r'加入购物车']
    if any(re.search(c, text_lower) for c in ctas):
        score += 20
        ds.details.append("CTA present")
    else:
        ds.suggestions.append("Add a call-to-action")

    # Social proof
    social = [r'\d+\s*(?:review|rating|star|customer)', r'best.?sell',
              r'top.?rated', r'好评', r'热销']
    if any(re.search(s, text_lower) for s in social):
        score += 20
        ds.details.append("Social proof found")

    # Trust signals
    trust = [r'guarantee', r'warranty', r'money.?back', r'free.?(?:shipping|return)',
             r'保障', r'包邮']
    if any(re.search(t, text_lower) for t in trust):
        score += 20
        ds.details.append("Trust signals present")

    # Urgency
    urgency = [r'limited', r'only\s*\d+\s*left', r'sale', r'限时', r'仅剩']
    if any(re.search(u, text_lower) for u in urgency):
        score += 15

    # Benefits language
    benefits = ["helps", "saves", "protects", "improves", "enables",
                "让", "帮助", "提升"]
    found = sum(1 for b in benefits if b in text_lower)
    score += min(25, found * 5)

    ds.score = min(100, score)
    return ds


def score_readability(text: str) -> DimensionScore:
    """Score readability."""
    ds = DimensionScore(name="Readability", score=0, weight=0, icon="👁️")
    score = 0

    sentences = re.split(r'[.!?。！？]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]

    if not sentences:
        ds.score = 30
        return ds

    # Average sentence length
    avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
    if 10 <= avg_len <= 20:
        score += 30
        ds.details.append(f"Good sentence length ({avg_len:.0f} words avg)")
    elif avg_len < 10:
        score += 20
    else:
        score += 10
        ds.suggestions.append("Shorten some sentences for readability")

    # Paragraph breaks
    paras = [p for p in text.split("\n\n") if p.strip()]
    if len(paras) >= 3:
        score += 25
    elif len(paras) >= 2:
        score += 15
    else:
        score += 5

    # Formatting elements
    format_count = 0
    if re.search(r'\*\*.+?\*\*', text):
        format_count += 1
    if re.search(r'^\s*[-•*]\s', text, re.MULTILINE):
        format_count += 1
    if re.search(r'[\U0001F300-\U0001F9FF]', text):
        format_count += 1
    score += min(25, format_count * 10)
    if format_count >= 2:
        ds.details.append("Good visual formatting")

    # Short lines
    lines = text.split("\n")
    long_lines = sum(1 for l in lines if len(l) > 120)
    if long_lines == 0:
        score += 20
    elif long_lines < 3:
        score += 10
    else:
        ds.suggestions.append(f"{long_lines} lines exceed 120 chars")

    ds.score = min(100, score)
    return ds


def score_compliance(text: str, platform: str = "amazon") -> DimensionScore:
    """Score platform compliance."""
    ds = DimensionScore(name="Compliance", score=0, weight=0, icon="✅")
    score = 70  # Start with baseline

    text_lower = text.lower()

    # Prohibited claims
    health_claims = [
        r'\b(?:cure|treat|heal|prevent|diagnose)\s+\w+', r'FDA\s*approved',
        r'clinically\s*proven', r'medical\s*grade',
    ]
    for pattern in health_claims:
        if re.search(pattern, text_lower):
            score -= 15
            ds.suggestions.append(f"Remove health claim: matches '{pattern}'")
            ds.details.append("⚠️ Potential health claim detected")

    # Superlative claims without qualification
    superlatives = [
        r'\b(?:best|#1|number\s*one|greatest|most\s+\w+)\b',
    ]
    for pattern in superlatives:
        if re.search(pattern, text_lower):
            score -= 5
            ds.suggestions.append("Qualify superlative claims or remove")

    # Contact info (usually prohibited in listings)
    contact = [r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', r'\w+@\w+\.\w+',
               r'(?:call|email|contact)\s+us']
    for pattern in contact:
        if re.search(pattern, text_lower):
            score -= 10
            ds.suggestions.append("Remove contact information from listing")

    # External URLs
    if re.search(r'https?://(?!(?:amazon|ebay|walmart|shopify))', text_lower):
        score -= 10
        ds.suggestions.append("Remove external URLs")

    # ALL CAPS abuse
    caps_words = re.findall(r'\b[A-Z]{4,}\b', text)
    if len(caps_words) > 5:
        score -= 5
        ds.suggestions.append("Reduce ALL CAPS usage")

    if score >= 70:
        ds.details.append("No major compliance issues")

    ds.score = max(0, min(100, score))
    return ds


def score_completeness(text: str) -> DimensionScore:
    """Score listing completeness."""
    ds = DimensionScore(name="Completeness", score=0, weight=0, icon="📦")
    score = 0

    sections = {
        "title": r'\*\*(?:title|标题|product\s*name)',
        "bullets": r'\*\*(?:bullet|feature|卖点|要点)',
        "description": r'\*\*(?:description|描述)',
        "keywords": r'\*\*(?:search\s*terms?|keywords?|标签|关键词)',
        "images": r'\*\*(?:image|图片)',
    }

    found = 0
    for section, pattern in sections.items():
        if re.search(pattern, text, re.IGNORECASE):
            found += 1
        else:
            ds.suggestions.append(f"Add {section} section")

    score = int(found / len(sections) * 100)
    ds.details.append(f"{found}/{len(sections)} sections present")

    ds.score = max(0, min(100, score))
    return ds


def compute_quality_score(
    text: str,
    platform: str = "amazon",
    listing_id: str = "",
) -> QualityReport:
    """Compute comprehensive quality score for a listing.

    Args:
        text: Full listing text.
        platform: Target marketplace.
        listing_id: Listing identifier.

    Returns:
        QualityReport with full breakdown and improvements.
    """
    weights = PLATFORM_WEIGHTS.get(platform.lower(), DEFAULT_WEIGHTS)

    # Score all dimensions
    dims = [
        score_title_quality(text, platform),
        score_bullets_quality(text),
        score_description_quality(text),
        score_seo(text, platform),
        score_conversion(text),
        score_readability(text),
        score_compliance(text, platform),
        score_completeness(text),
    ]

    # Map dimension names to weight keys
    dim_weight_map = {
        "Title": "title",
        "Bullets": "bullets",
        "Description": "description",
        "SEO": "seo",
        "Conversion": "conversion",
        "Readability": "readability",
        "Compliance": "compliance",
        "Completeness": "completeness",
    }

    for dim in dims:
        key = dim_weight_map.get(dim.name, dim.name.lower())
        dim.weight = weights.get(key, 0.1)

    # Total score
    total = sum(d.weighted for d in dims)
    total = min(100, max(0, total))

    # Tier
    if total >= 90:
        tier = QualityTier.PLATINUM
    elif total >= 75:
        tier = QualityTier.GOLD
    elif total >= 60:
        tier = QualityTier.SILVER
    elif total >= 40:
        tier = QualityTier.BRONZE
    else:
        tier = QualityTier.IRON

    # Generate improvements
    improvements = []
    for dim in sorted(dims, key=lambda d: d.score):
        for i, suggestion in enumerate(dim.suggestions):
            impact = (100 - dim.score) * dim.weight * 0.5
            effort = "low" if dim.score < 30 else "medium" if dim.score < 60 else "high"
            improvements.append(ImprovementItem(
                dimension=dim.name,
                action=suggestion,
                impact=round(impact, 1),
                effort=effort,
                priority=len(improvements) + 1,
            ))

    # Sort by ROI
    improvements.sort(key=lambda x: x.roi, reverse=True)

    # Benchmark
    benchmark = BENCHMARKS.get(platform.lower())

    return QualityReport(
        total_score=round(total, 1),
        tier=tier,
        dimensions=dims,
        improvements=improvements,
        platform=platform,
        listing_id=listing_id,
        scored_at=datetime.now(),
        benchmark=benchmark,
    )


def compare_scores(
    reports: list[QualityReport],
) -> str:
    """Compare quality scores across multiple listings/platforms."""
    if not reports:
        return "No reports to compare."

    lines = ["📊 Quality Score Comparison", ""]

    # Table header
    lines.append(f"{'Listing':<20} {'Platform':<12} {'Score':>6} {'Tier':<10}")
    lines.append("-" * 50)

    for r in sorted(reports, key=lambda x: x.total_score, reverse=True):
        lines.append(
            f"{r.listing_id:<20} {r.platform:<12} "
            f"{r.total_score:>5.0f}  {r.tier.value:<10}"
        )

    # Dimension comparison
    if len(reports) > 1:
        lines.append("")
        lines.append("Dimension Breakdown:")
        dim_names = [d.name for d in reports[0].dimensions]
        for name in dim_names:
            scores_str = " | ".join(
                f"{next((d.score for d in r.dimensions if d.name == name), 0):.0f}"
                for r in reports
            )
            lines.append(f"  {name:<15} {scores_str}")

    return "\n".join(lines)
