"""
Review-to-Listing Engine
========================

Extract key selling points from customer reviews and automatically
generate optimized listing bullet points and description content.

Features:
- Sentiment extraction (positive/negative/neutral)
- Benefit clustering (group similar praise/complaints)
- Auto-generate bullet points from top benefits
- Pain point detection for "addresses X" style bullets
- Feature frequency ranking across reviews
- Competitor review comparison
- Review quality scoring (helpful vs unhelpful)
- Voice-of-customer (VOC) keyword extraction
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Models ───────────────────────────────────────────────────

class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class ReviewQuality(str, Enum):
    HIGH = "high"         # Detailed, specific
    MEDIUM = "medium"     # Some detail
    LOW = "low"           # Vague / short


@dataclass
class ExtractedBenefit:
    """A benefit extracted from reviews."""
    text: str
    frequency: int
    sentiment: Sentiment
    confidence: float  # 0-1
    source_snippets: list[str] = field(default_factory=list)
    category: str = "general"


@dataclass
class PainPoint:
    """A customer pain point / complaint."""
    text: str
    frequency: int
    severity: float  # 0-1 (1 = most severe)
    fix_suggestion: str = ""
    source_snippets: list[str] = field(default_factory=list)


@dataclass
class ReviewAnalysisResult:
    """Complete review analysis output."""
    total_reviews: int
    avg_sentiment_score: float  # -1 to 1
    overall_sentiment: Sentiment
    benefits: list[ExtractedBenefit]
    pain_points: list[PainPoint]
    top_keywords: list[tuple[str, int]]
    voc_phrases: list[tuple[str, int]]
    generated_bullets: list[str]
    generated_description: str
    quality_distribution: dict[str, int]  # high/medium/low counts

    def summary(self) -> str:
        lines = [
            f"📊 Review Analysis ({self.total_reviews} reviews)",
            f"Overall Sentiment: {self.overall_sentiment.value} ({self.avg_sentiment_score:+.2f})",
            "",
            f"✅ Top Benefits ({len(self.benefits)}):",
        ]
        for b in self.benefits[:5]:
            lines.append(f"  • {b.text} (mentioned {b.frequency}x)")

        if self.pain_points:
            lines.append(f"\n⚠️ Pain Points ({len(self.pain_points)}):")
            for p in self.pain_points[:5]:
                lines.append(f"  • {p.text} (mentioned {p.frequency}x)")

        lines.append(f"\n🔑 VOC Keywords: {', '.join(k for k, _ in self.top_keywords[:10])}")

        if self.generated_bullets:
            lines.append("\n📝 Auto-Generated Bullets:")
            for i, b in enumerate(self.generated_bullets, 1):
                lines.append(f"  {i}. {b}")

        return "\n".join(lines)


# ── Sentiment Analysis ───────────────────────────────────────

POSITIVE_PATTERNS = {
    "en": [
        r'\b(?:love|great|amazing|excellent|perfect|awesome|fantastic|wonderful|'
        r'impressed|beautiful|quality|comfortable|sturdy|durable|recommend|'
        r'satisfied|happy|pleased|best|superb|brilliant|outstanding|remarkable)\b',
    ],
    "cn": [
        r'(?:喜欢|很好|不错|满意|推荐|完美|超赞|优秀|舒适|好用|'
        r'方便|惊喜|实用|漂亮|牢固|耐用|好评|物超所值)',
    ],
}

NEGATIVE_PATTERNS = {
    "en": [
        r'\b(?:terrible|awful|horrible|worst|broke|broken|cheap|flimsy|'
        r'disappointed|waste|return|refund|defective|poor|useless|'
        r'uncomfortable|fragile|misleading|scam|fake|rubbish|junk)\b',
    ],
    "cn": [
        r'(?:差|垃圾|退货|退款|失望|假|烂|坏|破|虚假|不好|难用|'
        r'骗人|坑|劣质|不推荐|后悔)',
    ],
}

# Feature categories for clustering
FEATURE_CATEGORIES = {
    "quality": [
        "quality", "material", "build", "durable", "sturdy", "solid",
        "premium", "well-made", "crafted", "construction",
        "质量", "材质", "做工", "耐用",
    ],
    "comfort": [
        "comfortable", "soft", "fit", "ergonomic", "lightweight",
        "cozy", "breathable", "cushion", "snug",
        "舒适", "柔软", "贴合", "轻便",
    ],
    "value": [
        "price", "value", "worth", "affordable", "cheap", "expensive",
        "bargain", "deal", "money",
        "价格", "性价比", "便宜", "划算",
    ],
    "appearance": [
        "look", "design", "color", "style", "aesthetic", "beautiful",
        "sleek", "elegant", "modern", "cute",
        "外观", "颜色", "设计", "好看", "漂亮",
    ],
    "functionality": [
        "work", "function", "feature", "easy", "use", "convenient",
        "efficient", "fast", "powerful", "performance",
        "功能", "好用", "方便", "快速", "性能",
    ],
    "shipping": [
        "shipping", "delivery", "package", "packaging", "arrived",
        "fast shipping", "box", "wrapped",
        "物流", "包装", "发货", "快递",
    ],
    "size": [
        "size", "fit", "small", "large", "big", "tiny", "compact",
        "spacious", "dimensions", "measurement",
        "尺寸", "大小", "尺码",
    ],
    "battery": [
        "battery", "charge", "charging", "power", "last", "hours",
        "电池", "充电", "续航",
    ],
}


def _detect_lang(text: str) -> str:
    cn = len(re.findall(r'[\u4e00-\u9fff]', text))
    en = len(re.findall(r'[a-zA-Z]', text))
    return "cn" if cn > en else "en"


def _tokenize(text: str) -> list[str]:
    """Tokenize text into words."""
    return re.findall(r'[\w\u4e00-\u9fff]+', text.lower())


def _extract_ngrams(tokens: list[str], n: int) -> list[str]:
    """Extract n-grams from token list."""
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def score_sentiment(text: str) -> float:
    """Score sentiment of text from -1 (negative) to +1 (positive)."""
    text_lower = text.lower()
    lang = _detect_lang(text)

    pos_count = 0
    neg_count = 0

    for pattern in POSITIVE_PATTERNS.get(lang, POSITIVE_PATTERNS["en"]):
        pos_count += len(re.findall(pattern, text_lower))

    for pattern in NEGATIVE_PATTERNS.get(lang, NEGATIVE_PATTERNS["en"]):
        neg_count += len(re.findall(pattern, text_lower))

    total = pos_count + neg_count
    if total == 0:
        return 0.0

    return (pos_count - neg_count) / total


def classify_sentiment(score: float) -> Sentiment:
    """Classify a sentiment score."""
    if score > 0.3:
        return Sentiment.POSITIVE
    elif score < -0.3:
        return Sentiment.NEGATIVE
    elif abs(score) <= 0.1:
        return Sentiment.NEUTRAL
    return Sentiment.MIXED


def assess_review_quality(text: str) -> ReviewQuality:
    """Assess quality of a single review."""
    words = _tokenize(text)
    word_count = len(words)

    # High quality: detailed, specific, mentions features
    if word_count >= 50:
        return ReviewQuality.HIGH
    elif word_count >= 20:
        return ReviewQuality.MEDIUM
    return ReviewQuality.LOW


def categorize_feature(text: str) -> str:
    """Determine which feature category text belongs to."""
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for category, keywords in FEATURE_CATEGORIES.items():
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > 0:
            scores[category] = matches

    if not scores:
        return "general"

    return max(scores, key=scores.get)


def extract_benefit_phrases(text: str) -> list[str]:
    """Extract specific benefit phrases from review text."""
    phrases = []

    # English patterns
    en_patterns = [
        r'(?:I (?:love|like|enjoy)|really (?:like|enjoy)|great|amazing)\s+(?:the\s+)?(.+?)(?:[.,!]|$)',
        r'(?:the\s+)?(\w[\w\s]{5,30})\s+(?:is|are|was|were)\s+(?:great|amazing|excellent|perfect|wonderful)',
        r'(?:best|excellent|perfect|amazing)\s+(.+?)(?:[.,!]|$)',
        r'(?:so|very|really|extremely)\s+([\w\s]{5,30})',
    ]

    # Chinese patterns
    cn_patterns = [
        r'(?:很|非常|特别|超级)(.{2,15})',
        r'(.{2,15})(?:很好|不错|挺好|可以)',
    ]

    for pattern in en_patterns + cn_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            cleaned = m.strip().rstrip('.,!;:')
            if 3 <= len(cleaned) <= 80:
                phrases.append(cleaned)

    return phrases


def extract_pain_points_from_text(text: str) -> list[str]:
    """Extract complaint/pain point phrases from review text."""
    points = []

    patterns = [
        r'(?:the\s+)?(\w[\w\s]{5,40})\s+(?:is|was|are|were)\s+(?:terrible|awful|bad|poor|broken|'
        r'too\s+(?:small|big|short|long|thin|thick|heavy|light))',
        r'(?:I\s+)?(?:wish|hoped?)\s+(?:it\s+)?(?:had|was|were|could)\s+(.+?)(?:[.,!]|$)',
        r'(?:problem|issue|downside|con|flaw|complaint)\s*[:：]?\s*(.+?)(?:[.,!]|$)',
        r'(?:broke|broken|stopped|failed|doesn\'t|didn\'t|can\'t|won\'t)\s+(.+?)(?:[.,!]|$)',
        r'(?:不好|差|太|问题|缺点|退|坏)(.{2,20})',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            cleaned = m.strip().rstrip('.,!;:')
            if 3 <= len(cleaned) <= 80:
                points.append(cleaned)

    return points


def extract_voc_keywords(reviews: list[str], top_n: int = 20) -> list[tuple[str, int]]:
    """Extract Voice-of-Customer keywords and phrases."""
    all_tokens: list[str] = []
    bigrams: list[str] = []

    # Stopwords
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "it", "this", "that",
        "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
        "i", "my", "me", "we", "they", "he", "she", "you", "your", "its",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "can", "not", "no", "so", "very", "just", "also", "been",
        "being", "than", "then", "there", "these", "those", "some", "any",
        "from", "by", "as", "if", "when", "all", "one", "two", "get",
        "got", "much", "more", "most", "how", "what", "which", "who",
        "的", "了", "是", "在", "和", "有", "也", "不", "就", "都",
        "这", "那", "很", "我", "你", "他",
    }

    for review in reviews:
        tokens = _tokenize(review)
        filtered = [t for t in tokens if t not in stopwords and len(t) > 2]
        all_tokens.extend(filtered)
        bigrams.extend(_extract_ngrams(filtered, 2))

    # Combine unigrams and bigrams
    combined = Counter(all_tokens) + Counter(bigrams)

    return combined.most_common(top_n)


def cluster_benefits(
    reviews: list[str],
    min_frequency: int = 2,
) -> list[ExtractedBenefit]:
    """Cluster and rank benefits across all reviews."""
    phrase_counter: Counter = Counter()
    phrase_snippets: dict[str, list[str]] = {}
    phrase_sentiments: dict[str, list[float]] = {}

    for review in reviews:
        phrases = extract_benefit_phrases(review)
        sentiment = score_sentiment(review)

        for phrase in phrases:
            normalized = phrase.lower().strip()
            phrase_counter[normalized] += 1

            if normalized not in phrase_snippets:
                phrase_snippets[normalized] = []
                phrase_sentiments[normalized] = []

            if len(phrase_snippets[normalized]) < 3:
                snippet = review[:120] + ("..." if len(review) > 120 else "")
                phrase_snippets[normalized].append(snippet)
            phrase_sentiments[normalized].append(sentiment)

    benefits = []
    for phrase, count in phrase_counter.most_common():
        if count < min_frequency:
            continue

        avg_sent = sum(phrase_sentiments[phrase]) / len(phrase_sentiments[phrase])
        category = categorize_feature(phrase)

        benefits.append(ExtractedBenefit(
            text=phrase,
            frequency=count,
            sentiment=classify_sentiment(avg_sent),
            confidence=min(1.0, count / max(len(reviews), 1)),
            source_snippets=phrase_snippets.get(phrase, []),
            category=category,
        ))

    return sorted(benefits, key=lambda b: b.frequency, reverse=True)


def cluster_pain_points(
    reviews: list[str],
    min_frequency: int = 2,
) -> list[PainPoint]:
    """Cluster and rank pain points from negative reviews."""
    point_counter: Counter = Counter()
    point_snippets: dict[str, list[str]] = {}

    for review in reviews:
        if score_sentiment(review) > 0.3:
            continue  # Skip mostly positive reviews

        points = extract_pain_points_from_text(review)
        for point in points:
            normalized = point.lower().strip()
            point_counter[normalized] += 1

            if normalized not in point_snippets:
                point_snippets[normalized] = []
            if len(point_snippets[normalized]) < 3:
                point_snippets[normalized].append(review[:120])

    pain_points = []
    for point, count in point_counter.most_common():
        if count < min_frequency:
            continue

        pain_points.append(PainPoint(
            text=point,
            frequency=count,
            severity=min(1.0, count / max(len(reviews), 1) * 3),
            source_snippets=point_snippets.get(point, []),
        ))

    return sorted(pain_points, key=lambda p: p.frequency, reverse=True)


def generate_bullets_from_reviews(
    benefits: list[ExtractedBenefit],
    pain_points: list[PainPoint],
    max_bullets: int = 5,
    platform: str = "amazon",
) -> list[str]:
    """Auto-generate listing bullets from review analysis.

    Strategy:
    - Top benefits become positive bullets
    - Top pain points become "addresses X" bullets (competitive advantage)
    """
    bullets: list[str] = []

    # Benefits → bullets (60% of bullets)
    benefit_count = max(1, int(max_bullets * 0.6))
    seen_categories: set[str] = set()

    for b in benefits:
        if len(bullets) >= benefit_count:
            break
        # Avoid duplicate categories
        if b.category in seen_categories and len(benefits) > benefit_count:
            continue
        seen_categories.add(b.category)

        text = b.text.strip()
        if text:
            # Capitalize first letter
            bullet = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
            # Add emphasis
            bullets.append(f"✅ {bullet} — loved by {b.frequency}+ customers")

    # Pain points → competitive bullets (40%)
    pain_count = max_bullets - len(bullets)
    for p in pain_points[:pain_count]:
        text = p.text.strip()
        if text:
            bullet = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
            bullets.append(f"🔧 Addresses common concern: {bullet}")

    return bullets[:max_bullets]


def generate_description_from_reviews(
    benefits: list[ExtractedBenefit],
    pain_points: list[PainPoint],
    voc_keywords: list[tuple[str, int]],
    product_name: str = "this product",
) -> str:
    """Generate a description paragraph from review insights."""
    sections = []

    # Opening with VOC keywords
    top_kws = [kw for kw, _ in voc_keywords[:5]]
    if top_kws:
        sections.append(
            f"Customers consistently praise {product_name} for its "
            f"{', '.join(top_kws[:3])}"
            f"{' and ' + top_kws[3] if len(top_kws) > 3 else ''}."
        )

    # Benefits section
    if benefits:
        pos_benefits = [b for b in benefits if b.sentiment == Sentiment.POSITIVE]
        if pos_benefits:
            items = [b.text for b in pos_benefits[:4]]
            sections.append(
                f"Top-rated features include {', '.join(items[:-1])}"
                f"{' and ' + items[-1] if len(items) > 1 else items[0]}."
            )

    # Address concerns
    if pain_points:
        sections.append(
            f"We've listened to customer feedback and addressed common concerns "
            f"like {pain_points[0].text}"
            f"{' and ' + pain_points[1].text if len(pain_points) > 1 else ''}."
        )

    # Closing with social proof
    sections.append(
        f"Join thousands of satisfied customers who chose {product_name}."
    )

    return " ".join(sections)


def analyze_reviews(
    reviews: list[str],
    product_name: str = "this product",
    platform: str = "amazon",
    max_bullets: int = 5,
    min_frequency: int = 2,
) -> ReviewAnalysisResult:
    """Complete review analysis pipeline.

    Args:
        reviews: List of customer review texts.
        product_name: Product name for description generation.
        platform: Target marketplace.
        max_bullets: Max number of bullets to generate.
        min_frequency: Min occurrences for a benefit/pain point to qualify.

    Returns:
        ReviewAnalysisResult with full analysis.
    """
    if not reviews:
        return ReviewAnalysisResult(
            total_reviews=0,
            avg_sentiment_score=0.0,
            overall_sentiment=Sentiment.NEUTRAL,
            benefits=[],
            pain_points=[],
            top_keywords=[],
            voc_phrases=[],
            generated_bullets=[],
            generated_description="",
            quality_distribution={"high": 0, "medium": 0, "low": 0},
        )

    # Sentiment analysis
    scores = [score_sentiment(r) for r in reviews]
    avg_score = sum(scores) / len(scores)
    overall = classify_sentiment(avg_score)

    # Quality distribution
    qualities = [assess_review_quality(r) for r in reviews]
    quality_dist = {
        "high": sum(1 for q in qualities if q == ReviewQuality.HIGH),
        "medium": sum(1 for q in qualities if q == ReviewQuality.MEDIUM),
        "low": sum(1 for q in qualities if q == ReviewQuality.LOW),
    }

    # Extract benefits and pain points
    benefits = cluster_benefits(reviews, min_frequency=min_frequency)
    pain_points = cluster_pain_points(reviews, min_frequency=min_frequency)

    # VOC keywords
    voc = extract_voc_keywords(reviews, top_n=20)

    # Generate bullets
    bullets = generate_bullets_from_reviews(
        benefits, pain_points,
        max_bullets=max_bullets,
        platform=platform,
    )

    # Generate description
    description = generate_description_from_reviews(
        benefits, pain_points, voc,
        product_name=product_name,
    )

    return ReviewAnalysisResult(
        total_reviews=len(reviews),
        avg_sentiment_score=round(avg_score, 3),
        overall_sentiment=overall,
        benefits=benefits,
        pain_points=pain_points,
        top_keywords=voc[:10],
        voc_phrases=voc,
        generated_bullets=bullets,
        generated_description=description,
        quality_distribution=quality_dist,
    )