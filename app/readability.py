"""Readability Analyzer for product listings.

Computes multiple readability indices optimized for e-commerce content:
- Flesch Reading Ease (FRE)
- Flesch-Kincaid Grade Level (FKGL)
- Gunning Fog Index
- Coleman-Liau Index
- SMOG Grade
- Automated Readability Index (ARI)
- Reading time estimation
- Sentence & vocabulary complexity analysis
- Platform-specific readability recommendations
"""

import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ReadabilityLevel(str, Enum):
    VERY_EASY = "very_easy"       # Grade 5 and below
    EASY = "easy"                 # Grade 6-7
    FAIRLY_EASY = "fairly_easy"  # Grade 8-9
    STANDARD = "standard"        # Grade 10-11
    DIFFICULT = "difficult"      # Grade 12-13
    VERY_DIFFICULT = "very_difficult"  # Grade 14+


class AudienceType(str, Enum):
    GENERAL = "general"
    TECH_SAVVY = "tech_savvy"
    LUXURY = "luxury"
    BUDGET = "budget"
    PROFESSIONAL = "professional"
    YOUTH = "youth"


# ── Syllable Counting ─────────────────────────────────────

# Common suffixes that add or don't add syllables
SILENT_E_EXCEPTIONS = {"recipe", "simile", "acne", "epitome", "hyperbole", "karate", "sesame"}
VOWELS = set("aeiouAEIOU")


def _count_syllables_en(word: str) -> int:
    """Count syllables in an English word using heuristic rules."""
    word = word.lower().strip()
    if not word or not any(c.isalpha() for c in word):
        return 0
    if len(word) <= 2:
        return 1

    # Known exceptions
    if word in SILENT_E_EXCEPTIONS:
        return _manual_syllable_count(word)

    count = 0
    prev_vowel = False
    for i, ch in enumerate(word):
        is_vowel = ch in "aeiouy"
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel

    # Silent 'e' at end
    if word.endswith("e") and not word.endswith("le") and count > 1:
        count -= 1

    # Handle -ed ending
    if word.endswith("ed") and len(word) > 3:
        if word[-3] not in "dt":
            count = max(1, count - 1)

    # -es ending (only adds syllable after s, x, z, ch, sh)
    if word.endswith("es") and len(word) > 3:
        if word[-3] not in "sxz" and not word.endswith("ches") and not word.endswith("shes"):
            count = max(1, count)

    return max(1, count)


def _manual_syllable_count(word: str) -> int:
    """Fallback: count vowel groups."""
    count = 0
    prev_vowel = False
    for ch in word.lower():
        is_vowel = ch in "aeiouy"
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    return max(1, count)


def _count_syllables_cn(text: str) -> int:
    """Count syllables in Chinese text (each character ≈ 1 syllable)."""
    return len(re.findall(r'[\u4e00-\u9fff]', text))


def _is_chinese(text: str) -> bool:
    """Detect if text is primarily Chinese."""
    cn = len(re.findall(r'[\u4e00-\u9fff]', text))
    en = len(re.findall(r'[a-zA-Z]', text))
    return cn > en


# ── Text Tokenization ─────────────────────────────────────

def _tokenize_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    # Handle bullet points and numbered lists as sentence boundaries
    text = re.sub(r'\n[\s]*[-•*]\s', '. ', text)
    text = re.sub(r'\n[\s]*\d+[.)]\s', '. ', text)

    sents = re.split(r'[.!?。！？；\n]+', text)
    return [s.strip() for s in sents if s.strip() and len(s.strip()) > 2]


def _tokenize_words(text: str) -> list[str]:
    """Extract words from text."""
    if _is_chinese(text):
        # Chinese: each character is roughly a word
        return re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+', text)
    return re.findall(r"[a-zA-Z']+", text)


