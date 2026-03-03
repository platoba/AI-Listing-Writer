"""Listing Quality Grader.

Comprehensive listing grader that combines all quality dimensions
into a single A-F grade with detailed breakdown:
- SEO density health
- Content structure & formatting
- Competitive readiness
- Platform compliance
- Conversion potential
- Mobile optimization readiness
"""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GradeDetail:
    """Individual grading criterion."""
    criterion: str
    score: float  # 0-100
    weight: float
    passed: bool
    notes: list[str] = field(default_factory=list)

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class ListingGrade:
    """Overall listing grade with breakdown."""
    total_score: float
    letter_grade: str
    criteria: list[GradeDetail]
    strengths: list[str]
    weaknesses: list[str]
    quick_wins: list[str]
    competitive_readiness: str  # "not ready", "almost", "ready", "strong"

    def summary(self) -> str:
        lines = [
            f"📊 Listing Grade: {self.letter_grade} ({self.total_score:.0f}/100)",
            f"🏆 Competitive Readiness: {self.competitive_readiness}",
            "",
        ]

        # Criteria breakdown
        lines.append("📋 Criteria Breakdown:")
        for c in sorted(self.criteria, key=lambda x: x.weighted_score, reverse=True):
            icon = "✅" if c.passed else "❌"
            bar = "█" * int(c.score / 10) + "░" * (10 - int(c.score / 10))
            lines.append(f"  {icon} {c.criterion}: {c.score:.0f}/100 [{bar}]")
            for note in c.notes:
                lines.append(f"      {note}")

        # Strengths
        if self.strengths:
            lines.append("")
            lines.append("💪 Strengths:")
            for s in self.strengths:
                lines.append(f"  ✅ {s}")

        # Weaknesses
        if self.weaknesses:
            lines.append("")
            lines.append("⚠️ Weaknesses:")
            for w in self.weaknesses:
                lines.append(f"  ❌ {w}")

        # Quick wins
        if self.quick_wins:
            lines.append("")
            lines.append("🚀 Quick Wins (do these first!):")
            for i, qw in enumerate(self.quick_wins, 1):
                lines.append(f"  {i}. {qw}")

        return "\n".join(lines)


# ── Constants ────────────────────────────────────────────

TITLE_LENGTH = {
    "amazon": {"min": 80, "max": 200, "ideal_min": 120, "ideal_max": 180},
    "ebay": {"min": 40, "max": 80, "ideal_min": 50, "ideal_max": 75},
    "shopify": {"min": 30, "max": 70, "ideal_min": 40, "ideal_max": 60},
    "walmart": {"min": 50, "max": 150, "ideal_min": 75, "ideal_max": 130},
    "etsy": {"min": 30, "max": 140, "ideal_min": 60, "ideal_max": 120},
    "aliexpress": {"min": 60, "max": 200, "ideal_min": 100, "ideal_max": 180},
}

BULLET_COUNT = {
    "amazon": {"min": 3, "ideal": 5, "max": 7},
    "ebay": {"min": 3, "ideal": 5, "max": 10},
    "shopify": {"min": 3, "ideal": 5, "max": 8},
    "walmart": {"min": 3, "ideal": 5, "max": 7},
    "etsy": {"min": 2, "ideal": 5, "max": 7},
    "aliexpress": {"min": 3, "ideal": 6, "max": 10},
}

CONVERSION_WORDS = {
    "en": [
        "buy now", "add to cart", "order today", "shop now", "get yours",
        "limited time", "sale", "discount", "free shipping", "guarantee",
        "money back", "best seller", "top rated", "award winning",
        "customer favorite", "as seen on", "trending", "new arrival",
    ],
    "cn": [
        "立即购买", "加入购物车", "限时优惠", "包邮", "满减",
        "爆款", "热销", "好评如潮", "品质保证", "正品保障",
        "退换无忧", "新品上市", "厂家直销", "特价",
    ],
}

MOBILE_ISSUES = [
    (r'(?:\S{60,})', "Very long words/URLs may break mobile layout"),
    (r'(?:={5,}|-{5,}|\*{5,})', "Decorative lines may not render well on mobile"),
]


