"""Competitor review mining and analysis engine.

Extracts actionable insights from product reviews:
- Sentiment analysis (positive/negative/neutral)
- Pain point extraction (top complaints, recurring issues)
- Feature request mining (what buyers want but can't find)
- Keyword extraction from reviews (real buyer language)
- Rating distribution analysis
- Review quality scoring
- Listing optimization suggestions based on review data
"""
import re
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta


# Sentiment lexicons
POSITIVE_WORDS = {
    "love", "amazing", "excellent", "perfect", "great", "fantastic",
    "awesome", "wonderful", "best", "outstanding", "superb", "brilliant",
    "incredible", "impressive", "beautiful", "sturdy", "durable", "quality",
    "recommend", "happy", "pleased", "satisfied", "solid", "reliable",
    "comfortable", "convenient", "easy", "fast", "smooth", "elegant",
    "premium", "worth", "value", "must-have", "favorite", "flawless",
    # Chinese
    "好", "棒", "赞", "优秀", "满意", "推荐", "完美", "喜欢", "值",
    "方便", "舒服", "耐用", "划算", "实用", "好看",
}

NEGATIVE_WORDS = {
    "terrible", "awful", "horrible", "worst", "bad", "poor", "cheap",
    "broken", "defective", "disappointing", "useless", "waste", "flimsy",
    "fragile", "leak", "crack", "missing", "wrong", "damaged", "fake",
    "scam", "overpriced", "slow", "difficult", "confusing", "uncomfortable",
    "noisy", "smell", "stain", "rust", "peel", "scratch", "return",
    "refund", "regret", "frustrated", "annoyed", "complaint",
    # Chinese
    "差", "烂", "垃圾", "失望", "退货", "退款", "假", "坏", "碎",
    "难用", "不值", "后悔", "投诉", "漏", "裂", "味道大",
}

INTENSIFIERS = {
    "very", "extremely", "absolutely", "totally", "completely", "highly",
    "incredibly", "really", "truly", "super", "quite", "rather",
    "特别", "非常", "极其", "太", "超级",
}

NEGATORS = {
    "not", "no", "never", "don't", "doesn't", "didn't", "won't",
    "wouldn't", "can't", "cannot", "isn't", "aren't", "wasn't",
    "weren't", "hardly", "barely", "scarcely", "neither", "nor",
    "不", "没", "没有", "别", "未",
}

# Pain point categories
PAIN_CATEGORIES = {
    "quality": ["broke", "broken", "crack", "cracked", "defective", "flimsy",
                "cheap", "thin", "weak", "fragile", "fell apart", "poor quality"],
    "sizing": ["too small", "too big", "too large", "too tight", "too loose",
               "doesn't fit", "size", "sizing", "runs small", "runs large"],
    "durability": ["wore out", "faded", "peeled", "rust", "rusted", "stain",
                   "discolor", "tear", "tore", "worn", "deteriorat"],
    "delivery": ["late", "delayed", "slow shipping", "wrong item", "missing",
                 "damaged in shipping", "packaging", "arrived broken"],
    "value": ["overpriced", "not worth", "waste of money", "expensive",
              "better options", "cheaper", "rip off", "ripoff"],
    "usability": ["hard to use", "difficult", "confusing", "complicated",
                  "instructions", "manual", "setup", "install"],
    "appearance": ["looks different", "color", "doesn't look like", "photo",
                   "picture", "misleading", "not as shown", "ugly"],
    "functionality": ["doesn't work", "stopped working", "malfunction",
                      "failed", "won't turn on", "battery", "charge"],
    "smell": ["smell", "odor", "chemical", "toxic", "stink", "off-gassing"],
    "safety": ["sharp", "cut", "burn", "hazard", "unsafe", "dangerous",
               "choking", "allergic", "reaction", "irritat"],
}

