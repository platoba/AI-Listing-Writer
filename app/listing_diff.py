"""Listing Diff & Version Comparison Engine.

Compare two listing versions side-by-side, calculate improvement deltas,
and generate actionable upgrade recommendations.

Features:
- Section-level diff (title, bullets, description, keywords)
- SEO improvement scoring (before vs after)
- Character count delta tracking
- Keyword coverage analysis
- Readability change detection
- Visual diff output (terminal-friendly)
"""
import re
import math
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class ImpactLevel(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class SectionDiff:
    """Diff result for a single section."""
    section: str
    change_type: ChangeType
    old_text: str = ""
    new_text: str = ""
    old_char_count: int = 0
    new_char_count: int = 0
    old_word_count: int = 0
    new_word_count: int = 0
    impact: ImpactLevel = ImpactLevel.NEUTRAL
    notes: list[str] = field(default_factory=list)

    @property
    def char_delta(self) -> int:
        return self.new_char_count - self.old_char_count

    @property
    def word_delta(self) -> int:
        return self.new_word_count - self.old_word_count

    @property
    def similarity(self) -> float:
        """Jaccard similarity between old and new."""
        if not self.old_text and not self.new_text:
            return 1.0
        if not self.old_text or not self.new_text:
            return 0.0
        old_words = set(self.old_text.lower().split())
        new_words = set(self.new_text.lower().split())
        if not old_words and not new_words:
            return 1.0
        intersection = old_words & new_words
        union = old_words | new_words
        return len(intersection) / len(union) if union else 1.0


@dataclass
class KeywordDelta:
    """Track keyword coverage changes."""
    added_keywords: list[str] = field(default_factory=list)
    removed_keywords: list[str] = field(default_factory=list)
    retained_keywords: list[str] = field(default_factory=list)
    old_density: float = 0.0
    new_density: float = 0.0

    @property
    def density_change(self) -> float:
        return self.new_density - self.old_density

    @property
    def coverage_improved(self) -> bool:
        return len(self.added_keywords) > len(self.removed_keywords)


@dataclass
class ReadabilityDelta:
    """Track readability changes."""
    old_avg_sentence_len: float = 0.0
    new_avg_sentence_len: float = 0.0
    old_flesch_approx: float = 0.0
    new_flesch_approx: float = 0.0

    @property
    def sentence_len_change(self) -> float:
        return self.new_avg_sentence_len - self.old_avg_sentence_len

    @property
    def readability_improved(self) -> bool:
        # Shorter sentences = generally more readable for product listings
        if self.old_avg_sentence_len == 0:
            return self.new_avg_sentence_len > 0  # Only improved if new text exists
        return self.new_avg_sentence_len < self.old_avg_sentence_len  # Strict improvement


@dataclass
class ListingDiffResult:
    """Complete diff result between two listing versions."""
    section_diffs: list[SectionDiff] = field(default_factory=list)
    keyword_delta: Optional[KeywordDelta] = None
    readability_delta: Optional[ReadabilityDelta] = None
    old_total_chars: int = 0
    new_total_chars: int = 0
    old_total_words: int = 0
    new_total_words: int = 0
    improvement_score: float = 0.0  # -100 to +100

    @property
    def total_char_delta(self) -> int:
        return self.new_total_chars - self.old_total_chars

    @property
    def total_word_delta(self) -> int:
        return self.new_total_words - self.old_total_words

    @property
    def sections_changed(self) -> int:
        return sum(1 for d in self.section_diffs if d.change_type != ChangeType.UNCHANGED)

    @property
    def sections_added(self) -> int:
        return sum(1 for d in self.section_diffs if d.change_type == ChangeType.ADDED)

    @property
    def sections_removed(self) -> int:
        return sum(1 for d in self.section_diffs if d.change_type == ChangeType.REMOVED)

    def summary(self) -> str:
        lines = [
            f"📊 Listing Diff Summary",
            f"{'─' * 50}",
            f"  Sections changed: {self.sections_changed}/{len(self.section_diffs)}",
            f"  Added: {self.sections_added} | Removed: {self.sections_removed}",
            f"  Char delta: {self.total_char_delta:+d} ({self.old_total_chars} → {self.new_total_chars})",
            f"  Word delta: {self.total_word_delta:+d} ({self.old_total_words} → {self.new_total_words})",
            f"  Improvement score: {self.improvement_score:+.1f}",
            "",
        ]

        for sd in self.section_diffs:
            icon = {
                ChangeType.ADDED: "🟢",
                ChangeType.REMOVED: "🔴",
                ChangeType.MODIFIED: "🟡",
                ChangeType.UNCHANGED: "⚪",
            }[sd.change_type]
            lines.append(f"  {icon} {sd.section}: {sd.change_type.value} "
                         f"(chars: {sd.char_delta:+d}, sim: {sd.similarity:.0%})")
            for note in sd.notes:
                lines.append(f"      → {note}")

        if self.keyword_delta:
            kd = self.keyword_delta
            lines.append("")
            lines.append(f"  🔑 Keywords: +{len(kd.added_keywords)} / -{len(kd.removed_keywords)} "
                         f"(density: {kd.density_change:+.2f}%)")

        if self.readability_delta:
            rd = self.readability_delta
            icon = "✅" if rd.readability_improved else "⚠️"
            lines.append(f"  {icon} Readability: avg sentence {rd.sentence_len_change:+.1f} words")

        return "\n".join(lines)


# ── Section Parsing ──────────────────────────────────────────

SECTION_PATTERNS = [
    (r'\*\*(?:Title|标题)\*\*[:\s]*(.+?)(?=\n\*\*|\Z)', "title"),
    (r'\*\*(?:Bullet\s*Points?|要点|卖点)\*\*[:\s]*(.*?)(?=\n\*\*|\Z)', "bullets"),
    (r'\*\*(?:Description|描述|商品描述)\*\*[:\s]*(.*?)(?=\n\*\*|\Z)', "description"),
    (r'\*\*(?:Search\s*Terms?|Keywords?|关键词|搜索词|标签)\*\*[:\s]*(.*?)(?=\n\*\*|\Z)', "keywords"),
    (r'\*\*(?:Target\s*Audience|目标受众)\*\*[:\s]*(.*?)(?=\n\*\*|\Z)', "audience"),
    (r'\*\*(?:Selling\s*Points?|USP|卖点)\*\*[:\s]*(.*?)(?=\n\*\*|\Z)', "selling_points"),
    (r'\*\*(?:Short\s*Description|简短描述)\*\*[:\s]*(.*?)(?=\n\*\*|\Z)', "short_description"),
    (r'\*\*(?:规格参数|Specs?|Specifications?)\*\*[:\s]*(.*?)(?=\n\*\*|\Z)', "specs"),
]


def parse_sections(text: str) -> dict[str, str]:
    """Parse a listing into named sections."""
    sections = {}
    for pattern, name in SECTION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            sections[name] = match.group(1).strip()
    # If no sections matched, treat the whole text as 'body'
    if not sections:
        sections["body"] = text.strip()
    return sections


def count_words(text: str) -> int:
    """Count words in text (handles English + Chinese)."""
    # English words
    en_words = len(re.findall(r'[a-zA-Z]+', text))
    # Chinese characters (each is roughly a word)
    cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    return en_words + cn_chars


def avg_sentence_length(text: str) -> float:
    """Calculate average sentence length in words."""
    sentences = re.split(r'[.!?。！？\n]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0.0
    total_words = sum(count_words(s) for s in sentences)
    return total_words / len(sentences)


def extract_keyword_set(text: str) -> set[str]:
    """Extract unique meaningful words from text."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "and", "but", "or", "not", "so", "for", "with", "about",
        "this", "that", "these", "those", "of", "at", "by", "in",
        "on", "to", "from", "up", "out", "if", "it", "its", "your",
        "our", "my", "their", "as", "you", "we", "they", "he", "she",
        "的", "了", "在", "是", "我", "有", "和", "就", "不",
    }
    tokens = re.findall(r'[\w\u4e00-\u9fff]+', text.lower())
    return {t for t in tokens if t not in stop_words and len(t) > 1}


def keyword_density(text: str, keywords: list[str]) -> float:
    """Calculate keyword density as percentage."""
    if not text or not keywords:
        return 0.0
    text_lower = text.lower()
    total_words = max(count_words(text), 1)
    keyword_hits = sum(text_lower.count(kw.lower()) for kw in keywords)
    return (keyword_hits / total_words) * 100


# ── Core Diff Engine ─────────────────────────────────────────

def diff_listings(old_text: str, new_text: str,
                  target_keywords: Optional[list[str]] = None) -> ListingDiffResult:
    """Compare two listing versions and produce a detailed diff.

    Args:
        old_text: The original listing text
        new_text: The updated listing text
        target_keywords: Optional list of target SEO keywords to track

    Returns:
        ListingDiffResult with section-level diffs, keyword delta, readability delta
    """
    old_sections = parse_sections(old_text)
    new_sections = parse_sections(new_text)

    all_section_names = sorted(set(old_sections.keys()) | set(new_sections.keys()))

    section_diffs = []
    improvement_points = 0

    for name in all_section_names:
        old_val = old_sections.get(name, "")
        new_val = new_sections.get(name, "")

        old_chars = len(old_val)
        new_chars = len(new_val)
        old_words = count_words(old_val)
        new_words = count_words(new_val)

        if name not in old_sections:
            change_type = ChangeType.ADDED
            impact = ImpactLevel.POSITIVE
            improvement_points += 15
            notes = [f"New section added ({new_chars} chars)"]
        elif name not in new_sections:
            change_type = ChangeType.REMOVED
            impact = ImpactLevel.NEGATIVE
            improvement_points -= 15
            notes = [f"Section removed ({old_chars} chars lost)"]
        elif old_val == new_val:
            change_type = ChangeType.UNCHANGED
            impact = ImpactLevel.NEUTRAL
            notes = []
        else:
            change_type = ChangeType.MODIFIED
            notes = []

            # Analyze the modification
            char_delta = new_chars - old_chars
            if char_delta > 0:
                notes.append(f"Expanded by {char_delta} chars")
                improvement_points += min(char_delta / 20, 10)
            elif char_delta < 0:
                notes.append(f"Shortened by {abs(char_delta)} chars")
                # Shortening can be good (conciseness) or bad
                if old_chars > 500 and new_chars > 100:
                    improvement_points += 3  # Trimming bloat
                elif new_chars < 30:
                    improvement_points -= 10  # Too short now

            # Similarity check
            sd_temp = SectionDiff(section=name, change_type=change_type,
                                  old_text=old_val, new_text=new_val)
            if sd_temp.similarity < 0.3:
                notes.append("Major rewrite (low similarity)")
                improvement_points += 5  # Rewrites usually improve
            elif sd_temp.similarity > 0.9:
                notes.append("Minor tweaks")

            impact = ImpactLevel.POSITIVE if improvement_points > 0 else ImpactLevel.NEGATIVE

        section_diffs.append(SectionDiff(
            section=name,
            change_type=change_type,
            old_text=old_val,
            new_text=new_val,
            old_char_count=old_chars,
            new_char_count=new_chars,
            old_word_count=old_words,
            new_word_count=new_words,
            impact=impact,
            notes=notes,
        ))

    # Keyword delta
    keyword_delta = None
    if target_keywords:
        old_kws = extract_keyword_set(old_text)
        new_kws = extract_keyword_set(new_text)
        target_set = {kw.lower() for kw in target_keywords}

        old_covered = old_kws & target_set
        new_covered = new_kws & target_set

        keyword_delta = KeywordDelta(
            added_keywords=sorted(new_covered - old_covered),
            removed_keywords=sorted(old_covered - new_covered),
            retained_keywords=sorted(old_covered & new_covered),
            old_density=keyword_density(old_text, target_keywords),
            new_density=keyword_density(new_text, target_keywords),
        )

        if keyword_delta.coverage_improved:
            improvement_points += 10
        elif len(keyword_delta.removed_keywords) > len(keyword_delta.added_keywords):
            improvement_points -= 5

    # Readability delta
    old_avg = avg_sentence_length(old_text)
    new_avg = avg_sentence_length(new_text)
    readability_delta = ReadabilityDelta(
        old_avg_sentence_len=old_avg,
        new_avg_sentence_len=new_avg,
    )
    if readability_delta.readability_improved and old_avg > 0:
        improvement_points += 5

    # Total counts
    old_total_chars = len(old_text)
    new_total_chars = len(new_text)
    old_total_words = count_words(old_text)
    new_total_words = count_words(new_text)

    # Clamp improvement score to [-100, 100]
    improvement_score = max(-100, min(100, improvement_points))

    return ListingDiffResult(
        section_diffs=section_diffs,
        keyword_delta=keyword_delta,
        readability_delta=readability_delta,
        old_total_chars=old_total_chars,
        new_total_chars=new_total_chars,
        old_total_words=old_total_words,
        new_total_words=new_total_words,
        improvement_score=improvement_score,
    )


def diff_summary_text(result: ListingDiffResult) -> str:
    """Generate a clean text summary of the diff."""
    return result.summary()


def diff_to_dict(result: ListingDiffResult) -> dict:
    """Serialize diff result to a dictionary for JSON export."""
    return {
        "sections_changed": result.sections_changed,
        "sections_added": result.sections_added,
        "sections_removed": result.sections_removed,
        "total_char_delta": result.total_char_delta,
        "total_word_delta": result.total_word_delta,
        "improvement_score": result.improvement_score,
        "section_diffs": [
            {
                "section": sd.section,
                "change_type": sd.change_type.value,
                "char_delta": sd.char_delta,
                "word_delta": sd.word_delta,
                "similarity": round(sd.similarity, 3),
                "impact": sd.impact.value,
                "notes": sd.notes,
            }
            for sd in result.section_diffs
        ],
        "keyword_delta": {
            "added": result.keyword_delta.added_keywords,
            "removed": result.keyword_delta.removed_keywords,
            "retained": result.keyword_delta.retained_keywords,
            "density_change": round(result.keyword_delta.density_change, 3),
        } if result.keyword_delta else None,
        "readability": {
            "old_avg_sentence": round(result.readability_delta.old_avg_sentence_len, 1),
            "new_avg_sentence": round(result.readability_delta.new_avg_sentence_len, 1),
            "improved": result.readability_delta.readability_improved,
        } if result.readability_delta else None,
    }