def _count_complex_words(words: list[str]) -> int:
    """Count complex words (3+ syllables, excluding common suffixes)."""
    complex_count = 0
    for w in words:
        if _is_chinese(w):
            continue
        syllables = _count_syllables_en(w)
        # Exclude common suffixes that inflate complexity
        base = w.lower()
        if syllables >= 3:
            if base.endswith(("ing", "ed", "es", "ly")):
                base_syl = _count_syllables_en(base.rstrip("ingly").rstrip("ed").rstrip("es"))
                if base_syl < 3:
                    continue
            complex_count += 1
    return complex_count


# ── Readability Indices ────────────────────────────────────

@dataclass
class ReadabilityIndex:
    name: str
    score: float
    grade_level: float
    interpretation: str


@dataclass
class VocabularyStats:
    total_words: int
    unique_words: int
    lexical_diversity: float  # unique/total ratio
    avg_word_length: float
    complex_words: int
    complex_word_pct: float
    most_used: list[tuple[str, int]] = field(default_factory=list)
    long_words: list[str] = field(default_factory=list)  # 10+ chars


@dataclass
class SentenceStats:
    total_sentences: int
    avg_words_per_sentence: float
    min_sentence_length: int
    max_sentence_length: int
    std_dev: float
    very_long_sentences: int  # >25 words
    very_short_sentences: int  # <5 words


@dataclass
class ReadabilityReport:
    text_length: int
    language: str
    indices: dict[str, ReadabilityIndex] = field(default_factory=dict)
    overall_level: ReadabilityLevel = ReadabilityLevel.STANDARD
    overall_grade: float = 0.0
    reading_time_seconds: int = 0
    vocabulary: Optional[VocabularyStats] = None
    sentences: Optional[SentenceStats] = None
    recommendations: list[str] = field(default_factory=list)
    platform_fit: dict[str, float] = field(default_factory=dict)  # platform -> fit score 0-100

    def summary(self) -> str:
        lines = [
            f"📖 Readability Report",
            f"Language: {self.language} | Length: {self.text_length} chars",
            f"Level: {self.overall_level.value.replace('_', ' ').title()} (Grade {self.overall_grade:.1f})",
            f"⏱️ Reading Time: {self.reading_time_seconds // 60}m {self.reading_time_seconds % 60}s",
            "",
        ]

        if self.indices:
            lines.append("📊 Readability Indices:")
            for name, idx in self.indices.items():
                lines.append(f"  {name}: {idx.score:.1f} ({idx.interpretation})")

        if self.vocabulary:
            v = self.vocabulary
            lines.extend([
                "",
                f"📝 Vocabulary:",
                f"  Words: {v.total_words} ({v.unique_words} unique, {v.lexical_diversity:.0%} diversity)",
                f"  Avg length: {v.avg_word_length:.1f} chars | Complex: {v.complex_words} ({v.complex_word_pct:.0%})",
            ])

        if self.sentences:
            s = self.sentences
            lines.extend([
                "",
                f"📐 Sentences:",
                f"  Count: {s.total_sentences} | Avg length: {s.avg_words_per_sentence:.1f} words",
                f"  Range: {s.min_sentence_length}-{s.max_sentence_length} words",
                f"  Too long (>25): {s.very_long_sentences} | Too short (<5): {s.very_short_sentences}",
            ])

        if self.platform_fit:
            lines.extend(["", "🎯 Platform Fit:"])
            for platform, fit in sorted(self.platform_fit.items(), key=lambda x: -x[1]):
                bar = "█" * int(fit / 10) + "░" * (10 - int(fit / 10))
                lines.append(f"  {platform:15s} [{bar}] {fit:.0f}/100")

        if self.recommendations:
            lines.extend(["", "💡 Recommendations:"])
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"  {i}. {rec}")

        return "\n".join(lines)


# ── Platform Readability Targets ───────────────────────────