# Feature request patterns
FEATURE_PATTERNS = [
    r"wish (?:it|they|this) (?:had|came with|included|offered)(.*?)(?:\.|$)",
    r"would be (?:nice|great|better|perfect) (?:if|to have)(.*?)(?:\.|$)",
    r"(?:should|could) (?:have|include|come with|add)(.*?)(?:\.|$)",
    r"(?:needs?|need) (?:a |an |to have |more )(.*?)(?:\.|$)",
    r"(?:missing|lacks?|no) (.*?)(?:\.|$)",
    r"(?:希望|期望|建议|要是).{2,30}(?:就好了|更好|不错)",
    r"如果(?:有|能).{2,20}(?:就|更)",
]


@dataclass
class ReviewItem:
    """Single review data."""
    text: str
    rating: Optional[float] = None  # 1-5 stars
    date: Optional[str] = None
    verified: bool = False
    helpful_votes: int = 0
    title: Optional[str] = None
    author: Optional[str] = None
    platform: str = "unknown"


@dataclass
class SentimentResult:
    """Sentiment analysis result for a review."""
    score: float  # -1.0 to 1.0
    label: str  # positive/negative/neutral
    positive_words: list[str] = field(default_factory=list)
    negative_words: list[str] = field(default_factory=list)
    confidence: float = 0.0

    @property
    def is_positive(self) -> bool:
        return self.score > 0.1

    @property
    def is_negative(self) -> bool:
        return self.score < -0.1


@dataclass
class PainPoint:
    """Extracted pain point from reviews."""
    category: str
    description: str
    frequency: int = 1
    sample_quotes: list[str] = field(default_factory=list)
    avg_rating: float = 0.0
    severity: float = 0.0  # 0-1, based on frequency and rating impact

    @property
    def severity_label(self) -> str:
        if self.severity >= 0.7:
            return "critical"
        if self.severity >= 0.4:
            return "moderate"
        return "minor"


@dataclass
class FeatureRequest:
    """Extracted feature request from reviews."""
    text: str
    frequency: int = 1
    sample_quotes: list[str] = field(default_factory=list)
    avg_rating: float = 0.0


@dataclass
class BuyerKeyword:
    """Keyword extracted from buyer language."""
    keyword: str
    frequency: int = 1
    context: str = ""  # positive or negative
    bigrams: list[str] = field(default_factory=list)


@dataclass
class ReviewInsights:
    """Complete review analysis results."""
    total_reviews: int = 0
    avg_rating: float = 0.0
    rating_distribution: dict[int, int] = field(default_factory=dict)
    sentiment_distribution: dict[str, int] = field(default_factory=lambda: {
        "positive": 0, "negative": 0, "neutral": 0
    })

    pain_points: list[PainPoint] = field(default_factory=list)
    feature_requests: list[FeatureRequest] = field(default_factory=list)
    buyer_keywords: list[BuyerKeyword] = field(default_factory=list)

    top_positive_themes: list[str] = field(default_factory=list)
    top_negative_themes: list[str] = field(default_factory=list)

    review_quality_score: float = 0.0
    listing_suggestions: list[str] = field(default_factory=list)

    # Time-based trends
    sentiment_trend: list[dict] = field(default_factory=list)  # monthly sentiment

    @property
    def satisfaction_rate(self) -> float:
        if self.total_reviews == 0:
            return 0.0
        pos = self.sentiment_distribution.get("positive", 0)
        return round(pos / self.total_reviews * 100, 1)

    @property
    def complaint_rate(self) -> float:
        if self.total_reviews == 0:
            return 0.0
        neg = self.sentiment_distribution.get("negative", 0)
        return round(neg / self.total_reviews * 100, 1)

    @property
    def has_quality_issues(self) -> bool:
        return any(p.category == "quality" and p.severity >= 0.5
                   for p in self.pain_points)


