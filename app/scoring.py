"""SEO scoring engine for product listings.

Scores listings on multiple dimensions:
- Readability (sentence length, complexity)
- Keyword optimization (density, placement, variety)
- Completeness (all sections filled, proper length)
- Emotional appeal (power words, urgency, social proof)
- Technical SEO (structured data hints, meta compliance)
"""
import re
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScoreDimension:
    name: str
    score: float  # 0-100
    weight: float  # 0-1
    details: list[str] = field(default_factory=list)

    @property
    def weighted(self) -> float:
        return self.score * self.weight


@dataclass
class SEOScore:
    dimensions: list[ScoreDimension] = field(default_factory=list)

    @property
    def total(self) -> float:
        if not self.dimensions:
            return 0.0
        return round(sum(d.weighted for d in self.dimensions), 1)

    @property
    def grade(self) -> str:
        t = self.total
        if t >= 90:
            return "A+"
        if t >= 80:
            return "A"
        if t >= 70:
            return "B"
        if t >= 60:
            return "C"
        if t >= 50:
            return "D"
        return "F"

    def summary(self) -> str:
        lines = [f"📊 SEO Score: {self.total}/100 (Grade: {self.grade})", ""]
        for d in sorted(self.dimensions, key=lambda x: x.weighted, reverse=True):
            bar = "█" * int(d.score / 10) + "░" * (10 - int(d.score / 10))
            lines.append(f"  {d.name}: {d.score:.0f}/100 [{bar}] (×{d.weight})")
            for detail in d.details:
                lines.append(f"    → {detail}")
        return "\n".join(lines)


# ── Power Words ────────────────────────────────────────────

POWER_WORDS_EN = {
    "urgency": {"now", "today", "limited", "hurry", "instant", "fast", "quick", "rush", "deadline", "last chance"},
    "exclusivity": {"exclusive", "premium", "elite", "rare", "unique", "custom", "bespoke", "limited edition", "one-of-a-kind"},
    "value": {"free", "save", "bonus", "deal", "bargain", "affordable", "discount", "value", "guarantee", "best"},
    "trust": {"proven", "certified", "authentic", "genuine", "official", "trusted", "tested", "verified", "safe", "reliable"},
    "emotion": {"love", "amazing", "incredible", "perfect", "beautiful", "stunning", "gorgeous", "brilliant", "powerful", "revolutionary"},
}

POWER_WORDS_CN = {
    "urgency": {"限时", "秒杀", "抢购", "最后", "立即", "火爆", "热销", "疯抢", "倒计时", "仅剩"},
    "exclusivity": {"独家", "定制", "尊享", "专属", "限量", "奢华", "高端", "私人", "稀有"},
    "value": {"免费", "特价", "折扣", "超值", "划算", "赠品", "包邮", "满减", "优惠"},
    "trust": {"正品", "认证", "保障", "质保", "售后", "品牌", "官方", "进口", "原装", "安全"},
    "emotion": {"爆款", "网红", "必备", "神器", "推荐", "好评", "满意", "惊喜", "完美", "舒适"},
}


def _count_sentences(text: str) -> int:
    """Rough sentence count."""
    sents = re.split(r'[.!?。！？\n]+', text)
    return max(1, len([s for s in sents if s.strip()]))


def _avg_sentence_length(text: str) -> float:
    """Average words per sentence."""
    sents = re.split(r'[.!?。！？\n]+', text)
    sents = [s.strip() for s in sents if s.strip()]
    if not sents:
        return 0.0
    total_words = sum(len(re.findall(r'[\w\u4e00-\u9fff]+', s)) for s in sents)
    return total_words / len(sents)


def _is_chinese(text: str) -> bool:
    """Detect if text is primarily Chinese."""
    cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    en_chars = len(re.findall(r'[a-zA-Z]', text))
    return cn_chars > en_chars