# Optimal grade levels by platform and audience
PLATFORM_TARGETS = {
    "amazon": {"grade": 7.0, "max_grade": 10.0, "fre_min": 60, "audience": AudienceType.GENERAL},
    "ebay": {"grade": 7.0, "max_grade": 10.0, "fre_min": 60, "audience": AudienceType.GENERAL},
    "shopee": {"grade": 5.0, "max_grade": 8.0, "fre_min": 70, "audience": AudienceType.YOUTH},
    "lazada": {"grade": 6.0, "max_grade": 9.0, "fre_min": 65, "audience": AudienceType.GENERAL},
    "aliexpress": {"grade": 5.0, "max_grade": 8.0, "fre_min": 70, "audience": AudienceType.BUDGET},
    "walmart": {"grade": 6.0, "max_grade": 9.0, "fre_min": 65, "audience": AudienceType.GENERAL},
    "etsy": {"grade": 8.0, "max_grade": 12.0, "fre_min": 50, "audience": AudienceType.GENERAL},
    "shopify": {"grade": 8.0, "max_grade": 12.0, "fre_min": 50, "audience": AudienceType.GENERAL},
    "temu": {"grade": 5.0, "max_grade": 7.0, "fre_min": 75, "audience": AudienceType.BUDGET},
}


# ── Readability Analyzer ──────────────────────────────────

