"""SEO Keyword Density Analyzer.

Advanced keyword density analysis with:
- TF-IDF scoring for keyword importance
- N-gram analysis (unigrams, bigrams, trigrams)
- Keyword stuffing detection
- LSI (Latent Semantic Indexing) keyword suggestions
- Section-level density breakdown
- Optimal density range checking per platform
"""
import re
import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional


# ── Optimal density ranges by platform ───────────────────

PLATFORM_DENSITY = {
    "amazon": {"min": 1.0, "max": 3.5, "ideal": 2.0},
    "ebay": {"min": 0.8, "max": 3.0, "ideal": 1.8},
    "shopify": {"min": 1.0, "max": 2.5, "ideal": 1.5},
    "walmart": {"min": 1.0, "max": 3.0, "ideal": 2.0},
    "aliexpress": {"min": 1.5, "max": 4.0, "ideal": 2.5},
    "etsy": {"min": 0.5, "max": 2.5, "ideal": 1.5},
    "独立站": {"min": 1.0, "max": 2.5, "ideal": 1.5},
}

# ── LSI Seed Clusters ───────────────────────────────────

LSI_CLUSTERS = {
    "wireless earbuds": [
        "bluetooth", "noise cancelling", "battery life", "charging case",
        "ear tips", "waterproof", "ipx", "sound quality", "bass",
        "microphone", "hands-free", "workout", "gym", "commute",
    ],
    "phone case": [
        "protection", "shockproof", "slim", "grip", "scratch resistant",
        "drop protection", "military grade", "clear", "tpu", "polycarbonate",
        "wireless charging compatible", "screen protector", "camera protection",
    ],
    "water bottle": [
        "insulated", "stainless steel", "leak proof", "bpa free",
        "vacuum", "cold", "hot", "thermos", "hydration", "sports",
        "reusable", "eco friendly", "dishwasher safe", "lid",
    ],
    "yoga mat": [
        "non slip", "thick", "exercise", "pilates", "workout",
        "eco friendly", "tpe", "alignment", "cushion", "portable",
        "carry strap", "sweat resistant", "grip", "meditation",
    ],
    "backpack": [
        "laptop", "waterproof", "travel", "hiking", "school",
        "compartment", "usb charging", "anti theft", "lightweight",
        "ergonomic", "padded", "organizer", "durable", "capacity",
    ],
}

# ── Stop words ──────────────────────────────────────────

STOP_WORDS_EN = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "this", "that",
    "these", "those", "it", "its", "you", "your", "we", "our", "they",
    "their", "he", "she", "him", "her", "not", "no", "so", "if", "as",
    "up", "out", "about", "into", "over", "after", "all", "also", "just",
    "than", "then", "very", "s", "t", "re", "ll", "ve", "d", "m",
}

STOP_WORDS_CN = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
}


@dataclass
class KeywordDensity:
    """Density data for a single keyword/phrase."""
    keyword: str
    count: int
    density: float  # percentage
    tf_idf: float = 0.0
    sections: dict[str, int] = field(default_factory=dict)
    status: str = ""  # "optimal", "low", "high", "stuffing"


@dataclass
class NGramResult:
    """N-gram analysis results."""
    unigrams: list[KeywordDensity]
    bigrams: list[KeywordDensity]
    trigrams: list[KeywordDensity]


@dataclass
class DensityReport:
    """Complete density analysis report."""
    total_words: int
    unique_words: int
    vocabulary_richness: float
    target_keyword_analysis: list[KeywordDensity]
    top_ngrams: NGramResult
    stuffing_alerts: list[str]
    lsi_suggestions: list[str]
    section_breakdown: dict[str, dict]
    platform: str
    overall_health: str  # "healthy", "warning", "critical"
    recommendations: list[str]


def _tokenize(text: str, remove_stops: bool = True) -> list[str]:
    """Tokenize text into words, optionally removing stop words."""
    is_cn = len(re.findall(r'[\u4e00-\u9fff]', text)) > len(re.findall(r'[a-zA-Z]', text))

    if is_cn:
        # Chinese: single character + common 2-char words
        tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text.lower())
        if remove_stops:
            tokens = [t for t in tokens if t not in STOP_WORDS_CN]
    else:
        tokens = re.findall(r'[a-zA-Z]+', text.lower())
        if remove_stops:
            tokens = [t for t in tokens if t not in STOP_WORDS_EN and len(t) > 1]

    return tokens