def score_readability(text: str) -> ScoreDimension:
    """Score readability based on sentence structure and complexity."""
    dim = ScoreDimension(name="📖 Readability", score=100.0, weight=0.2)

    avg_len = _avg_sentence_length(text)
    sent_count = _count_sentences(text)
    word_count = len(re.findall(r'[\w\u4e00-\u9fff]+', text))

    # Optimal avg sentence length: 12-20 words
    if avg_len < 8:
        dim.score -= 15
        dim.details.append(f"Sentences too short (avg {avg_len:.1f} words)")
    elif avg_len > 25:
        dim.score -= 20
        dim.details.append(f"Sentences too long (avg {avg_len:.1f} words) — aim for 15-20")
    else:
        dim.details.append(f"Good sentence length (avg {avg_len:.1f} words)")

    # Check paragraph structure (line breaks)
    paragraphs = [p for p in text.split("\n") if p.strip()]
    if len(paragraphs) < 3:
        dim.score -= 10
        dim.details.append("Too few paragraphs — break up content")
    else:
        dim.details.append(f"{len(paragraphs)} paragraphs — good structure")

    # Check formatting (bold, bullets)
    has_bold = bool(re.search(r'\*\*.+?\*\*', text))
    has_bullets = bool(re.search(r'^[\s]*[-•*]\s', text, re.MULTILINE))
    has_numbers = bool(re.search(r'^[\s]*\d+[.)]\s', text, re.MULTILINE))
    formatting_score = sum([has_bold, has_bullets, has_numbers])
    if formatting_score == 0:
        dim.score -= 15
        dim.details.append("No formatting detected — add bold, bullets, or numbered lists")
    elif formatting_score >= 2:
        dim.details.append("Good use of formatting elements")

    dim.score = max(0, dim.score)
    return dim


def score_keywords(text: str, target_keywords: Optional[list[str]] = None) -> ScoreDimension:
    """Score keyword optimization."""
    dim = ScoreDimension(name="🔑 Keywords", score=100.0, weight=0.25)

    words = re.findall(r'[\w\u4e00-\u9fff]+', text.lower())
    word_count = len(words)

    if word_count < 50:
        dim.score -= 20
        dim.details.append(f"Content too thin ({word_count} words) — aim for 200+")
    elif word_count > 200:
        dim.details.append(f"Good content depth ({word_count} words)")

    if target_keywords:
        found = 0
        for kw in target_keywords:
            if kw.lower() in text.lower():
                found += 1
        ratio = found / len(target_keywords)
        if ratio < 0.3:
            dim.score -= 25
            dim.details.append(f"Only {found}/{len(target_keywords)} target keywords found")
        elif ratio < 0.6:
            dim.score -= 10
            dim.details.append(f"{found}/{len(target_keywords)} target keywords (could improve)")
        else:
            dim.details.append(f"{found}/{len(target_keywords)} target keywords present ✓")

        # Check keyword in title
        sections = _extract_bold_sections(text)
        title_text = ""
        for key in ["title", "标题", "product name", "seo title"]:
            for sk, sv in sections.items():
                if key in sk:
                    title_text = sv
                    break
            if title_text:
                break

        if title_text and target_keywords:
            kw_in_title = sum(1 for kw in target_keywords if kw.lower() in title_text.lower())
            if kw_in_title == 0:
                dim.score -= 15
                dim.details.append("No target keywords in title!")
            else:
                dim.details.append(f"{kw_in_title} keywords in title ✓")
    else:
        # Auto-detect keyword variety
        from collections import Counter
        freq = Counter(words)
        unique_ratio = len(freq) / max(word_count, 1)
        if unique_ratio < 0.3:
            dim.score -= 15
            dim.details.append("Low keyword variety — use more synonyms")
        else:
            dim.details.append(f"Keyword variety: {unique_ratio:.0%}")

    dim.score = max(0, dim.score)
    return dim


def score_completeness(text: str, platform: str = "amazon") -> ScoreDimension:
    """Score listing completeness for a platform."""
    dim = ScoreDimension(name="📋 Completeness", score=100.0, weight=0.25)

    sections = _extract_bold_sections(text)

    from app.validator import PLATFORM_RULES
    rules = PLATFORM_RULES.get(platform.lower(), {})
    required = rules.get("required_sections", [])

    if required:
        found = 0
        for req in required:
            if any(req in k for k in sections):
                found += 1
        ratio = found / len(required)
        if ratio <= 0.25:
            dim.score -= 40
            dim.details.append(f"Only {found}/{len(required)} required sections (severely incomplete)")
        elif ratio < 0.5:
            dim.score -= 30
            dim.details.append(f"Only {found}/{len(required)} required sections")
        elif ratio < 1.0:
            dim.score -= 15
            dim.details.append(f"{found}/{len(required)} sections (missing some)")
        else:
            dim.details.append(f"All {len(required)} required sections present ✓")
    else:
        # Generic check: at least 3 sections
        if len(sections) < 3:
            dim.score -= 20
            dim.details.append(f"Only {len(sections)} sections — add more")
        else:
            dim.details.append(f"{len(sections)} sections detected ✓")

    # Content depth per section
    thin_sections = [k for k, v in sections.items() if len(v.strip()) < 30]
    if thin_sections:
        dim.score -= 5 * len(thin_sections)
        dim.details.append(f"{len(thin_sections)} thin sections need more content")

    dim.score = max(0, dim.score)
    return dim


