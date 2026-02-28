"""Competitor listing analyzer.

Parses and analyzes competitor product listings to extract:
- Keywords and phrases used
- Structural patterns
- Selling points and claims
- Price positioning signals
- Gap analysis vs your listing
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from collections import Counter


@dataclass
class ExtractedKeywords:
    """Keywords extracted from a competitor listing."""
    primary: list[str] = field(default_factory=list)      # High frequency, title keywords
    secondary: list[str] = field(default_factory=list)     # Medium frequency, bullet keywords
    long_tail: list[str] = field(default_factory=list)     # Multi-word phrases
    emotional: list[str] = field(default_factory=list)     # Power/emotion words found
    technical: list[str] = field(default_factory=list)     # Specs and technical terms


@dataclass
class CompetitorProfile:
    """Analyzed profile of a competitor listing."""
    title: str = ""
    title_length: int = 0
    word_count: int = 0
    bullet_count: int = 0
    avg_bullet_length: float = 0
    description_length: int = 0
    keywords: ExtractedKeywords = field(default_factory=ExtractedKeywords)
    selling_points: list[str] = field(default_factory=list)
    claims: list[str] = field(default_factory=list)         # "best", "#1", etc.
    has_warranty_mention: bool = False
    has_money_back: bool = False
    has_free_shipping: bool = False
    has_bundle: bool = False
    emoji_count: int = 0
    has_html: bool = False
    readability_score: float = 0.0     # Flesch-like 0-100
    structure_score: float = 0.0       # How well-structured 0-100


@dataclass
class GapAnalysisResult:
    """What your listing is missing vs competitors."""
    missing_keywords: list[str] = field(default_factory=list)
    missing_selling_points: list[str] = field(default_factory=list)
    structural_gaps: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)


@dataclass
class CompetitorComparison:
    """Side-by-side comparison of multiple listings."""
    your_profile: CompetitorProfile
    competitor_profiles: list[CompetitorProfile] = field(default_factory=list)
    gap_analysis: Optional[GapAnalysisResult] = None
    recommendation_score: float = 0.0   # 0-100 how much room for improvement


# =============================================================================
# Word lists for analysis
# =============================================================================

EMOTION_WORDS = {
    "amazing", "incredible", "stunning", "gorgeous", "beautiful", "elegant",
    "premium", "luxury", "exclusive", "revolutionary", "innovative",
    "breakthrough", "game-changer", "must-have", "essential", "ultimate",
    "perfect", "flawless", "exceptional", "outstanding", "superior",
    "powerful", "advanced", "professional", "deluxe", "supreme",
    "unbeatable", "extraordinary", "remarkable", "magnificent", "superb",
}

URGENCY_WORDS = {
    "limited", "exclusive", "hurry", "now", "today", "fast", "quick",
    "instant", "immediately", "selling fast", "few left", "last chance",
    "don't miss", "act now", "while supplies last", "flash",
}

TRUST_WORDS = {
    "guaranteed", "certified", "tested", "proven", "verified", "authentic",
    "genuine", "official", "authorized", "warranty", "endorsed",
    "recommended", "approved", "validated", "trusted", "reliable",
}

TECHNICAL_PATTERNS = [
    r"\b\d+(?:\.\d+)?\s*(?:mm|cm|m|inch|in|ft|kg|g|lb|oz|ml|l|mah|w|v|hz|ghz|mhz|gb|tb|mb|fps|rpm|psi|dpi)\b",
    r"\b(?:USB|HDMI|WiFi|Wi-Fi|Bluetooth|NFC|GPS|LED|LCD|OLED|AMOLED|4K|8K|1080p|720p|HDR)\b",
    r"\b(?:IP[0-9]{2}|IPX[0-9])\b",  # IP ratings
    r"\b[A-Z]{2,5}\d{3,}\b",          # Model numbers
]

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "be", "this", "that",
    "are", "was", "were", "been", "has", "have", "had", "do", "does",
    "did", "will", "would", "could", "should", "may", "can", "not",
    "all", "each", "every", "your", "our", "their", "its", "you",
    "we", "they", "i", "my", "me", "him", "her", "us", "them",
    "more", "most", "very", "just", "also", "so", "than", "then",
    "up", "out", "no", "only", "own", "same", "both", "few", "other",
}


class CompetitorAnalyzer:
    """Analyze and compare product listings."""

    def analyze_listing(self, text: str, title: str = "") -> CompetitorProfile:
        """Analyze a single listing text."""
        profile = CompetitorProfile()

        # Title analysis
        if title:
            profile.title = title
            profile.title_length = len(title)

        # Full text analysis
        full_text = f"{title}\n{text}" if title else text
        words = full_text.split()
        profile.word_count = len(words)

        # Bullet analysis
        bullets = self._extract_bullets(text)
        profile.bullet_count = len(bullets)
        if bullets:
            profile.avg_bullet_length = sum(len(b) for b in bullets) / len(bullets)

        # Description length
        profile.description_length = len(text)

        # Keywords extraction
        profile.keywords = self._extract_keywords(full_text)

        # Selling points
        profile.selling_points = self._extract_selling_points(full_text)

        # Claims detection
        profile.claims = self._detect_claims(full_text)

        # Feature flags
        text_lower = full_text.lower()
        warranty_words = ["warranty", "guarantee", "保修", "质保"]
        negation_prefixes = ["no ", "not ", "without ", "don't ", "doesn't ", "non-"]
        profile.has_warranty_mention = any(
            w in text_lower and not any(
                f"{neg}{w}" in text_lower for neg in negation_prefixes
            )
            for w in warranty_words
        )
        profile.has_money_back = any(w in text_lower for w in
                                     ["money back", "refund", "退款", "退货"])
        profile.has_free_shipping = any(w in text_lower for w in
                                        ["free shipping", "包邮", "free delivery"])
        profile.has_bundle = any(w in text_lower for w in
                                 ["bundle", "set of", "pack of", "套装", "combo"])

        # Emoji count
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0001F900-\U0001F9FF"
            "\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF]+",
            flags=re.UNICODE,
        )
        profile.emoji_count = len(emoji_pattern.findall(full_text))

        # HTML detection
        profile.has_html = bool(re.search(r"<[a-zA-Z][^>]*>", full_text))

        # Readability
        profile.readability_score = self._calc_readability(full_text)

        # Structure score
        profile.structure_score = self._calc_structure_score(
            title, text, bullets, profile
        )

        return profile

    def compare(self, your_listing: str, your_title: str,
                competitor_listings: list[dict[str, str]]) -> CompetitorComparison:
        """Compare your listing against competitors.

        competitor_listings: list of {"title": "...", "text": "..."}
        """
        your_profile = self.analyze_listing(your_listing, your_title)
        comp_profiles = []
        for comp in competitor_listings:
            cp = self.analyze_listing(
                comp.get("text", ""),
                comp.get("title", ""),
            )
            comp_profiles.append(cp)

        gap = self._gap_analysis(your_profile, comp_profiles)
        rec_score = self._recommendation_score(your_profile, comp_profiles, gap)

        return CompetitorComparison(
            your_profile=your_profile,
            competitor_profiles=comp_profiles,
            gap_analysis=gap,
            recommendation_score=rec_score,
        )

    def _extract_bullets(self, text: str) -> list[str]:
        """Extract bullet points from text."""
        bullet_patterns = [
            r"^[-•★✓✔·⚡🔋🎯📦💡]\s+.+",
            r"^\d+[\.\)]\s+.+",
            r"^[A-Z][A-Z\s]+[-:]\s+.+",  # "FEATURE: description"
        ]
        bullets = []
        for line in text.split("\n"):
            line = line.strip()
            if any(re.match(p, line) for p in bullet_patterns):
                bullets.append(line)
        return bullets

    def _extract_keywords(self, text: str) -> ExtractedKeywords:
        """Extract and categorize keywords."""
        kw = ExtractedKeywords()

        # Clean text
        clean = re.sub(r"[^\w\s-]", " ", text.lower())
        words = [w for w in clean.split() if w not in STOP_WORDS and len(w) > 2]

        # Word frequency
        freq = Counter(words)

        # Primary: top frequency words
        kw.primary = [w for w, c in freq.most_common(10) if c >= 2]

        # Secondary: medium frequency
        kw.secondary = [w for w, c in freq.most_common(25)
                        if c >= 1 and w not in kw.primary][:10]

        # Long-tail: 2-3 word phrases
        bigrams = self._extract_ngrams(clean, 2)
        trigrams = self._extract_ngrams(clean, 3)
        kw.long_tail = [p for p, c in (bigrams + trigrams).most_common(10) if c >= 1]

        # Emotional words found
        kw.emotional = [w for w in words if w in EMOTION_WORDS]
        kw.emotional = list(dict.fromkeys(kw.emotional))[:10]

        # Technical terms
        tech_terms = []
        for pattern in TECHNICAL_PATTERNS:
            tech_terms.extend(re.findall(pattern, text, re.IGNORECASE))
        kw.technical = list(dict.fromkeys(tech_terms))[:10]

        return kw

    def _extract_ngrams(self, text: str, n: int) -> Counter:
        """Extract n-gram phrases."""
        words = [w for w in text.split() if w not in STOP_WORDS and len(w) > 2]
        ngrams = [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]
        return Counter(ngrams)

    def _extract_selling_points(self, text: str) -> list[str]:
        """Identify selling points in text."""
        patterns = [
            r"(?:features?|benefits?|advantages?|includes?)\s*[:：]\s*(.+)",
            r"(?:✓|✔|★|⭐|👍)\s*(.+)",
            r"(?:perfect for|ideal for|great for|designed for)\s+(.+?)[\.\n]",
            r"(?:saves? you|helps? you|makes? it easy)\s+(.+?)[\.\n]",
            r"(?:unlike|compared to|better than)\s+(.+?)[\.\n]",
        ]
        points = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            points.extend(matches)
        return list(dict.fromkeys(points))[:15]

    def _detect_claims(self, text: str) -> list[str]:
        """Detect marketing claims (may need substantiation)."""
        claim_patterns = [
            (r"\b(?:best|#1|number one|top rated|highest rated|most popular)\b", "superlative claim"),
            (r"\b(?:guaranteed|100% satisfaction|money.?back)\b", "guarantee claim"),
            (r"\b(?:clinically proven|scientifically|lab tested)\b", "science claim"),
            (r"\b(?:eco.?friendly|sustainable|green|organic)\b", "environmental claim"),
            (r"\b(?:award.?winning|prize.?winning|acclaimed)\b", "award claim"),
            (r"\b(?:patented|patent pending|proprietary)\b", "IP claim"),
            (r"\b(?:doctor|physician|dentist|vet)\s+(?:recommended|approved)\b", "endorsement claim"),
        ]
        claims = []
        for pattern, claim_type in claim_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                claims.append(claim_type)
        return list(dict.fromkeys(claims))

    def _calc_readability(self, text: str) -> float:
        """Simplified readability score (0-100, higher = easier to read)."""
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return 50.0

        words = text.split()
        if not words:
            return 50.0

        avg_sentence_len = len(words) / len(sentences)
        avg_word_len = sum(len(w) for w in words) / len(words)

        # Simplified Flesch formula
        score = 206.835 - (1.015 * avg_sentence_len) - (84.6 * (avg_word_len / 5))
        return max(0, min(100, score))

    def _calc_structure_score(self, title: str, text: str,
                               bullets: list, profile: CompetitorProfile) -> float:
        """Score how well-structured the listing is (0-100)."""
        score = 0.0

        # Has title
        if title:
            score += 15
            # Title is reasonable length
            if 40 <= len(title) <= 200:
                score += 10

        # Has bullets
        if bullets:
            score += 15
            if 3 <= len(bullets) <= 7:
                score += 10

        # Has reasonable length
        if profile.description_length >= 200:
            score += 10
        if profile.description_length >= 500:
            score += 5

        # Uses formatting
        if profile.has_html or profile.emoji_count > 0:
            score += 10

        # Has sections (headers, bold, etc.)
        section_markers = len(re.findall(r"(?:\*\*|#{1,3}|<h[1-6]>)", text))
        if section_markers >= 2:
            score += 10

        # Has specs/technical info
        if profile.keywords.technical:
            score += 10

        # Warranty/guarantee mention
        if profile.has_warranty_mention:
            score += 5

        return min(100, score)

    def _gap_analysis(self, your: CompetitorProfile,
                       competitors: list[CompetitorProfile]) -> GapAnalysisResult:
        """Identify gaps between your listing and competitors."""
        gap = GapAnalysisResult()

        if not competitors:
            return gap

        # Collect all competitor keywords
        comp_keywords: set[str] = set()
        for cp in competitors:
            comp_keywords.update(cp.keywords.primary)
            comp_keywords.update(cp.keywords.secondary)

        your_keywords = set(your.keywords.primary + your.keywords.secondary)

        # Missing keywords
        gap.missing_keywords = list(comp_keywords - your_keywords)[:15]

        # Missing selling points
        comp_points: set[str] = set()
        for cp in competitors:
            comp_points.update(cp.selling_points)
        your_points = set(your.selling_points)
        # Fuzzy match: check if the concept is missing, not exact match
        gap.missing_selling_points = list(comp_points - your_points)[:10]

        # Structural gaps
        avg_bullets = sum(cp.bullet_count for cp in competitors) / len(competitors)
        if your.bullet_count < avg_bullets - 1:
            gap.structural_gaps.append(
                f"Your bullets ({your.bullet_count}) < avg competitor ({avg_bullets:.0f})")

        avg_desc_len = sum(cp.description_length for cp in competitors) / len(competitors)
        if your.description_length < avg_desc_len * 0.6:
            gap.structural_gaps.append(
                f"Description too short ({your.description_length}) vs avg ({avg_desc_len:.0f})")

        avg_title_len = sum(cp.title_length for cp in competitors) / len(competitors)
        if your.title_length < avg_title_len * 0.7:
            gap.structural_gaps.append(
                f"Title too short ({your.title_length}) vs avg ({avg_title_len:.0f})")

        # Opportunities
        warranty_count = sum(1 for cp in competitors if cp.has_warranty_mention)
        if warranty_count >= len(competitors) / 2 and not your.has_warranty_mention:
            gap.opportunities.append("Add warranty/guarantee mention (competitors have it)")

        bundle_count = sum(1 for cp in competitors if cp.has_bundle)
        if bundle_count >= len(competitors) / 3 and not your.has_bundle:
            gap.opportunities.append("Consider bundle/combo offering")

        # Check if competitors use more emotion words
        avg_emotion = sum(len(cp.keywords.emotional) for cp in competitors) / len(competitors)
        if len(your.keywords.emotional) < avg_emotion * 0.5:
            gap.opportunities.append("Use more emotional/power words")

        # Your strengths
        unique_keywords = your_keywords - comp_keywords
        if unique_keywords:
            gap.strengths.append(f"Unique keywords: {', '.join(list(unique_keywords)[:5])}")

        if your.readability_score > max(cp.readability_score for cp in competitors):
            gap.strengths.append("Better readability than all competitors")

        if your.structure_score > max(cp.structure_score for cp in competitors):
            gap.strengths.append("Better structure than all competitors")

        return gap

    def _recommendation_score(self, your: CompetitorProfile,
                               competitors: list[CompetitorProfile],
                               gap: GapAnalysisResult) -> float:
        """How much room for improvement (0=perfect, 100=needs lots of work)."""
        if not competitors:
            return 50.0

        penalties = 0
        penalties += len(gap.missing_keywords) * 2
        penalties += len(gap.missing_selling_points) * 3
        penalties += len(gap.structural_gaps) * 5
        penalties += len(gap.opportunities) * 3

        # Bonus for strengths
        bonuses = len(gap.strengths) * 3

        return max(0, min(100, penalties - bonuses))

    def format_comparison(self, comparison: CompetitorComparison) -> str:
        """Format comparison as readable report."""
        y = comparison.your_profile
        lines = [
            "📊 **Competitor Analysis Report**",
            "",
            f"🎯 Improvement Score: {comparison.recommendation_score:.0f}/100 "
            f"({'low' if comparison.recommendation_score < 30 else 'medium' if comparison.recommendation_score < 60 else 'high'} priority)",
            "",
            "--- YOUR LISTING ---",
            f"Title: {y.title_length} chars | Bullets: {y.bullet_count} | "
            f"Description: {y.description_length} chars",
            f"Readability: {y.readability_score:.0f}/100 | Structure: {y.structure_score:.0f}/100",
            f"Keywords: {len(y.keywords.primary)} primary | {len(y.keywords.technical)} technical",
            "",
        ]

        for i, cp in enumerate(comparison.competitor_profiles, 1):
            lines.extend([
                f"--- COMPETITOR #{i} ---",
                f"Title: {cp.title_length} chars | Bullets: {cp.bullet_count} | "
                f"Description: {cp.description_length} chars",
                f"Readability: {cp.readability_score:.0f}/100 | Structure: {cp.structure_score:.0f}/100",
                "",
            ])

        gap = comparison.gap_analysis
        if gap:
            if gap.missing_keywords:
                lines.extend([
                    "🔍 **Missing Keywords:**",
                    f"  {', '.join(gap.missing_keywords[:10])}",
                    "",
                ])
            if gap.missing_selling_points:
                lines.extend([
                    "💡 **Missing Selling Points:**",
                    *[f"  - {sp}" for sp in gap.missing_selling_points[:5]],
                    "",
                ])
            if gap.structural_gaps:
                lines.extend([
                    "📐 **Structural Gaps:**",
                    *[f"  - {g}" for g in gap.structural_gaps],
                    "",
                ])
            if gap.opportunities:
                lines.extend([
                    "🚀 **Opportunities:**",
                    *[f"  - {o}" for o in gap.opportunities],
                    "",
                ])
            if gap.strengths:
                lines.extend([
                    "💪 **Your Strengths:**",
                    *[f"  - {s}" for s in gap.strengths],
                    "",
                ])

        return "\n".join(lines)