def _extract_ngrams(tokens: list[str], n: int) -> Counter:
    """Extract n-grams from token list."""
    ngrams = []
    for i in range(len(tokens) - n + 1):
        gram = " ".join(tokens[i:i + n])
        ngrams.append(gram)
    return Counter(ngrams)


def _extract_sections(text: str) -> dict[str, str]:
    """Extract named sections from listing text."""
    sections = {}
    pattern = r'\*\*(.+?)\*\*\s*[:：]?\s*(.*?)(?=\*\*[^*]|\Z)'
    matches = list(re.finditer(pattern, text, re.DOTALL))

    if matches:
        for m in matches:
            name = m.group(1).strip()
            content = m.group(2).strip()
            sections[name] = content
    else:
        # Fall back to line-based splitting
        lines = text.strip().split("\n")
        if lines:
            sections["Full Text"] = text

    return sections


def _compute_tf_idf(term_freq: int, total_terms: int, doc_freq: int = 1,
                     total_docs: int = 10) -> float:
    """Compute TF-IDF score."""
    tf = term_freq / max(total_terms, 1)
    idf = math.log((1 + total_docs) / (1 + doc_freq)) + 1
    return round(tf * idf, 4)


def analyze_density(
    text: str,
    target_keywords: Optional[list[str]] = None,
    platform: str = "amazon",
    top_n: int = 15,
) -> DensityReport:
    """Perform comprehensive keyword density analysis.

    Args:
        text: Full listing text.
        target_keywords: Optional list of target keywords to analyze.
        platform: Target platform for density thresholds.
        top_n: Number of top keywords to return per n-gram level.

    Returns:
        DensityReport with full analysis.
    """
    tokens_all = _tokenize(text, remove_stops=False)
    tokens_clean = _tokenize(text, remove_stops=True)
    total_words = len(tokens_all)
    unique_words = len(set(tokens_clean))

    density_ranges = PLATFORM_DENSITY.get(platform.lower(), PLATFORM_DENSITY["amazon"])

    # ── Target keyword analysis ──────────────────────────
    target_analysis = []
    if target_keywords:
        text_lower = text.lower()
        for kw in target_keywords:
            kw_lower = kw.lower()
            # Count occurrences (phrase match)
            count = len(re.findall(re.escape(kw_lower), text_lower))
            kw_word_count = len(kw_lower.split())
            # Density = (occurrences * words_in_phrase) / total_words * 100
            density = (count * kw_word_count) / max(total_words, 1) * 100

            # Status
            if density > density_ranges["max"] * 1.5:
                status = "stuffing"
            elif density > density_ranges["max"]:
                status = "high"
            elif density < density_ranges["min"]:
                status = "low"
            else:
                status = "optimal"

            # Section breakdown
            sections = _extract_sections(text)
            sec_counts = {}
            for sec_name, sec_text in sections.items():
                sec_count = len(re.findall(re.escape(kw_lower), sec_text.lower()))
                if sec_count > 0:
                    sec_counts[sec_name] = sec_count

            kd = KeywordDensity(
                keyword=kw,
                count=count,
                density=round(density, 2),
                tf_idf=_compute_tf_idf(count, total_words),
                sections=sec_counts,
                status=status,
            )
            target_analysis.append(kd)

    # ── N-gram analysis ──────────────────────────────────
    uni_counter = _extract_ngrams(tokens_clean, 1)
    bi_counter = _extract_ngrams(tokens_clean, 2)
    tri_counter = _extract_ngrams(tokens_clean, 3)

    def _counter_to_density(counter: Counter, n: int) -> list[KeywordDensity]:
        results = []
        for gram, count in counter.most_common(top_n):
            density = (count * n) / max(total_words, 1) * 100
            if density > density_ranges["max"] * 1.5:
                status = "stuffing"
            elif density > density_ranges["max"]:
                status = "high"
            elif density < 0.3:
                status = "low"
            else:
                status = "optimal"
            results.append(KeywordDensity(
                keyword=gram,
                count=count,
                density=round(density, 2),
                tf_idf=_compute_tf_idf(count, total_words),
                status=status,
            ))
        return results

    ngrams = NGramResult(
        unigrams=_counter_to_density(uni_counter, 1),
        bigrams=_counter_to_density(bi_counter, 2),
        trigrams=_counter_to_density(tri_counter, 3),
    )

    # ── Stuffing detection ───────────────────────────────
    stuffing_alerts = []
    all_densities = target_analysis + ngrams.unigrams + ngrams.bigrams
    for kd in all_densities:
        if kd.status == "stuffing":
            stuffing_alerts.append(
                f"⚠️ '{kd.keyword}' appears {kd.count}x ({kd.density:.1f}%) — "
                f"exceeds safe limit ({density_ranges['max']}%)"
            )

    # ── LSI suggestions ──────────────────────────────────
    lsi_suggestions = _suggest_lsi_keywords(text, target_keywords)

    # ── Section breakdown ────────────────────────────────
    sections = _extract_sections(text)
    section_breakdown = {}
    for sec_name, sec_text in sections.items():
        sec_tokens = _tokenize(sec_text, remove_stops=True)
        sec_total = len(_tokenize(sec_text, remove_stops=False))
        sec_counter = Counter(sec_tokens)
        top_words = sec_counter.most_common(5)
        section_breakdown[sec_name] = {
            "word_count": sec_total,
            "unique_words": len(set(sec_tokens)),
            "top_keywords": [
                {"word": w, "count": c, "density": round(c / max(sec_total, 1) * 100, 2)}
                for w, c in top_words
            ],
        }

    # ── Overall health ───────────────────────────────────
    if stuffing_alerts:
        overall = "critical"
    elif any(kd.status in ("high", "low") for kd in target_analysis):
        overall = "warning"
    else:
        overall = "healthy"

    # ── Recommendations ──────────────────────────────────
    recommendations = _generate_recommendations(
        target_analysis, ngrams, stuffing_alerts,
        total_words, unique_words, density_ranges, lsi_suggestions,
    )

    vocab_richness = unique_words / max(total_words, 1)

    return DensityReport(
        total_words=total_words,
        unique_words=unique_words,
        vocabulary_richness=round(vocab_richness, 3),
        target_keyword_analysis=target_analysis,
        top_ngrams=ngrams,
        stuffing_alerts=stuffing_alerts,
        lsi_suggestions=lsi_suggestions,
        section_breakdown=section_breakdown,
        platform=platform,
        overall_health=overall,
        recommendations=recommendations,
    )