class ReviewAnalyzer:
    """Analyze product reviews to extract actionable listing insights."""

    def __init__(self, reviews: list[ReviewItem]):
        self.reviews = reviews
        self._sentiments: list[SentimentResult] = []

    def analyze(self) -> ReviewInsights:
        """Run full analysis pipeline."""
        insights = ReviewInsights(total_reviews=len(self.reviews))

        if not self.reviews:
            return insights

        # Step 1: Sentiment analysis
        self._sentiments = [self._analyze_sentiment(r.text) for r in self.reviews]
        for s in self._sentiments:
            insights.sentiment_distribution[s.label] += 1

        # Step 2: Rating distribution
        ratings = [r.rating for r in self.reviews if r.rating is not None]
        if ratings:
            insights.avg_rating = round(sum(ratings) / len(ratings), 2)
            for r in ratings:
                bucket = int(r)
                if bucket < 1:
                    bucket = 1
                if bucket > 5:
                    bucket = 5
                insights.rating_distribution[bucket] = \
                    insights.rating_distribution.get(bucket, 0) + 1

        # Step 3: Pain point extraction
        insights.pain_points = self._extract_pain_points()

        # Step 4: Feature request mining
        insights.feature_requests = self._extract_feature_requests()

        # Step 5: Buyer keyword extraction
        insights.buyer_keywords = self._extract_buyer_keywords()

        # Step 6: Theme extraction
        insights.top_positive_themes = self._extract_themes(positive=True)
        insights.top_negative_themes = self._extract_themes(positive=False)

        # Step 7: Review quality scoring
        insights.review_quality_score = self._score_review_quality()

        # Step 8: Sentiment trend
        insights.sentiment_trend = self._compute_sentiment_trend()

        # Step 9: Generate listing suggestions
        insights.listing_suggestions = self._generate_suggestions(insights)

        return insights

    def _analyze_sentiment(self, text: str) -> SentimentResult:
        """Rule-based sentiment analysis."""
        if not text:
            return SentimentResult(score=0.0, label="neutral", confidence=0.0)

        words = re.findall(r'\w+', text.lower())
        pos_found = []
        neg_found = []

        i = 0
        while i < len(words):
            word = words[i]
            # Check for negation
            is_negated = False
            if i > 0 and words[i - 1] in NEGATORS:
                is_negated = True

            # Check for intensifier
            intensity = 1.0
            if i > 0 and words[i - 1] in INTENSIFIERS:
                intensity = 1.5

            if word in POSITIVE_WORDS:
                if is_negated:
                    neg_found.append(f"not {word}")
                else:
                    pos_found.extend([word] * (1 if intensity == 1.0 else 2))
            elif word in NEGATIVE_WORDS:
                if is_negated:
                    pos_found.append(f"not {word}")
                else:
                    neg_found.extend([word] * (1 if intensity == 1.0 else 2))

            i += 1

        pos_count = len(pos_found)
        neg_count = len(neg_found)
        total = pos_count + neg_count

        if total == 0:
            return SentimentResult(
                score=0.0, label="neutral",
                positive_words=[], negative_words=[],
                confidence=0.2,
            )

        score = (pos_count - neg_count) / total
        confidence = min(1.0, total / 5)  # More words → higher confidence

        if score > 0.1:
            label = "positive"
        elif score < -0.1:
            label = "negative"
        else:
            label = "neutral"

        return SentimentResult(
            score=round(score, 3),
            label=label,
            positive_words=list(set(pos_found)),
            negative_words=list(set(neg_found)),
            confidence=round(confidence, 2),
        )

    def _extract_pain_points(self) -> list[PainPoint]:
        """Extract and categorize pain points from negative reviews."""
        category_hits: dict[str, list[tuple[str, float]]] = defaultdict(list)

        for review, sentiment in zip(self.reviews, self._sentiments):
            if sentiment.score > 0.3:
                continue  # Skip clearly positive reviews

            text_lower = review.text.lower()
            rating = review.rating or 3.0

            for category, patterns in PAIN_CATEGORIES.items():
                for pattern in patterns:
                    if pattern in text_lower:
                        # Extract context around the match
                        idx = text_lower.find(pattern)
                        start = max(0, idx - 40)
                        end = min(len(text_lower), idx + len(pattern) + 40)
                        context = review.text[start:end].strip()
                        category_hits[category].append((context, rating))
                        break  # One category match per review

        pain_points = []
        total = len(self.reviews) or 1

        for category, hits in category_hits.items():
            freq = len(hits)
            avg_rat = sum(r for _, r in hits) / freq if freq > 0 else 3.0
            # Severity: higher frequency + lower rating = more severe
            severity = min(1.0, (freq / total) * 3) * (1 - (avg_rat - 1) / 4)

            samples = [q for q, _ in hits[:3]]  # Top 3 quotes

            pain_points.append(PainPoint(
                category=category,
                description=f"{category.replace('_', ' ').title()} issues "
                            f"({freq} mentions)",
                frequency=freq,
                sample_quotes=samples,
                avg_rating=round(avg_rat, 2),
                severity=round(severity, 3),
            ))

        pain_points.sort(key=lambda p: p.severity, reverse=True)
        return pain_points

    def _extract_feature_requests(self) -> list[FeatureRequest]:
        """Mine feature requests from review text."""
        requests_found: dict[str, list[tuple[str, float]]] = defaultdict(list)

        for review in self.reviews:
            text = review.text
            rating = review.rating or 3.0

            for pattern in FEATURE_PATTERNS:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    cleaned = match.strip().rstrip(".!?")[:100]
                    if len(cleaned) < 5:
                        continue
                    # Normalize key
                    key = cleaned.lower().strip()
                    requests_found[key].append((text[:100], rating))

        results = []
        for text, hits in requests_found.items():
            freq = len(hits)
            avg_rat = sum(r for _, r in hits) / freq
            results.append(FeatureRequest(
                text=text,
                frequency=freq,
                sample_quotes=[q for q, _ in hits[:2]],
                avg_rating=round(avg_rat, 2),
            ))

        results.sort(key=lambda f: f.frequency, reverse=True)
        return results[:15]  # Top 15 feature requests

    def _extract_buyer_keywords(self) -> list[BuyerKeyword]:
        """Extract real buyer language keywords."""
        from collections import Counter

        positive_words: Counter = Counter()
        negative_words: Counter = Counter()

        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "it", "this",
            "that", "with", "for", "and", "but", "or", "not", "very",
            "have", "has", "had", "been", "will", "would", "could",
            "should", "just", "like", "get", "got", "one", "use", "used",
            "really", "also", "much", "well", "than", "can", "does",
            "did", "its", "they", "them", "their", "these", "those",
            "some", "all", "any", "each", "from", "more", "most",
            "other", "out", "over", "only", "own", "same", "too",
        }

        for review, sentiment in zip(self.reviews, self._sentiments):
            words = re.findall(r'[a-zA-Z\u4e00-\u9fff]{3,}', review.text.lower())
            filtered = [w for w in words if w not in stop_words and len(w) > 2]

            counter = positive_words if sentiment.is_positive else negative_words
            counter.update(filtered)

        # Merge and create keyword objects
        all_keywords: dict[str, BuyerKeyword] = {}

        for word, count in positive_words.most_common(30):
            all_keywords[word] = BuyerKeyword(
                keyword=word, frequency=count, context="positive"
            )

        for word, count in negative_words.most_common(30):
            if word in all_keywords:
                # Keyword appears in both contexts
                all_keywords[word].frequency += count
                all_keywords[word].context = "mixed"
            else:
                all_keywords[word] = BuyerKeyword(
                    keyword=word, frequency=count, context="negative"
                )

        result = sorted(all_keywords.values(),
                        key=lambda k: k.frequency, reverse=True)
        return result[:25]

    def _extract_themes(self, positive: bool = True) -> list[str]:
        """Extract common themes from positive or negative reviews."""
        theme_counter: Counter = Counter()

        for review, sentiment in zip(self.reviews, self._sentiments):
            if positive and sentiment.score <= 0.1:
                continue
            if not positive and sentiment.score >= -0.1:
                continue

            # Extract noun phrases (simple 2-gram approach)
            words = re.findall(r'[a-zA-Z\u4e00-\u9fff]+', review.text.lower())
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i + 1]}"
                if len(bigram) > 6:
                    theme_counter[bigram] += 1

        # Filter meaningful themes
        themes = []
        for theme, count in theme_counter.most_common(20):
            if count >= 2:
                themes.append(theme)
            if len(themes) >= 8:
                break

        return themes

    def _score_review_quality(self) -> float:
        """Score the overall quality/authenticity of reviews."""
        if not self.reviews:
            return 0.0

        scores = []

        # 1. Length diversity (not all same length = more authentic)
        lengths = [len(r.text) for r in self.reviews]
        if len(lengths) > 1:
            avg_len = sum(lengths) / len(lengths)
            variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
            length_score = min(1.0, math.sqrt(variance) / 100)
            scores.append(length_score)

        # 2. Verified purchase ratio
        verified = sum(1 for r in self.reviews if r.verified)
        verified_ratio = verified / len(self.reviews)
        scores.append(verified_ratio)

        # 3. Rating distribution (natural = bell curve around 3-4)
        ratings = [r.rating for r in self.reviews if r.rating is not None]
        if ratings:
            # All 5-star or all 1-star is suspicious
            unique_ratings = len(set(int(r) for r in ratings))
            rating_diversity = min(1.0, unique_ratings / 4)
            scores.append(rating_diversity)

        # 4. Sentiment vs rating consistency
        consistent = 0
        total_check = 0
        for review, sentiment in zip(self.reviews, self._sentiments):
            if review.rating is not None:
                total_check += 1
                if (review.rating >= 4 and sentiment.is_positive) or \
                   (review.rating <= 2 and sentiment.is_negative) or \
                   (2 < review.rating < 4 and sentiment.label == "neutral"):
                    consistent += 1
        if total_check > 0:
            scores.append(consistent / total_check)

        if not scores:
            return 50.0

        return round(sum(scores) / len(scores) * 100, 1)

    def _compute_sentiment_trend(self) -> list[dict]:
        """Compute monthly sentiment trend."""
        monthly: dict[str, dict] = defaultdict(
            lambda: {"positive": 0, "negative": 0, "neutral": 0, "count": 0}
        )

        for review, sentiment in zip(self.reviews, self._sentiments):
            if review.date:
                try:
                    dt = datetime.fromisoformat(review.date.replace("Z", "+00:00"))
                    month_key = dt.strftime("%Y-%m")
                except (ValueError, AttributeError):
                    month_key = "unknown"
            else:
                month_key = "unknown"

            monthly[month_key][sentiment.label] += 1
            monthly[month_key]["count"] += 1

        trend = []
        for month, data in sorted(monthly.items()):
            if month == "unknown":
                continue
            total = data["count"] or 1
            trend.append({
                "month": month,
                "positive_pct": round(data["positive"] / total * 100, 1),
                "negative_pct": round(data["negative"] / total * 100, 1),
                "count": data["count"],
            })

        return trend

    def _generate_suggestions(self, insights: ReviewInsights) -> list[str]:
        """Generate listing optimization suggestions based on review analysis."""
        suggestions = []

        # Based on pain points
        for pp in insights.pain_points[:3]:
            if pp.severity >= 0.5:
                suggestions.append(
                    f"⚠️ Address '{pp.category}' concerns in your listing — "
                    f"{pp.frequency} buyers mentioned this issue. "
                    f"Add clear specifications to set expectations."
                )
            elif pp.severity >= 0.3:
                suggestions.append(
                    f"📝 Consider mentioning '{pp.category}' specs clearly — "
                    f"some buyers had concerns."
                )

        # Based on positive themes
        for theme in insights.top_positive_themes[:3]:
            suggestions.append(
                f"✅ Highlight '{theme}' in your listing — "
                f"buyers frequently praise this."
            )

        # Based on buyer keywords
        pos_keywords = [k for k in insights.buyer_keywords
                        if k.context == "positive" and k.frequency >= 3]
        if pos_keywords:
            kw_list = ", ".join(k.keyword for k in pos_keywords[:5])
            suggestions.append(
                f"🔑 Use buyer language in your listing: {kw_list}"
            )

        # Based on feature requests
        if insights.feature_requests:
            top_req = insights.feature_requests[0]
            suggestions.append(
                f"💡 Buyers want: '{top_req.text}' — "
                f"consider adding this to product or listing."
            )

        # Based on satisfaction rate
        if insights.satisfaction_rate < 60:
            suggestions.append(
                f"🔴 Low satisfaction ({insights.satisfaction_rate}%) — "
                f"review product quality before investing in marketing."
            )
        elif insights.satisfaction_rate >= 85:
            suggestions.append(
                f"🟢 High satisfaction ({insights.satisfaction_rate}%) — "
                f"leverage positive reviews in listing social proof."
            )

        # Based on rating
        if insights.avg_rating < 3.5:
            suggestions.append(
                "📉 Below-average ratings — focus on quality improvements "
                "before scaling."
            )

        return suggestions