class ReadabilityAnalyzer:
    """Comprehensive readability analysis engine for product listings."""

    # Words per minute for reading time
    WPM_ENGLISH = 238
    WPM_CHINESE = 300  # characters per minute

    def __init__(self):
        pass

    def analyze(self, text: str, platform: str = "amazon",
                audience: AudienceType = None) -> ReadabilityReport:
        """Run full readability analysis on text.

        Args:
            text: Product listing text to analyze.
            platform: Target e-commerce platform.
            audience: Target audience type (auto-detected from platform if None).

        Returns:
            ReadabilityReport with indices, stats, and recommendations.
        """
        if not text or not text.strip():
            return ReadabilityReport(
                text_length=0,
                language="unknown",
                overall_level=ReadabilityLevel.STANDARD,
                recommendations=["No text provided for analysis."],
            )

        is_cn = _is_chinese(text)
        language = "zh" if is_cn else "en"
        words = _tokenize_words(text)
        sentences = _tokenize_sentences(text)

        if not audience:
            target = PLATFORM_TARGETS.get(platform.lower(), PLATFORM_TARGETS["amazon"])
            audience = target.get("audience", AudienceType.GENERAL)

        report = ReadabilityReport(
            text_length=len(text),
            language=language,
        )

        # Calculate word/sentence stats
        total_words = len(words)
        total_sentences = len(sentences) or 1

        if total_words == 0:
            report.recommendations.append("Text contains no analyzable words.")
            return report

        # Vocabulary stats
        report.vocabulary = self._analyze_vocabulary(words, is_cn)

        # Sentence stats
        report.sentences = self._analyze_sentences(sentences, is_cn)

        # Calculate readability indices
        if is_cn:
            report.indices = self._chinese_indices(text, words, sentences)
        else:
            report.indices = self._english_indices(words, sentences, total_words, total_sentences)

        # Overall grade level
        grade_levels = [idx.grade_level for idx in report.indices.values() if idx.grade_level > 0]
        report.overall_grade = round(sum(grade_levels) / len(grade_levels), 1) if grade_levels else 0

        # Overall level
        report.overall_level = self._grade_to_level(report.overall_grade)

        # Reading time
        if is_cn:
            cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            report.reading_time_seconds = int(cn_chars / self.WPM_CHINESE * 60)
        else:
            report.reading_time_seconds = int(total_words / self.WPM_ENGLISH * 60)

        # Platform fit scores
        report.platform_fit = self._calculate_platform_fit(report)

        # Recommendations
        report.recommendations = self._generate_recommendations(
            report, platform, audience
        )

        return report

    def _analyze_vocabulary(self, words: list[str], is_cn: bool) -> VocabularyStats:
        """Analyze vocabulary complexity."""
        total = len(words)
        if total == 0:
            return VocabularyStats(0, 0, 0, 0, 0, 0)

        unique = set(w.lower() for w in words)
        avg_len = sum(len(w) for w in words) / total

        complex_words = 0
        if not is_cn:
            complex_words = _count_complex_words(words)

        # Most used words (filter stop words)
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
                       "to", "for", "of", "and", "or", "but", "with", "by", "from",
                       "it", "its", "this", "that", "be", "has", "have", "had",
                       "not", "no", "as", "your", "you", "our", "we", "they",
                       "的", "了", "是", "在", "和", "有", "不", "这", "那", "也"}
        word_freq: dict[str, int] = {}
        for w in words:
            wl = w.lower()
            if wl not in stop_words and len(wl) > 2:
                word_freq[wl] = word_freq.get(wl, 0) + 1
        most_used = sorted(word_freq.items(), key=lambda x: -x[1])[:10]

        # Long words
        long_words = sorted(set(w for w in words if len(w) >= 10 and w.isalpha()))[:10]

        return VocabularyStats(
            total_words=total,
            unique_words=len(unique),
            lexical_diversity=round(len(unique) / total, 3) if total else 0,
            avg_word_length=round(avg_len, 1),
            complex_words=complex_words,
            complex_word_pct=round(complex_words / total, 3) if total else 0,
            most_used=most_used,
            long_words=long_words,
        )

    def _analyze_sentences(self, sentences: list[str], is_cn: bool) -> SentenceStats:
        """Analyze sentence structure."""
        if not sentences:
            return SentenceStats(0, 0, 0, 0, 0, 0, 0)

        lengths = []
        for sent in sentences:
            if is_cn:
                words = len(re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+', sent))
            else:
                words = len(re.findall(r"[a-zA-Z']+", sent))
            lengths.append(words)

        if not lengths:
            return SentenceStats(0, 0, 0, 0, 0, 0, 0)

        avg = sum(lengths) / len(lengths)
        variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
        std_dev = math.sqrt(variance)

        return SentenceStats(
            total_sentences=len(sentences),
            avg_words_per_sentence=round(avg, 1),
            min_sentence_length=min(lengths) if lengths else 0,
            max_sentence_length=max(lengths) if lengths else 0,
            std_dev=round(std_dev, 1),
            very_long_sentences=sum(1 for l in lengths if l > 25),
            very_short_sentences=sum(1 for l in lengths if l < 5),
        )

    def _english_indices(self, words: list[str], sentences: list[str],
                          total_words: int, total_sentences: int) -> dict[str, ReadabilityIndex]:
        """Calculate English readability indices."""
        indices = {}

        total_syllables = sum(_count_syllables_en(w) for w in words)
        avg_words_per_sent = total_words / total_sentences
        avg_syllables_per_word = total_syllables / total_words if total_words else 0
        complex_words = _count_complex_words(words)
        complex_pct = complex_words / total_words if total_words else 0

        # 1. Flesch Reading Ease
        fre = 206.835 - (1.015 * avg_words_per_sent) - (84.6 * avg_syllables_per_word)
        fre = max(0, min(100, fre))
        fre_grade = max(0, (100 - fre) / 10 + 1)
        indices["Flesch Reading Ease"] = ReadabilityIndex(
            name="Flesch Reading Ease",
            score=round(fre, 1),
            grade_level=round(fre_grade, 1),
            interpretation=self._interpret_fre(fre),
        )

        # 2. Flesch-Kincaid Grade Level
        fkgl = (0.39 * avg_words_per_sent) + (11.8 * avg_syllables_per_word) - 15.59
        fkgl = max(0, fkgl)
        indices["Flesch-Kincaid Grade"] = ReadabilityIndex(
            name="Flesch-Kincaid Grade Level",
            score=round(fkgl, 1),
            grade_level=round(fkgl, 1),
            interpretation=f"Grade {fkgl:.0f} reading level",
        )

        # 3. Gunning Fog Index
        fog = 0.4 * (avg_words_per_sent + 100 * complex_pct)
        fog = max(0, fog)
        indices["Gunning Fog"] = ReadabilityIndex(
            name="Gunning Fog Index",
            score=round(fog, 1),
            grade_level=round(fog, 1),
            interpretation=self._interpret_fog(fog),
        )

        # 4. Coleman-Liau Index
        avg_chars_per_word = sum(len(w) for w in words) / total_words if total_words else 0
        L = avg_chars_per_word * 100  # letters per 100 words
        S = (total_sentences / total_words) * 100 if total_words else 0  # sentences per 100 words
        cli = (0.0588 * L) - (0.296 * S) - 15.8
        cli = max(0, cli)
        indices["Coleman-Liau"] = ReadabilityIndex(
            name="Coleman-Liau Index",
            score=round(cli, 1),
            grade_level=round(cli, 1),
            interpretation=f"Grade {cli:.0f}",
        )

        # 5. SMOG Grade
        if total_sentences >= 3:
            smog = 1.0430 * math.sqrt(complex_words * (30 / total_sentences)) + 3.1291
        else:
            smog = fkgl  # fallback
        smog = max(0, smog)
        indices["SMOG"] = ReadabilityIndex(
            name="SMOG Grade",
            score=round(smog, 1),
            grade_level=round(smog, 1),
            interpretation=f"Grade {smog:.0f}",
        )

        # 6. Automated Readability Index
        chars_per_word = sum(len(w) for w in words) / total_words if total_words else 0
        ari = (4.71 * chars_per_word) + (0.5 * avg_words_per_sent) - 21.43
        ari = max(0, ari)
        indices["ARI"] = ReadabilityIndex(
            name="Automated Readability Index",
            score=round(ari, 1),
            grade_level=round(ari, 1),
            interpretation=f"Grade {ari:.0f}",
        )

        return indices

    def _chinese_indices(self, text: str, words: list[str],
                          sentences: list[str]) -> dict[str, ReadabilityIndex]:
        """Calculate readability indices for Chinese text."""
        indices = {}

        cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_sentences = len(sentences) or 1

        # Average characters per sentence
        avg_chars_per_sent = cn_chars / total_sentences

        # Chinese readability score (custom formula)
        # Based on: character density, sentence length, punctuation variety
        score = 100
        if avg_chars_per_sent > 50:
            score -= (avg_chars_per_sent - 50) * 1.5
        elif avg_chars_per_sent < 10:
            score -= (10 - avg_chars_per_sent) * 2

        # Vocabulary complexity (rare characters, multi-byte idioms)
        common_pct = self._chinese_common_ratio(text)
        score = score * (0.5 + 0.5 * common_pct)
        score = max(0, min(100, score))

        grade = max(1, (100 - score) / 8)

        indices["Chinese Readability"] = ReadabilityIndex(
            name="中文可读性",
            score=round(score, 1),
            grade_level=round(grade, 1),
            interpretation=self._interpret_chinese_score(score),
        )

        # Sentence complexity
        sent_score = 100
        if avg_chars_per_sent > 40:
            sent_score -= min(50, (avg_chars_per_sent - 40) * 2)
        sent_grade = max(1, (100 - sent_score) / 8)

        indices["Sentence Complexity"] = ReadabilityIndex(
            name="句子复杂度",
            score=round(sent_score, 1),
            grade_level=round(sent_grade, 1),
            interpretation=f"平均每句{avg_chars_per_sent:.0f}字",
        )

        return indices

    def _chinese_common_ratio(self, text: str) -> float:
        """Estimate ratio of commonly used Chinese characters (top 3000)."""
        cn_chars = re.findall(r'[\u4e00-\u9fff]', text)
        if not cn_chars:
            return 1.0
        # Approximate: characters in the common range (0x4e00-0x6fff cover most common)
        common = sum(1 for c in cn_chars if ord(c) < 0x7000)
        return common / len(cn_chars) if cn_chars else 1.0

    def _interpret_fre(self, score: float) -> str:
        if score >= 90:
            return "Very easy (5th grade)"
        if score >= 80:
            return "Easy (6th grade)"
        if score >= 70:
            return "Fairly easy (7th grade)"
        if score >= 60:
            return "Standard (8-9th grade)"
        if score >= 50:
            return "Fairly difficult (10-12th grade)"
        if score >= 30:
            return "Difficult (college level)"
        return "Very difficult (graduate level)"

    def _interpret_fog(self, fog: float) -> str:
        if fog < 8:
            return "Easy reading"
        if fog < 12:
            return "Ideal for wide audience"
        if fog < 16:
            return "Fairly complex"
        return "Very complex"

    def _interpret_chinese_score(self, score: float) -> str:
        if score >= 80:
            return "通俗易懂"
        if score >= 60:
            return "较易理解"
        if score >= 40:
            return "一般难度"
        if score >= 20:
            return "较为复杂"
        return "非常复杂"

    def _grade_to_level(self, grade: float) -> ReadabilityLevel:
        if grade <= 5:
            return ReadabilityLevel.VERY_EASY
        if grade <= 7:
            return ReadabilityLevel.EASY
        if grade <= 9:
            return ReadabilityLevel.FAIRLY_EASY
        if grade <= 11:
            return ReadabilityLevel.STANDARD
        if grade <= 13:
            return ReadabilityLevel.DIFFICULT
        return ReadabilityLevel.VERY_DIFFICULT

    def _calculate_platform_fit(self, report: ReadabilityReport) -> dict[str, float]:
        """Calculate how well text readability fits each platform."""
        fit = {}
        grade = report.overall_grade

        for platform, target in PLATFORM_TARGETS.items():
            ideal = target["grade"]
            max_grade = target["max_grade"]
            score = 100.0

            # Grade level fit (closer to ideal = better)
            diff = abs(grade - ideal)
            if diff <= 1:
                pass  # perfect
            elif diff <= 2:
                score -= 10
            elif diff <= 4:
                score -= 25
            else:
                score -= 40

            # Too difficult penalty
            if grade > max_grade:
                excess = grade - max_grade
                score -= excess * 10

            # Too easy is slightly less bad than too hard
            if grade < ideal - 3:
                score -= 10

            # FRE check
            if report.language == "en":
                fre_idx = report.indices.get("Flesch Reading Ease")
                if fre_idx:
                    fre_min = target.get("fre_min", 60)
                    if fre_idx.score < fre_min:
                        score -= (fre_min - fre_idx.score) * 0.5

            # Sentence length check
            if report.sentences:
                if report.sentences.very_long_sentences > 3:
                    score -= 10

            fit[platform] = round(max(0, min(100, score)), 1)

        return fit

    def _generate_recommendations(self, report: ReadabilityReport,
                                   platform: str,
                                   audience: AudienceType) -> list[str]:
        """Generate actionable readability recommendations."""
        recs = []
        target = PLATFORM_TARGETS.get(platform.lower(), PLATFORM_TARGETS["amazon"])
        ideal_grade = target["grade"]

        # Grade level recommendations
        if report.overall_grade > target["max_grade"]:
            recs.append(
                f"Text is too complex (grade {report.overall_grade:.0f}) for {platform}. "
                f"Target: grade {ideal_grade:.0f}-{target['max_grade']:.0f}. "
                "Use shorter sentences and simpler words."
            )
        elif report.overall_grade < ideal_grade - 3:
            recs.append(
                f"Text may be too simplistic (grade {report.overall_grade:.0f}) for {platform}. "
                f"Target: grade {ideal_grade:.0f}. "
                "Add more detail and product-specific terminology."
            )

        # FRE recommendations
        if report.language == "en":
            fre = report.indices.get("Flesch Reading Ease")
            if fre and fre.score < target.get("fre_min", 60):
                recs.append(
                    f"Flesch Reading Ease ({fre.score:.0f}) below {platform} target ({target['fre_min']}). "
                    "Shorten sentences and use common words."
                )

        # Sentence recommendations
        if report.sentences:
            s = report.sentences
            if s.very_long_sentences > 0:
                recs.append(
                    f"{s.very_long_sentences} sentences exceed 25 words. "
                    "Break them into shorter, punchier statements."
                )
            if s.avg_words_per_sentence > 20:
                recs.append(
                    f"Average sentence length ({s.avg_words_per_sentence:.0f} words) is high. "
                    "Aim for 12-18 words per sentence for product listings."
                )
            if s.std_dev > 10:
                recs.append(
                    "Sentence lengths vary widely. Maintain more consistent sentence lengths."
                )

        # Vocabulary recommendations
        if report.vocabulary:
            v = report.vocabulary
            if v.complex_word_pct > 0.15:
                recs.append(
                    f"{v.complex_word_pct:.0%} complex words. Replace technical jargon with "
                    "simpler alternatives where possible."
                )
            if v.lexical_diversity < 0.3:
                recs.append(
                    f"Low vocabulary diversity ({v.lexical_diversity:.0%}). "
                    "Use more synonyms and varied expressions."
                )
            if v.avg_word_length > 6:
                recs.append(
                    f"Average word length ({v.avg_word_length:.1f} chars) is high. "
                    "Prefer shorter, more common words."
                )

        # Audience-specific
        if audience == AudienceType.YOUTH:
            if report.overall_grade > 8:
                recs.append(
                    "For younger audiences, keep grade level under 8. "
                    "Use casual, energetic language."
                )
        elif audience == AudienceType.PROFESSIONAL:
            if report.overall_grade < 8:
                recs.append(
                    "Professional audience can handle grade 10-12 content. "
                    "Add industry terminology and detailed specs."
                )

        # Reading time
        if report.reading_time_seconds > 120:
            recs.append(
                f"Reading time ({report.reading_time_seconds // 60}m{report.reading_time_seconds % 60}s) "
                "is long for a product listing. Consider trimming to key selling points."
            )

        if not recs:
            recs.append("✅ Readability is well-optimized for the target platform and audience.")

        return recs

    def compare_texts(self, texts: dict[str, str], platform: str = "amazon") -> str:
        """Compare readability across multiple listing variants.

        Args:
            texts: Dict of variant_name -> text content.
            platform: Target platform.

        Returns:
            Formatted comparison report.
        """
        if not texts:
            return "No texts to compare."

        results = {}
        for name, text in texts.items():
            results[name] = self.analyze(text, platform)

        lines = ["📊 Readability Comparison", f"Platform: {platform}", ""]

        # Header
        names = list(results.keys())
        lines.append(f"{'Metric':<25}" + "".join(f"{n:>15}" for n in names))
        lines.append("─" * (25 + 15 * len(names)))

        # Grade level
        lines.append(
            f"{'Grade Level':<25}" +
            "".join(f"{r.overall_grade:>15.1f}" for r in results.values())
        )

        # Level
        lines.append(
            f"{'Level':<25}" +
            "".join(f"{r.overall_level.value:>15}" for r in results.values())
        )

        # Reading time
        lines.append(
            f"{'Reading Time (sec)':<25}" +
            "".join(f"{r.reading_time_seconds:>15}" for r in results.values())
        )

        # FRE (English only)
        if all(r.language == "en" for r in results.values()):
            fre_vals = []
            for r in results.values():
                fre = r.indices.get("Flesch Reading Ease")
                fre_vals.append(fre.score if fre else 0)
            lines.append(
                f"{'Flesch Reading Ease':<25}" +
                "".join(f"{v:>15.1f}" for v in fre_vals)
            )

        # Word count
        lines.append(
            f"{'Word Count':<25}" +
            "".join(
                f"{r.vocabulary.total_words if r.vocabulary else 0:>15}"
                for r in results.values()
            )
        )

        # Platform fit
        lines.append("")
        lines.append(f"{'Platform Fit':<25}" +
                      "".join(f"{r.platform_fit.get(platform, 0):>15.0f}" for r in results.values()))

        # Winner
        best_name = max(results.keys(), key=lambda n: results[n].platform_fit.get(platform, 0))
        lines.append("")
        lines.append(f"🏆 Best fit for {platform}: {best_name}")

        return "\n".join(lines)


def analyze_readability(text: str, platform: str = "amazon",
                         audience: AudienceType = None) -> ReadabilityReport:
    """Convenience function for quick readability analysis."""
    analyzer = ReadabilityAnalyzer()
    return analyzer.analyze(text, platform, audience)