def _suggest_lsi_keywords(text: str, target_keywords: Optional[list[str]] = None) -> list[str]:
    """Suggest LSI keywords based on content and target keywords."""
    if not target_keywords:
        return []

    text_lower = text.lower()
    suggestions = []

    for kw in target_keywords:
        kw_lower = kw.lower()
        for cluster_key, cluster_words in LSI_CLUSTERS.items():
            if kw_lower in cluster_key or cluster_key in kw_lower:
                for lsi_word in cluster_words:
                    if lsi_word.lower() not in text_lower:
                        suggestions.append(lsi_word)

    # Deduplicate and limit
    seen = set()
    unique = []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return unique[:10]


def _generate_recommendations(
    target_analysis: list[KeywordDensity],
    ngrams: NGramResult,
    stuffing_alerts: list[str],
    total_words: int,
    unique_words: int,
    density_ranges: dict,
    lsi_suggestions: list[str],
) -> list[str]:
    """Generate actionable recommendations."""
    recs = []

    # Stuffing fix
    if stuffing_alerts:
        recs.append("🚨 Reduce keyword repetition — search engines may penalize stuffing")

    # Low density keywords
    low = [kd for kd in target_analysis if kd.status == "low"]
    if low:
        kws = ", ".join(f"'{kd.keyword}'" for kd in low[:3])
        recs.append(f"📈 Increase usage of {kws} — currently below minimum density")

    # High density keywords
    high = [kd for kd in target_analysis if kd.status == "high"]
    if high:
        kws = ", ".join(f"'{kd.keyword}'" for kd in high[:3])
        recs.append(f"📉 Reduce {kws} — nearing keyword stuffing threshold")

    # Content depth
    if total_words < 150:
        recs.append("📝 Add more content — listings under 150 words rank poorly")
    elif total_words < 300:
        recs.append("📝 Consider expanding content to 300+ words for better SEO")

    # Vocabulary
    vocab_ratio = unique_words / max(total_words, 1)
    if vocab_ratio < 0.3:
        recs.append("🔤 Use more varied vocabulary — text feels repetitive")

    # LSI keywords
    if lsi_suggestions:
        sample = ", ".join(lsi_suggestions[:5])
        recs.append(f"🔗 Add related terms: {sample}")

    # Ideal density tip
    if not recs:
        recs.append(
            f"✅ Density looks good! Target range: "
            f"{density_ranges['min']}-{density_ranges['max']}% "
            f"(ideal: {density_ranges['ideal']}%)"
        )

    return recs