def _detect_language(text: str) -> str:
    """Detect if text is primarily Chinese or English."""
    cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    en_chars = len(re.findall(r'[a-zA-Z]', text))
    return "cn" if cn_chars > en_chars else "en"


def _extract_title(text: str) -> str:
    """Try to extract the title from listing text."""
    patterns = [
        r'\*\*(?:title|标题|product\s*name|seo\s*title)\*\*\s*[:：]?\s*(.+?)(?:\n|$)',
        r'^(.+?)(?:\n|$)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            title = m.group(1).strip()
            if len(title) > 10:
                return title
    return ""


def _extract_bullets(text: str) -> list[str]:
    """Extract bullet points from listing text."""
    bullets = []

    # Pattern 1: **Bullet Points** section
    bp_match = re.search(
        r'\*\*(?:bullet\s*points?|features?|特点|卖点|要点)\*\*\s*[:：]?\s*(.*?)(?=\*\*[^*]|\Z)',
        text, re.IGNORECASE | re.DOTALL
    )
    if bp_match:
        section = bp_match.group(1)
        bullets = re.findall(r'^\s*[-•*✅✓→►]\s*(.+)', section, re.MULTILINE)
        if not bullets:
            bullets = re.findall(r'^\s*\d+[.)]\s*(.+)', section, re.MULTILINE)

    # Pattern 2: any bullets in text
    if not bullets:
        bullets = re.findall(r'^\s*[-•*]\s*(.+)', text, re.MULTILINE)

    return [b.strip() for b in bullets if len(b.strip()) > 5]


def _extract_description(text: str) -> str:
    """Extract description section."""
    desc_match = re.search(
        r'\*\*(?:description|描述|product\s*description|详情)\*\*\s*[:：]?\s*(.*?)(?=\*\*[^*]|\Z)',
        text, re.IGNORECASE | re.DOTALL
    )
    if desc_match:
        return desc_match.group(1).strip()
    return text


def grade_title(text: str, platform: str = "amazon") -> GradeDetail:
    """Grade the listing title."""
    gd = GradeDetail(
        criterion="📝 Title Quality",
        score=0.0,
        weight=0.20,
        passed=False,
    )

    title = _extract_title(text)
    if not title:
        gd.score = 10
        gd.notes.append("No title detected")
        return gd

    limits = TITLE_LENGTH.get(platform.lower(), TITLE_LENGTH["amazon"])
    title_len = len(title)

    # Length check
    if limits["ideal_min"] <= title_len <= limits["ideal_max"]:
        gd.score += 40
        gd.notes.append(f"Title length ({title_len}) is ideal ✓")
    elif limits["min"] <= title_len <= limits["max"]:
        gd.score += 25
        gd.notes.append(f"Title length ({title_len}) is acceptable")
    elif title_len < limits["min"]:
        gd.score += 10
        gd.notes.append(f"Title too short ({title_len} chars, min: {limits['min']})")
    else:
        gd.score += 15
        gd.notes.append(f"Title too long ({title_len} chars, max: {limits['max']})")

    # Capitalization check (English only)
    lang = _detect_language(title)
    if lang == "en":
        words = title.split()
        cap_words = sum(1 for w in words if w[0:1].isupper())
        if cap_words / max(len(words), 1) > 0.6:
            gd.score += 15
            gd.notes.append("Good title capitalization")
        else:
            gd.score += 5
            gd.notes.append("Consider capitalizing key words")

    # Special characters check
    special = re.findall(r'[|,\-–—/]', title)
    if len(special) > 5:
        gd.notes.append("Too many separators — may look spammy")
    elif 1 <= len(special) <= 3:
        gd.score += 15
        gd.notes.append("Good use of separators for readability")
    else:
        gd.score += 10

    # Brand mention
    has_brand = bool(re.search(r'^[A-Z][a-zA-Z]+\s', title))
    if has_brand:
        gd.score += 15
        gd.notes.append("Brand name at beginning ✓")
    else:
        gd.score += 5
        gd.notes.append("Consider adding brand name at start")

    # Key features in title
    feature_words = ["with", "for", "includes", "featuring", "compatible", "pack", "set"]
    features_found = sum(1 for fw in feature_words if fw.lower() in title.lower())
    if features_found >= 2:
        gd.score += 15
        gd.notes.append(f"{features_found} feature descriptors in title ✓")
    elif features_found >= 1:
        gd.score += 10

    gd.score = min(100, gd.score)
    gd.passed = gd.score >= 60
    return gd


def grade_bullets(text: str, platform: str = "amazon") -> GradeDetail:
    """Grade bullet points quality."""
    gd = GradeDetail(
        criterion="🔹 Bullet Points",
        score=0.0,
        weight=0.20,
        passed=False,
    )

    bullets = _extract_bullets(text)
    targets = BULLET_COUNT.get(platform.lower(), BULLET_COUNT["amazon"])

    if not bullets:
        gd.score = 10
        gd.notes.append("No bullet points detected")
        return gd

    # Count check
    if bullets and len(bullets) >= targets["ideal"]:
        gd.score += 30
        gd.notes.append(f"{len(bullets)} bullets (ideal: {targets['ideal']}) ✓")
    elif len(bullets) >= targets["min"]:
        gd.score += 20
        gd.notes.append(f"{len(bullets)} bullets (could add more, ideal: {targets['ideal']})")
    else:
        gd.score += 10
        gd.notes.append(f"Only {len(bullets)} bullets (min: {targets['min']})")

    # Length consistency
    lengths = [len(b) for b in bullets]
    avg_len = sum(lengths) / max(len(lengths), 1)
    if avg_len >= 80:
        gd.score += 20
        gd.notes.append(f"Good detail level (avg {avg_len:.0f} chars/bullet)")
    elif avg_len >= 40:
        gd.score += 10
        gd.notes.append(f"Moderate detail (avg {avg_len:.0f} chars — aim for 80+)")
    else:
        gd.score += 5
        gd.notes.append(f"Thin bullets (avg {avg_len:.0f} chars — add more detail)")

    # Check if bullets start with capitalized words or benefit-led
    benefit_starters = 0
    for b in bullets:
        if re.match(r'^[A-Z【🔹✅]', b):
            benefit_starters += 1
    if benefit_starters == len(bullets):
        gd.score += 20
        gd.notes.append("All bullets start strong ✓")
    elif benefit_starters > len(bullets) / 2:
        gd.score += 10

    # Variety check (no duplicate starts)
    starts = [b[:20].lower() for b in bullets]
    if len(set(starts)) == len(starts):
        gd.score += 15
        gd.notes.append("Good variety across bullets ✓")
    else:
        gd.score += 5
        gd.notes.append("Some bullets start similarly — diversify")

    # Keyword integration
    all_text = " ".join(bullets).lower()
    word_count = len(all_text.split())
    unique_words = len(set(all_text.split()))
    if unique_words / max(word_count, 1) > 0.5:
        gd.score += 15
    else:
        gd.score += 5

    gd.score = min(100, gd.score)
    gd.passed = gd.score >= 60
    return gd


def grade_description(text: str) -> GradeDetail:
    """Grade description quality."""
    gd = GradeDetail(
        criterion="📄 Description",
        score=0.0,
        weight=0.15,
        passed=False,
    )

    desc = _extract_description(text)
    if not desc or len(desc) < 20:
        gd.score = 10
        gd.notes.append("No substantial description found")
        return gd

    word_count = len(re.findall(r'[\w\u4e00-\u9fff]+', desc))

    # Length
    if word_count >= 200:
        gd.score += 25
        gd.notes.append(f"Good description length ({word_count} words) ✓")
    elif word_count >= 100:
        gd.score += 15
        gd.notes.append(f"Moderate description ({word_count} words — aim for 200+)")
    else:
        gd.score += 5
        gd.notes.append(f"Short description ({word_count} words)")

    # Formatting
    has_bold = bool(re.search(r'\*\*.+?\*\*', desc))
    has_bullets = bool(re.search(r'^\s*[-•*]\s', desc, re.MULTILINE))
    has_headers = bool(re.search(r'^\s*#{1,3}\s', desc, re.MULTILINE))
    formatting_count = sum([has_bold, has_bullets, has_headers])
    if formatting_count >= 2:
        gd.score += 20
        gd.notes.append("Well-formatted with structure ✓")
    elif formatting_count >= 1:
        gd.score += 10
        gd.notes.append("Some formatting — add more structure")
    else:
        gd.score += 5
        gd.notes.append("No formatting — add bold, bullets, headers")

    # Paragraph structure
    paragraphs = [p for p in desc.split("\n\n") if p.strip()]
    if len(paragraphs) >= 3:
        gd.score += 20
        gd.notes.append(f"{len(paragraphs)} paragraphs — good structure ✓")
    elif len(paragraphs) >= 2:
        gd.score += 10
    else:
        gd.score += 5
        gd.notes.append("Single block of text — break into paragraphs")

    # Emotional/persuasive language
    lang = _detect_language(desc)
    conv_words = CONVERSION_WORDS.get(lang, CONVERSION_WORDS["en"])
    found_conv = sum(1 for cw in conv_words if cw.lower() in desc.lower())
    if found_conv >= 3:
        gd.score += 20
        gd.notes.append(f"{found_conv} conversion triggers found ✓")
    elif found_conv >= 1:
        gd.score += 10
    else:
        gd.score += 5
        gd.notes.append("Add persuasive/conversion language")

    # Sentence variety
    sentences = re.split(r'[.!?。！？]+', desc)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    if len(sentences) >= 5:
        lengths = [len(s.split()) for s in sentences]
        std_dev = (sum((l - sum(lengths) / len(lengths)) ** 2 for l in lengths) / len(lengths)) ** 0.5
        if std_dev > 3:
            gd.score += 15
            gd.notes.append("Good sentence length variety ✓")
        else:
            gd.score += 5
            gd.notes.append("Monotonous sentence lengths — vary for readability")

    gd.score = min(100, gd.score)
    gd.passed = gd.score >= 60
    return gd


def grade_conversion_elements(text: str) -> GradeDetail:
    """Grade conversion optimization elements."""
    gd = GradeDetail(
        criterion="💰 Conversion Elements",
        score=0.0,
        weight=0.20,
        passed=False,
    )

    text_lower = text.lower()
    lang = _detect_language(text)

    # Call to action
    cta_patterns = [
        r'buy\s+now', r'add\s+to\s+cart', r'order\s+today', r'shop\s+now',
        r'get\s+yours', r'try\s+it', r'start\s+now',
        r'立即购买', r'加入购物车', r'立刻下单', r'马上抢购',
    ]
    has_cta = any(re.search(p, text_lower) for p in cta_patterns)
    if has_cta:
        gd.score += 20
        gd.notes.append("Call-to-action present ✓")
    else:
        gd.notes.append("Missing call-to-action (buy now, add to cart, etc.)")

    # Social proof
    social_patterns = [
        r'\d+[,.]?\d*\s*(?:reviews?|ratings?|stars?|customers?)',
        r'best\s*sell(?:er|ing)', r'top\s*rated', r'#\d+',
        r'好评\d+', r'热销\d+', r'销量\d+', r'★',
    ]
    has_social = any(re.search(p, text_lower) for p in social_patterns)
    if has_social:
        gd.score += 15
        gd.notes.append("Social proof elements found ✓")
    else:
        gd.notes.append("Add social proof (ratings, reviews, bestseller badge)")

    # Urgency/scarcity
    urgency_patterns = [
        r'limited\s*(time|stock|edition|supply)', r'only\s*\d+\s*left',
        r'sale\s*ends?', r'while\s*supplies?\s*last', r'hurry',
        r'限时', r'仅剩', r'秒杀', r'抢购', r'最后',
    ]
    has_urgency = any(re.search(p, text_lower) for p in urgency_patterns)
    if has_urgency:
        gd.score += 15
        gd.notes.append("Urgency/scarcity elements ✓")

    # Trust signals
    trust_patterns = [
        r'guarantee', r'warranty', r'money\s*back', r'certified',
        r'authentic', r'official', r'free\s*(?:shipping|return)',
        r'保障', r'质保', r'正品', r'包邮', r'退换',
    ]
    has_trust = any(re.search(p, text_lower) for p in trust_patterns)
    if has_trust:
        gd.score += 15
        gd.notes.append("Trust signals present ✓")
    else:
        gd.notes.append("Add trust signals (guarantee, warranty, certified)")

    # Value proposition
    value_patterns = [
        r'save\s+\d+%', r'\d+%\s*off', r'free\s+(?:gift|bonus)',
        r'bundle', r'pack\s+of\s+\d+', r'includes?\s+\d+',
        r'折', r'优惠', r'赠品', r'套装', r'满减',
    ]
    has_value = any(re.search(p, text_lower) for p in value_patterns)
    if has_value:
        gd.score += 15
        gd.notes.append("Value proposition highlighted ✓")

    # Benefits vs features ratio
    benefit_words = ["helps", "makes", "allows", "enables", "improves",
                     "reduces", "saves", "protects", "prevents", "ensures",
                     "让", "帮助", "提升", "改善", "保护"]
    benefit_count = sum(1 for bw in benefit_words if bw in text_lower)
    if benefit_count >= 3:
        gd.score += 20
        gd.notes.append(f"Benefit-oriented language ({benefit_count} benefit words) ✓")
    elif benefit_count >= 1:
        gd.score += 10

    gd.score = min(100, gd.score)
    gd.passed = gd.score >= 60
    return gd


def grade_mobile_readiness(text: str) -> GradeDetail:
    """Grade mobile display readiness."""
    gd = GradeDetail(
        criterion="📱 Mobile Readiness",
        score=80.0,
        weight=0.10,
        passed=True,
    )

    # Check for very long lines
    lines = text.split("\n")
    long_lines = [i for i, l in enumerate(lines, 1) if len(l) > 120]
    if long_lines:
        gd.score -= 15
        gd.notes.append(f"{len(long_lines)} lines exceed 120 chars (may wrap poorly)")

    # Check for mobile-unfriendly patterns
    for pattern, warning in MOBILE_ISSUES:
        if re.search(pattern, text):
            gd.score -= 10
            gd.notes.append(warning)

    # Short paragraphs (good for mobile)
    paragraphs = [p for p in text.split("\n") if p.strip()]
    short_paras = sum(1 for p in paragraphs if len(p) < 200)
    if short_paras / max(len(paragraphs), 1) > 0.6:
        gd.score += 10
        gd.notes.append("Good paragraph sizing for mobile ✓")

    # Emoji usage (improves mobile scanability)
    emoji_count = len(re.findall(r'[\U0001F300-\U0001F9FF]', text))
    if emoji_count >= 3:
        gd.score += 10
        gd.notes.append(f"Emoji used ({emoji_count}) — good for mobile scanning ✓")
    elif emoji_count >= 1:
        gd.score += 5

    gd.score = max(0, min(100, gd.score))
    gd.passed = gd.score >= 60
    return gd


def grade_seo_compliance(text: str, platform: str = "amazon") -> GradeDetail:
    """Grade SEO compliance for the platform."""
    gd = GradeDetail(
        criterion="🔍 SEO Compliance",
        score=0.0,
        weight=0.15,
        passed=False,
    )

    text_lower = text.lower()

    # Backend keywords / search terms section
    has_search_terms = bool(re.search(
        r'\*\*(?:search\s*terms?|backend\s*keywords?|标签|关键词)\*\*',
        text, re.IGNORECASE
    ))
    if has_search_terms:
        gd.score += 20
        gd.notes.append("Search terms section present ✓")
    else:
        gd.notes.append("Missing search terms / backend keywords section")

    # No keyword stuffing (basic check)
    words = re.findall(r'[\w\u4e00-\u9fff]+', text_lower)
    if words:
        from collections import Counter
        freq = Counter(words)
        top_word, top_count = freq.most_common(1)[0]
        top_density = top_count / len(words) * 100
        if top_density > 5:
            gd.notes.append(f"⚠️ '{top_word}' appears at {top_density:.1f}% density — may be stuffing")
        else:
            gd.score += 20
            gd.notes.append("No keyword stuffing detected ✓")

    # Title optimization
    title = _extract_title(text)
    if title:
        title_words = len(title.split())
        if title_words >= 5:
            gd.score += 15
            gd.notes.append(f"Title has {title_words} words — keyword-rich ✓")
        else:
            gd.score += 5
            gd.notes.append("Title too short for SEO")

    # Alt text hints (for image descriptions)
    has_alt = bool(re.search(r'\*\*(?:image|alt|图片)\*\*', text, re.IGNORECASE))
    if has_alt:
        gd.score += 10
        gd.notes.append("Image/alt text descriptions present ✓")

    # Meta description (for Shopify/web)
    if platform.lower() in ("shopify", "独立站"):
        has_meta = bool(re.search(r'\*\*meta\s*description\*\*', text, re.IGNORECASE))
        if has_meta:
            gd.score += 15
            gd.notes.append("Meta description present ✓")
        else:
            gd.notes.append("Missing meta description")
    else:
        gd.score += 15  # Not applicable, give full marks

    # Content depth
    total_words = len(words)
    if total_words >= 300:
        gd.score += 20
        gd.notes.append(f"Good content depth ({total_words} words) ✓")
    elif total_words >= 150:
        gd.score += 10
        gd.notes.append(f"Moderate content ({total_words} words — aim for 300+)")
    else:
        gd.score += 5
        gd.notes.append(f"Thin content ({total_words} words)")

    gd.score = min(100, gd.score)
    gd.passed = gd.score >= 60
    return gd


def grade_listing(
    text: str,
    platform: str = "amazon",
    target_keywords: Optional[list[str]] = None,
) -> ListingGrade:
    """Generate comprehensive listing grade.

    Args:
        text: Full listing text.
        platform: Target marketplace platform.
        target_keywords: Optional keywords for density checking.

    Returns:
        ListingGrade with detailed breakdown.
    """
    criteria = [
        grade_title(text, platform),
        grade_bullets(text, platform),
        grade_description(text),
        grade_conversion_elements(text),
        grade_mobile_readiness(text),
        grade_seo_compliance(text, platform),
    ]

    total_score = sum(c.weighted_score for c in criteria)
    total_score = min(100, total_score)

    # Letter grade
    if total_score >= 90:
        letter = "A+"
    elif total_score >= 80:
        letter = "A"
    elif total_score >= 70:
        letter = "B+"
    elif total_score >= 60:
        letter = "B"
    elif total_score >= 50:
        letter = "C"
    elif total_score >= 40:
        letter = "D"
    else:
        letter = "F"

    # Strengths (criteria scoring 80+)
    strengths = []
    for c in criteria:
        if c.score >= 80:
            strengths.append(f"{c.criterion} ({c.score:.0f}/100)")

    # Weaknesses (criteria scoring below 50)
    weaknesses = []
    for c in criteria:
        if c.score < 50:
            weaknesses.append(f"{c.criterion} ({c.score:.0f}/100)")

    # Quick wins (highest weight items with lowest scores)
    scored = sorted(criteria, key=lambda c: c.score)
    quick_wins = []
    for c in scored[:3]:
        if c.score < 80:
            for note in c.notes:
                if not note.startswith("✓") and "✓" not in note:
                    quick_wins.append(note)
                    break

    # Competitive readiness
    if total_score >= 85:
        competitive = "strong"
    elif total_score >= 70:
        competitive = "ready"
    elif total_score >= 55:
        competitive = "almost"
    else:
        competitive = "not ready"

    return ListingGrade(
        total_score=round(total_score, 1),
        letter_grade=letter,
        criteria=criteria,
        strengths=strengths,
        weaknesses=weaknesses,
        quick_wins=quick_wins[:5],
        competitive_readiness=competitive,
    )
