"""Keyword extraction and suggestion engine."""
import re
from collections import Counter
from typing import Optional

from app.ai_engine import call_ai

# Common stop words (EN + CN)
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
    "neither", "each", "every", "all", "any", "few", "more", "most",
    "other", "some", "such", "no", "only", "own", "same", "than",
    "too", "very", "just", "because", "as", "until", "while", "of",
    "at", "by", "for", "with", "about", "against", "between", "through",
    "during", "before", "after", "above", "below", "to", "from", "up",
    "down", "in", "out", "on", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how",
    "this", "that", "these", "those", "i", "me", "my", "myself", "we",
    "our", "ours", "you", "your", "yours", "he", "him", "his", "she",
    "her", "hers", "it", "its", "they", "them", "their", "theirs",
    "what", "which", "who", "whom", "if",
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
    "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
    "会", "着", "没有", "看", "好", "自己", "这",
}


def extract_keywords(text: str, top_n: int = 20) -> list[str]:
    """Extract top keywords from text using frequency analysis."""
    # Split on non-word chars, keep Chinese chars
    tokens = re.findall(r'[\w\u4e00-\u9fff]+', text.lower())
    tokens = [t for t in tokens if t not in STOP_WORDS and len(t) > 1]
    counter = Counter(tokens)
    return [word for word, _ in counter.most_common(top_n)]


def suggest_keywords_ai(product: str, platform: str = "amazon") -> str:
    """Use AI to suggest SEO keywords for a product on a given platform."""
    prompt = f"""You are an e-commerce SEO keyword expert.

Product: {product}
Platform: {platform}

Generate:
1. **Primary Keywords** (5) — highest search volume, most relevant
2. **Long-tail Keywords** (10) — specific phrases buyers actually search
3. **Negative Keywords** (5) — terms to avoid/exclude
4. **Trending Keywords** (5) — currently trending related terms
5. **Backend/Hidden Keywords** (10) — for search term fields

Format each section as a numbered list. Be specific and actionable.
Language: Match the product language (English or Chinese)."""

    return call_ai(prompt)


def compare_keywords(listing_a: str, listing_b: str) -> dict:
    """Compare keywords between two listings."""
    kw_a = set(extract_keywords(listing_a, 30))
    kw_b = set(extract_keywords(listing_b, 30))
    return {
        "only_a": sorted(kw_a - kw_b),
        "only_b": sorted(kw_b - kw_a),
        "shared": sorted(kw_a & kw_b),
        "coverage_a": len(kw_a & kw_b) / max(len(kw_b), 1),
        "coverage_b": len(kw_a & kw_b) / max(len(kw_a), 1),
    }


def keyword_density(text: str, keyword: str) -> float:
    """Calculate keyword density as a percentage."""
    tokens = re.findall(r'[\w\u4e00-\u9fff]+', text.lower())
    if not tokens:
        return 0.0
    kw_lower = keyword.lower()
    count = sum(1 for t in tokens if t == kw_lower)
    return round(count / len(tokens) * 100, 2)