def format_density_report(report: DensityReport) -> str:
    """Format density report as readable text."""
    lines = [
        f"🔍 SEO Keyword Density Report ({report.platform})",
        f"{'=' * 50}",
        f"📊 Words: {report.total_words} | Unique: {report.unique_words} | "
        f"Richness: {report.vocabulary_richness:.1%}",
        f"🏥 Health: {report.overall_health.upper()}",
        "",
    ]

    # Target keywords
    if report.target_keyword_analysis:
        lines.append("🎯 Target Keywords:")
        for kd in report.target_keyword_analysis:
            icon = {"optimal": "✅", "low": "⬇️", "high": "⬆️", "stuffing": "🚨"}.get(
                kd.status, "❓"
            )
            lines.append(
                f"  {icon} '{kd.keyword}': {kd.count}x ({kd.density}%) "
                f"[TF-IDF: {kd.tf_idf}] — {kd.status}"
            )
            if kd.sections:
                sec_parts = [f"{k}: {v}x" for k, v in kd.sections.items()]
                lines.append(f"      Sections: {', '.join(sec_parts)}")
        lines.append("")

    # Top n-grams
    lines.append("📈 Top Unigrams:")
    for kd in report.top_ngrams.unigrams[:8]:
        lines.append(f"  • {kd.keyword}: {kd.count}x ({kd.density}%)")

    lines.append("")
    lines.append("📈 Top Bigrams:")
    for kd in report.top_ngrams.bigrams[:8]:
        lines.append(f"  • {kd.keyword}: {kd.count}x ({kd.density}%)")

    lines.append("")
    lines.append("📈 Top Trigrams:")
    for kd in report.top_ngrams.trigrams[:5]:
        lines.append(f"  • {kd.keyword}: {kd.count}x ({kd.density}%)")

    # Stuffing alerts
    if report.stuffing_alerts:
        lines.append("")
        lines.append("🚨 Stuffing Alerts:")
        for alert in report.stuffing_alerts:
            lines.append(f"  {alert}")

    # LSI suggestions
    if report.lsi_suggestions:
        lines.append("")
        lines.append("🔗 Suggested LSI Keywords:")
        lines.append(f"  {', '.join(report.lsi_suggestions)}")

    # Section breakdown
    if len(report.section_breakdown) > 1:
        lines.append("")
        lines.append("📋 Section Breakdown:")
        for sec_name, data in report.section_breakdown.items():
            lines.append(f"  [{sec_name}] {data['word_count']} words, "
                         f"{data['unique_words']} unique")
            for kw_data in data["top_keywords"][:3]:
                lines.append(f"    • {kw_data['word']}: {kw_data['count']}x ({kw_data['density']}%)")

    # Recommendations
    lines.append("")
    lines.append("💡 Recommendations:")
    for rec in report.recommendations:
        lines.append(f"  {rec}")

    return "\n".join(lines)