def analyze_reviews(reviews: list[dict]) -> ReviewInsights:
    """Convenience function to analyze reviews from dict format.

    Args:
        reviews: List of dicts with keys: text, rating, date, verified, title

    Returns:
        ReviewInsights with full analysis
    """
    items = []
    for r in reviews:
        items.append(ReviewItem(
            text=r.get("text", ""),
            rating=r.get("rating"),
            date=r.get("date"),
            verified=r.get("verified", False),
            helpful_votes=r.get("helpful_votes", 0),
            title=r.get("title"),
            author=r.get("author"),
            platform=r.get("platform", "unknown"),
        ))
    analyzer = ReviewAnalyzer(items)
    return analyzer.analyze()


def format_review_report(insights: ReviewInsights) -> str:
    """Format review insights as a readable text report."""
    lines = [
        "=" * 60,
        "📊 REVIEW ANALYSIS REPORT",
        "=" * 60,
        "",
        f"Total Reviews: {insights.total_reviews}",
        f"Average Rating: {'⭐' * int(insights.avg_rating)} "
        f"({insights.avg_rating}/5.0)",
        f"Satisfaction Rate: {insights.satisfaction_rate}%",
        f"Complaint Rate: {insights.complaint_rate}%",
        f"Review Quality Score: {insights.review_quality_score}/100",
        "",
    ]

    # Rating distribution
    lines.append("📈 Rating Distribution:")
    for stars in range(5, 0, -1):
        count = insights.rating_distribution.get(stars, 0)
        bar = "█" * (count * 2)
        lines.append(f"  {'⭐' * stars}: {bar} ({count})")
    lines.append("")

    # Sentiment
    lines.append("😊 Sentiment Distribution:")
    for label, count in insights.sentiment_distribution.items():
        pct = round(count / max(insights.total_reviews, 1) * 100, 1)
        lines.append(f"  {label}: {count} ({pct}%)")
    lines.append("")

    # Pain points
    if insights.pain_points:
        lines.append("🔴 Pain Points:")
        for pp in insights.pain_points:
            severity_icon = "🔴" if pp.severity >= 0.7 else "🟡" if pp.severity >= 0.4 else "🟢"
            lines.append(f"  {severity_icon} {pp.description} "
                         f"[severity: {pp.severity_label}]")
            for q in pp.sample_quotes[:2]:
                lines.append(f"    \"{q}\"")
        lines.append("")

    # Feature requests
    if insights.feature_requests:
        lines.append("💡 Feature Requests:")
        for fr in insights.feature_requests[:5]:
            lines.append(f"  • {fr.text} (×{fr.frequency})")
        lines.append("")

    # Buyer keywords
    if insights.buyer_keywords:
        lines.append("🔑 Buyer Keywords:")
        for kw in insights.buyer_keywords[:10]:
            icon = "🟢" if kw.context == "positive" else "🔴" if kw.context == "negative" else "🟡"
            lines.append(f"  {icon} {kw.keyword} (×{kw.frequency})")
        lines.append("")

    # Suggestions
    if insights.listing_suggestions:
        lines.append("📋 Listing Optimization Suggestions:")
        for s in insights.listing_suggestions:
            lines.append(f"  {s}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