def score_emotional_appeal(text: str) -> ScoreDimension:
    """Score emotional/persuasive language usage."""
    dim = ScoreDimension(name="💡 Emotional Appeal", score=50.0, weight=0.15)

    is_cn = _is_chinese(text)
    power_words = POWER_WORDS_CN if is_cn else POWER_WORDS_EN

    total_found = 0
    categories_hit = 0
    for category, words in power_words.items():
        found = [w for w in words if w.lower() in text.lower()]
        if found:
            categories_hit += 1
            total_found += len(found)
            dim.details.append(f"{category}: {', '.join(found[:3])}")

    # Score based on variety of power word categories
    if categories_hit >= 4:
        dim.score = 95
        dim.details.insert(0, "Excellent persuasive language variety")
    elif categories_hit >= 3:
        dim.score = 80
        dim.details.insert(0, "Good emotional appeal")
    elif categories_hit >= 2:
        dim.score = 65
    elif categories_hit >= 1:
        dim.score = 50
        dim.details.insert(0, "Limited emotional appeal — add more power words")
    else:
        dim.score = 30
        dim.details.insert(0, "No power words detected — listing may feel flat")

    # Check for call-to-action
    cta_patterns = [
        r'buy\s+now', r'add\s+to\s+cart', r'order\s+today', r'shop\s+now',
        r'get\s+yours', r'don\'t\s+miss', r'click', r'grab',
        r'立即购买', r'加入购物车', r'立刻下单', r'马上抢购',
    ]
    has_cta = any(re.search(p, text, re.IGNORECASE) for p in cta_patterns)
    if has_cta:
        dim.score = min(100, dim.score + 5)
        dim.details.append("Call-to-action detected ✓")

    dim.score = max(0, min(100, dim.score))
    return dim


def score_technical_seo(text: str, platform: str = "amazon") -> ScoreDimension:
    """Score technical SEO compliance."""
    dim = ScoreDimension(name="⚙️ Technical SEO", score=100.0, weight=0.15)

    # Check for meta-like elements (for web platforms)
    if platform.lower() in ("独立站", "shopify"):
        has_meta_desc = bool(re.search(r'\*\*meta\s+description\*\*', text, re.IGNORECASE))
        has_seo_title = bool(re.search(r'\*\*seo\s+title\*\*', text, re.IGNORECASE))
        has_faq = bool(re.search(r'\*\*faq\*\*', text, re.IGNORECASE))

        if not has_seo_title:
            dim.score -= 20
            dim.details.append("Missing SEO title")
        if not has_meta_desc:
            dim.score -= 20
            dim.details.append("Missing meta description")
        if not has_faq:
            dim.score -= 10
            dim.details.append("No FAQ section (good for schema markup)")
        if has_seo_title and has_meta_desc:
            dim.details.append("SEO title + meta description present ✓")
    else:
        # For marketplace platforms, check search terms / keywords
        has_keywords = bool(
            re.search(r'\*\*(search\s+terms|keywords|标签|backend)\*\*', text, re.IGNORECASE)
        )
        if has_keywords:
            dim.details.append("Keyword/search terms section present ✓")
        else:
            dim.score -= 15
            dim.details.append("Missing keyword/search terms section")

    # Check for HTML tags (good for platforms that support it)
    has_html = bool(re.search(r'<[a-zA-Z]+[^>]*>', text))
    if has_html:
        dim.details.append("HTML formatting detected")

    # Check total length
    total_len = len(text)
    if total_len < 200:
        dim.score -= 20
        dim.details.append(f"Listing too short ({total_len} chars)")
    elif total_len > 500:
        dim.details.append(f"Good content length ({total_len} chars)")

    dim.score = max(0, dim.score)
    return dim


def _extract_bold_sections(text: str) -> dict[str, str]:
    """Extract **Section Name** blocks."""
    sections = {}
    pattern = r'\*\*(.+?)\*\*\s*(?:\(.*?\))?\s*[:：]?\s*(.*?)(?=\*\*[^*]|\Z)'
    for m in re.finditer(pattern, text, re.DOTALL):
        key = m.group(1).strip().lower()
        val = m.group(2).strip()
        sections[key] = val
    return sections


def score_listing(
    text: str,
    platform: str = "amazon",
    target_keywords: Optional[list[str]] = None,
) -> SEOScore:
    """Generate a comprehensive SEO score for a listing.

    Args:
        text: The full listing text.
        platform: Target platform.
        target_keywords: Optional list of target keywords to check against.

    Returns:
        SEOScore with breakdown by dimension.
    """
    seo = SEOScore()
    seo.dimensions = [
        score_readability(text),
        score_keywords(text, target_keywords),
        score_completeness(text, platform),
        score_emotional_appeal(text),
        score_technical_seo(text, platform),
    ]
    return seo
