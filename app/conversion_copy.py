"""Conversion Copy Engine — psychological triggers, power words, benefit-driven copy generation."""

from __future__ import annotations

import math
import re
import sqlite3
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TriggerCategory(str, Enum):
    URGENCY = "urgency"
    SCARCITY = "scarcity"
    SOCIAL_PROOF = "social_proof"
    AUTHORITY = "authority"
    RECIPROCITY = "reciprocity"
    CURIOSITY = "curiosity"
    FEAR_OF_LOSS = "fear_of_loss"
    EXCLUSIVITY = "exclusivity"


TRIGGER_PATTERNS: dict[TriggerCategory, list[str]] = {
    TriggerCategory.URGENCY: [
        r"\blimited[\s-]?time\b", r"\bhurry\b", r"\bact now\b", r"\bdon'?t wait\b",
        r"\btoday only\b", r"\bexpires?\b", r"\bdeadline\b", r"\blast chance\b",
        r"\bright now\b", r"\bwhile supplies last\b", r"\bflash sale\b",
        r"\bending soon\b", r"\bcountdown\b", r"\bonly \d+ (hours?|days?|minutes?) left\b",
    ],
    TriggerCategory.SCARCITY: [
        r"\bonly \d+ left\b", r"\blimited (stock|quantity|edition)\b",
        r"\bselling fast\b", r"\balmost gone\b", r"\bfew remaining\b",
        r"\brare\b", r"\bexclusive batch\b", r"\bwhile stocks? last\b",
        r"\bsold out\b", r"\bback in stock\b", r"\bpre-?order\b",
    ],
    TriggerCategory.SOCIAL_PROOF: [
        r"\b\d+[,.]?\d*\+?\s*(customers?|buyers?|users?|people|reviews?|ratings?)\b",
        r"\bbest[\s-]?sell(er|ing)\b", r"\b#1\b", r"\bnumber one\b",
        r"\btop[\s-]?rated\b", r"\bmost popular\b", r"\btrending\b",
        r"\bas seen (on|in)\b", r"\btrusted by\b", r"\brecommended by\b",
        r"\baward[\s-]?winning\b", r"\bchoice of\b",
    ],
    TriggerCategory.AUTHORITY: [
        r"\bfda[\s-]?approved\b", r"\bcertified\b", r"\bclinically[\s-]?(proven|tested)\b",
        r"\bpatented\b", r"\blab[\s-]?tested\b", r"\bexpert[\s-]?recommended\b",
        r"\bprofessional[\s-]?grade\b", r"\bindustry[\s-]?leading\b",
        r"\bpeer[\s-]?reviewed\b", r"\bscientifically\b",
    ],
    TriggerCategory.RECIPROCITY: [
        r"\bfree (gift|bonus|shipping|sample|trial)\b", r"\bbuy \d+ get \d+\b",
        r"\bcomplimentary\b", r"\bno[\s-]?cost\b", r"\bincluded at no\b",
        r"\bbonus\b", r"\b(extra|additional) \w+ free\b",
    ],
    TriggerCategory.CURIOSITY: [
        r"\bsecret\b", r"\bunlock\b", r"\bdiscover\b", r"\breveal\b",
        r"\bhidden\b", r"\bmystery\b", r"\byou won'?t believe\b",
        r"\bthe truth about\b", r"\blittle[\s-]?known\b", r"\bsurpris(e|ing)\b",
    ],
    TriggerCategory.FEAR_OF_LOSS: [
        r"\bdon'?t miss\b", r"\bbefore it'?s (gone|too late)\b",
        r"\byou('ll)? (lose|miss)\b", r"\brisk[\s-]?free\b",
        r"\bmoney[\s-]?back\b", r"\bno[\s-]?risk\b", r"\bguarantee\b",
        r"\bnothing to lose\b", r"\b(full|100%?) refund\b",
    ],
    TriggerCategory.EXCLUSIVITY: [
        r"\bvip\b", r"\bmembers?[\s-]?only\b", r"\bexclusive\b",
        r"\binvitation[\s-]?only\b", r"\bpremium\b", r"\belite\b",
        r"\bselect (few|group)\b", r"\binner circle\b", r"\bearly access\b",
    ],
}

POWER_WORDS: dict[str, float] = {
    # High conversion (1.0)
    "free": 1.0, "new": 0.9, "proven": 0.95, "guaranteed": 0.95,
    "instant": 0.9, "exclusive": 0.85, "limited": 0.85, "save": 0.9,
    "easy": 0.8, "discover": 0.75, "results": 0.85, "secret": 0.7,
    "amazing": 0.65, "powerful": 0.7, "ultimate": 0.75, "premium": 0.8,
    "professional": 0.75, "revolutionary": 0.7, "transform": 0.75,
    "breakthrough": 0.7, "essential": 0.65, "upgrade": 0.7,
    # Medium conversion (0.5-0.7)
    "quality": 0.6, "value": 0.65, "comfortable": 0.55, "reliable": 0.6,
    "durable": 0.6, "lightweight": 0.55, "versatile": 0.5, "innovative": 0.6,
    "advanced": 0.55, "authentic": 0.6, "original": 0.55, "natural": 0.5,
    "organic": 0.55, "handmade": 0.5, "crafted": 0.55, "elegant": 0.5,
    # Low conversion filler
    "good": 0.2, "nice": 0.15, "great": 0.25, "very": 0.1, "really": 0.1,
    "quite": 0.05, "somewhat": 0.05, "basically": 0.05, "actually": 0.1,
}

CTA_TEMPLATES: dict[str, list[str]] = {
    "buy": [
        "Buy Now and {benefit}",
        "Add to Cart — {benefit}",
        "Get Yours Today",
        "Order Now and Save {discount}%",
        "Shop Now — Limited Stock",
    ],
    "try": [
        "Try It Risk-Free",
        "Start Your Free Trial",
        "Experience {product} Today",
        "See the Difference for Yourself",
    ],
    "learn": [
        "Discover How {product} Can {benefit}",
        "Learn More About {product}",
        "See Why {social_proof}",
        "Find Out What Makes {product} Different",
    ],
}


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class TriggerMatch:
    category: TriggerCategory
    pattern: str
    text_matched: str
    position: int  # char offset

    def to_dict(self) -> dict:
        return {
            "category": self.category.value,
            "pattern": self.pattern,
            "text_matched": self.text_matched,
            "position": self.position,
        }


@dataclass
class PowerWordHit:
    word: str
    score: float
    count: int
    positions: list[int] = field(default_factory=list)


@dataclass
class CopyScore:
    """Composite copy conversion score."""
    trigger_score: float = 0.0       # 0-25
    power_word_score: float = 0.0    # 0-25
    benefit_score: float = 0.0       # 0-25
    structure_score: float = 0.0     # 0-25
    total: float = 0.0              # 0-100
    grade: str = "F"
    triggers_found: list[TriggerMatch] = field(default_factory=list)
    power_words_found: list[PowerWordHit] = field(default_factory=list)
    benefit_count: int = 0
    feature_count: int = 0
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "trigger_score": round(self.trigger_score, 2),
            "power_word_score": round(self.power_word_score, 2),
            "benefit_score": round(self.benefit_score, 2),
            "structure_score": round(self.structure_score, 2),
            "total": round(self.total, 2),
            "grade": self.grade,
            "triggers_found": [t.to_dict() for t in self.triggers_found],
            "power_words_found": [asdict(p) for p in self.power_words_found],
            "benefit_count": self.benefit_count,
            "feature_count": self.feature_count,
            "suggestions": self.suggestions,
        }


@dataclass
class BenefitFeature:
    text: str
    is_benefit: bool  # True = benefit, False = feature
    confidence: float


# ---------------------------------------------------------------------------
# Trigger Scanner
# ---------------------------------------------------------------------------

class TriggerScanner:
    """Scan copy for psychological trigger patterns."""

    def __init__(self, extra_patterns: Optional[dict[TriggerCategory, list[str]]] = None):
        self._patterns: dict[TriggerCategory, list[re.Pattern]] = {}
        base = dict(TRIGGER_PATTERNS)
        if extra_patterns:
            for cat, pats in extra_patterns.items():
                base.setdefault(cat, []).extend(pats)
        for cat, pats in base.items():
            self._patterns[cat] = [re.compile(p, re.IGNORECASE) for p in pats]

    def scan(self, text: str) -> list[TriggerMatch]:
        matches: list[TriggerMatch] = []
        for cat, compiled in self._patterns.items():
            for pat in compiled:
                for m in pat.finditer(text):
                    matches.append(TriggerMatch(
                        category=cat,
                        pattern=pat.pattern,
                        text_matched=m.group(),
                        position=m.start(),
                    ))
        # deduplicate by (category, position)
        seen: set[tuple[str, int]] = set()
        deduped: list[TriggerMatch] = []
        for m in matches:
            key = (m.category.value, m.position)
            if key not in seen:
                seen.add(key)
                deduped.append(m)
        return sorted(deduped, key=lambda x: x.position)

    def category_counts(self, text: str) -> dict[str, int]:
        matches = self.scan(text)
        counts: dict[str, int] = {}
        for m in matches:
            counts[m.category.value] = counts.get(m.category.value, 0) + 1
        return counts

    def coverage(self, text: str) -> float:
        """Fraction of trigger categories present (0-1)."""
        cats = set(m.category for m in self.scan(text))
        return len(cats) / len(TriggerCategory)


# ---------------------------------------------------------------------------
# Power Word Analyzer
# ---------------------------------------------------------------------------

class PowerWordAnalyzer:
    """Score copy based on power word density and strength."""

    def __init__(self, custom_words: Optional[dict[str, float]] = None):
        self._words = dict(POWER_WORDS)
        if custom_words:
            self._words.update(custom_words)

    def analyze(self, text: str) -> list[PowerWordHit]:
        words_lower = re.findall(r'\b[a-z]+\b', text.lower())
        hits: dict[str, PowerWordHit] = {}
        for i, w in enumerate(words_lower):
            if w in self._words:
                if w not in hits:
                    hits[w] = PowerWordHit(word=w, score=self._words[w], count=0, positions=[])
                hits[w].count += 1
                hits[w].positions.append(i)
        return sorted(hits.values(), key=lambda x: x.score * x.count, reverse=True)

    def density(self, text: str) -> float:
        """Power word density = power_words / total_words."""
        words = re.findall(r'\b[a-z]+\b', text.lower())
        if not words:
            return 0.0
        pw_count = sum(1 for w in words if w in self._words)
        return pw_count / len(words)

    def weighted_score(self, text: str) -> float:
        """Sum of (score * count) for all power words, normalised to 0-100."""
        hits = self.analyze(text)
        raw = sum(h.score * h.count for h in hits)
        words = re.findall(r'\b[a-z]+\b', text.lower())
        n = max(len(words), 1)
        return min(100.0, (raw / n) * 200)

    def filler_ratio(self, text: str) -> float:
        """Ratio of low-value filler words (score < 0.3)."""
        words = re.findall(r'\b[a-z]+\b', text.lower())
        if not words:
            return 0.0
        fillers = [w for w in words if w in self._words and self._words[w] < 0.3]
        return len(fillers) / len(words)


# ---------------------------------------------------------------------------
# Benefit Extractor
# ---------------------------------------------------------------------------

BENEFIT_SIGNALS = [
    r"\b(you('ll)?|your)\b",
    r"\b(enjoy|experience|feel|achieve|get|receive|gain|boost|improve|enhance|save|protect)\b",
    r"\b(never|no more|without|forget about)\b",
    r"\b(so (that|you)|which means|resulting in|giving you|allowing you)\b",
    r"\b(imagine|picture|think of)\b",
]

FEATURE_SIGNALS = [
    r"\b(made (of|from|with)|built (with|from)|features?|includes?|comes? with)\b",
    r"\b(dimensions?|measures?|weighs?|capacity|material|specs?)\b",
    r"\b(\d+\s*(mm|cm|inch|oz|lb|kg|mAh|watt|volt|GB|TB))\b",
    r"\b(stainless steel|aluminum|silicone|cotton|polyester|nylon|ceramic|bamboo)\b",
    r"\b(powered by|compatible with|works with|supports?)\b",
]


class BenefitExtractor:
    """Classify sentences as benefits vs features."""

    def __init__(self):
        self._benefit_re = [re.compile(p, re.IGNORECASE) for p in BENEFIT_SIGNALS]
        self._feature_re = [re.compile(p, re.IGNORECASE) for p in FEATURE_SIGNALS]

    def classify(self, sentence: str) -> BenefitFeature:
        b_score = sum(1 for p in self._benefit_re if p.search(sentence))
        f_score = sum(1 for p in self._feature_re if p.search(sentence))
        total = max(b_score + f_score, 1)
        is_benefit = b_score >= f_score
        confidence = max(b_score, f_score) / total
        return BenefitFeature(text=sentence, is_benefit=is_benefit, confidence=confidence)

    def extract(self, text: str) -> list[BenefitFeature]:
        sentences = re.split(r'[.!?\n•\-✓✔★●▸►]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        return [self.classify(s) for s in sentences]

    def ratio(self, text: str) -> dict[str, int]:
        items = self.extract(text)
        benefits = sum(1 for i in items if i.is_benefit)
        features = sum(1 for i in items if not i.is_benefit)
        return {"benefits": benefits, "features": features, "total": len(items)}

    def suggest_benefit_rewrites(self, text: str) -> list[dict]:
        """Find features that should be rewritten as benefits."""
        items = self.extract(text)
        suggestions = []
        for item in items:
            if not item.is_benefit and item.confidence > 0.5:
                suggestions.append({
                    "original": item.text,
                    "tip": "Rewrite as a benefit: explain how this feature helps the customer.",
                    "example_prefix": "So you can... / Which means you'll... / Enjoy...",
                })
        return suggestions


# ---------------------------------------------------------------------------
# Structure Analyzer
# ---------------------------------------------------------------------------

class StructureAnalyzer:
    """Analyze copy structure for conversion best practices."""

    def analyze(self, text: str) -> dict:
        lines = text.strip().split('\n')
        non_empty = [l for l in lines if l.strip()]

        # Bullet points
        bullets = [l for l in non_empty if re.match(r'\s*[-•✓✔★●▸►]\s', l)]

        # Short paragraphs (under 3 lines each)
        paragraphs = text.strip().split('\n\n')
        short_paras = [p for p in paragraphs if p.strip() and p.strip().count('\n') < 3]

        # Capitalized headers
        headers = [l for l in non_empty if l.strip().isupper() and len(l.strip()) > 3]

        # Questions (engagement)
        questions = [l for l in non_empty if '?' in l]

        # Emoji usage
        emoji_count = len(re.findall(
            r'[\U0001F300-\U0001F9FF\U00002702-\U000027B0\U0000FE00-\U0000FEFF]', text
        ))

        # Call to action detection
        cta_patterns = [
            r'\b(buy|order|shop|add to cart|get (yours|it|started))\b',
            r'\b(click|tap|visit|check out)\b',
            r'\b(sign up|subscribe|join|register)\b',
            r'\b(try|start|begin|discover)\b',
            r'\b(call|contact|message|reach)\b',
        ]
        ctas = sum(1 for p in cta_patterns if re.search(p, text, re.IGNORECASE))

        # Word count
        word_count = len(text.split())

        # Readability (avg words per sentence)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        avg_sentence_len = (
            sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        )

        return {
            "line_count": len(non_empty),
            "word_count": word_count,
            "bullet_count": len(bullets),
            "paragraph_count": len(paragraphs),
            "short_paragraph_ratio": len(short_paras) / max(len(paragraphs), 1),
            "header_count": len(headers),
            "question_count": len(questions),
            "emoji_count": emoji_count,
            "cta_count": ctas,
            "avg_sentence_length": round(avg_sentence_len, 1),
            "has_bullets": len(bullets) > 0,
            "has_cta": ctas > 0,
            "has_questions": len(questions) > 0,
        }

    def score(self, text: str) -> float:
        """Structure score 0-25."""
        info = self.analyze(text)
        pts = 0.0
        # Bullets: 0-5
        pts += min(info["bullet_count"] * 1.0, 5.0)
        # CTA: 0-5
        pts += min(info["cta_count"] * 2.5, 5.0)
        # Short paragraphs: 0-5
        pts += info["short_paragraph_ratio"] * 5.0
        # Questions: 0-3
        pts += min(info["question_count"] * 1.5, 3.0)
        # Sentence length sweet spot (12-20 words): 0-4
        avg = info["avg_sentence_length"]
        if 12 <= avg <= 20:
            pts += 4.0
        elif 8 <= avg < 12 or 20 < avg <= 25:
            pts += 2.0
        else:
            pts += 0.5
        # Emoji moderate use: 0-3
        if 1 <= info["emoji_count"] <= 5:
            pts += 3.0
        elif info["emoji_count"] > 5:
            pts += 1.0
        return min(pts, 25.0)


# ---------------------------------------------------------------------------
# CTA Generator
# ---------------------------------------------------------------------------

class CTAGenerator:
    """Generate contextual calls-to-action."""

    def generate(
        self,
        style: str = "buy",
        product: str = "this product",
        benefit: str = "save time",
        discount: int = 0,
        social_proof: str = "thousands of happy customers",
    ) -> list[str]:
        templates = CTA_TEMPLATES.get(style, CTA_TEMPLATES["buy"])
        results = []
        for tpl in templates:
            cta = tpl.format(
                product=product,
                benefit=benefit,
                discount=discount,
                social_proof=social_proof,
            )
            results.append(cta)
        return results

    def best_for_platform(self, platform: str) -> list[str]:
        """Platform-specific CTA recommendations."""
        platform_ctas: dict[str, list[str]] = {
            "amazon": ["Add to Cart", "Buy Now", "Subscribe & Save"],
            "shopee": ["Buy Now", "Add to Cart", "Chat to Buy"],
            "lazada": ["Buy Now", "Add to Cart", "Get Voucher"],
            "aliexpress": ["Buy Now", "Add to Cart", "Order with Shipping Protection"],
            "ebay": ["Buy It Now", "Add to Watchlist", "Make an Offer"],
            "etsy": ["Add to Cart", "Buy It Now", "Add to Favorites"],
            "tiktok_shop": ["Buy Now", "Shop Now", "Get It Before It's Gone"],
        }
        return platform_ctas.get(platform.lower(), ["Buy Now", "Add to Cart", "Shop Now"])


# ---------------------------------------------------------------------------
# Copy Store (SQLite)
# ---------------------------------------------------------------------------

class CopyStore:
    """Persist copy analysis results for historical comparison."""

    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS copy_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT NOT NULL,
                platform TEXT DEFAULT '',
                total_score REAL NOT NULL,
                grade TEXT NOT NULL,
                trigger_score REAL DEFAULT 0,
                power_word_score REAL DEFAULT 0,
                benefit_score REAL DEFAULT 0,
                structure_score REAL DEFAULT 0,
                triggers_json TEXT DEFAULT '[]',
                suggestions_json TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_copy_listing ON copy_analyses(listing_id);
            CREATE INDEX IF NOT EXISTS idx_copy_created ON copy_analyses(created_at);
        """)
        self._conn.commit()

    def save(self, listing_id: str, platform: str, score: CopyScore) -> int:
        cur = self._conn.execute("""
            INSERT INTO copy_analyses
            (listing_id, platform, total_score, grade, trigger_score,
             power_word_score, benefit_score, structure_score, triggers_json, suggestions_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            listing_id, platform, score.total, score.grade,
            score.trigger_score, score.power_word_score,
            score.benefit_score, score.structure_score,
            json.dumps([t.to_dict() for t in score.triggers_found]),
            json.dumps(score.suggestions),
        ))
        self._conn.commit()
        return cur.lastrowid  # type: ignore

    def history(self, listing_id: str, limit: int = 20) -> list[dict]:
        rows = self._conn.execute("""
            SELECT * FROM copy_analyses WHERE listing_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (listing_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def best_scores(self, limit: int = 10) -> list[dict]:
        rows = self._conn.execute("""
            SELECT listing_id, platform, MAX(total_score) as best_score, grade
            FROM copy_analyses
            GROUP BY listing_id
            ORDER BY best_score DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def avg_score_by_platform(self) -> dict[str, float]:
        rows = self._conn.execute("""
            SELECT platform, AVG(total_score) as avg_score
            FROM copy_analyses
            WHERE platform != ''
            GROUP BY platform
        """).fetchall()
        return {r["platform"]: round(r["avg_score"], 2) for r in rows}

    def improvement_trend(self, listing_id: str) -> list[dict]:
        rows = self._conn.execute("""
            SELECT total_score, grade, created_at
            FROM copy_analyses WHERE listing_id = ?
            ORDER BY created_at ASC
        """, (listing_id,)).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Conversion Copy Engine (Main Class)
# ---------------------------------------------------------------------------

def _grade(score: float) -> str:
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B+"
    elif score >= 60:
        return "B"
    elif score >= 50:
        return "C"
    elif score >= 40:
        return "D"
    else:
        return "F"


class ConversionCopyEngine:
    """Main entry point: analyse listing copy for conversion potential."""

    def __init__(self, db_path: str = ":memory:"):
        self.trigger_scanner = TriggerScanner()
        self.power_analyzer = PowerWordAnalyzer()
        self.benefit_extractor = BenefitExtractor()
        self.structure_analyzer = StructureAnalyzer()
        self.cta_generator = CTAGenerator()
        self.store = CopyStore(db_path)

    def analyze(self, text: str, listing_id: str = "", platform: str = "") -> CopyScore:
        # 1. Triggers (0-25)
        triggers = self.trigger_scanner.scan(text)
        coverage = self.trigger_scanner.coverage(text)
        trigger_score = min(coverage * 25 + len(triggers) * 0.5, 25.0)

        # 2. Power words (0-25)
        pw_hits = self.power_analyzer.analyze(text)
        pw_weighted = self.power_analyzer.weighted_score(text)
        filler = self.power_analyzer.filler_ratio(text)
        power_word_score = min(pw_weighted * 0.25 - filler * 5, 25.0)
        power_word_score = max(power_word_score, 0.0)

        # 3. Benefits vs features (0-25)
        bf_ratio = self.benefit_extractor.ratio(text)
        b = bf_ratio["benefits"]
        f = bf_ratio["features"]
        total_bf = max(b + f, 1)
        benefit_ratio = b / total_bf
        benefit_score = benefit_ratio * 20 + min(b * 1.0, 5.0)
        benefit_score = min(benefit_score, 25.0)

        # 4. Structure (0-25)
        structure_score = self.structure_analyzer.score(text)

        # Total
        total = trigger_score + power_word_score + benefit_score + structure_score
        grade = _grade(total)

        # Suggestions
        suggestions = self._generate_suggestions(
            trigger_score, power_word_score, benefit_score, structure_score,
            triggers, bf_ratio, text,
        )

        score = CopyScore(
            trigger_score=trigger_score,
            power_word_score=power_word_score,
            benefit_score=benefit_score,
            structure_score=structure_score,
            total=total,
            grade=grade,
            triggers_found=triggers,
            power_words_found=pw_hits,
            benefit_count=b,
            feature_count=f,
            suggestions=suggestions,
        )

        # Persist
        if listing_id:
            self.store.save(listing_id, platform, score)

        return score

    def compare(self, texts: list[str]) -> list[CopyScore]:
        """Compare multiple listing copies."""
        return [self.analyze(t) for t in texts]

    def report(self, score: CopyScore) -> str:
        lines = [
            "=" * 50,
            "CONVERSION COPY ANALYSIS REPORT",
            "=" * 50,
            f"Overall Score: {score.total:.1f}/100 ({score.grade})",
            "",
            f"  Triggers:    {score.trigger_score:.1f}/25",
            f"  Power Words: {score.power_word_score:.1f}/25",
            f"  Benefits:    {score.benefit_score:.1f}/25",
            f"  Structure:   {score.structure_score:.1f}/25",
            "",
            f"Benefits found: {score.benefit_count}",
            f"Features found: {score.feature_count}",
            "",
        ]
        if score.triggers_found:
            lines.append("Triggers Detected:")
            cats: dict[str, list[str]] = {}
            for t in score.triggers_found:
                cats.setdefault(t.category.value, []).append(t.text_matched)
            for cat, matches in cats.items():
                lines.append(f"  [{cat}] {', '.join(matches[:5])}")
            lines.append("")

        if score.power_words_found:
            lines.append("Top Power Words:")
            for pw in score.power_words_found[:10]:
                lines.append(f"  {pw.word} (score={pw.score}, used {pw.count}x)")
            lines.append("")

        if score.suggestions:
            lines.append("Suggestions:")
            for i, s in enumerate(score.suggestions, 1):
                lines.append(f"  {i}. {s}")

        lines.append("=" * 50)
        return "\n".join(lines)

    def _generate_suggestions(
        self,
        trigger_score: float,
        power_word_score: float,
        benefit_score: float,
        structure_score: float,
        triggers: list[TriggerMatch],
        bf_ratio: dict,
        text: str,
    ) -> list[str]:
        suggestions = []

        # Trigger suggestions
        cats_found = set(t.category for t in triggers)
        if TriggerCategory.URGENCY not in cats_found:
            suggestions.append("Add urgency: 'Limited time offer' or 'Only X left in stock'")
        if TriggerCategory.SOCIAL_PROOF not in cats_found:
            suggestions.append("Add social proof: '10,000+ happy customers' or 'Top rated'")
        if TriggerCategory.FEAR_OF_LOSS not in cats_found:
            suggestions.append("Add risk reversal: 'Money-back guarantee' or 'Risk-free trial'")

        # Power word suggestions
        if power_word_score < 10:
            suggestions.append("Use more power words: 'proven', 'exclusive', 'instant', 'guaranteed'")

        # Benefit suggestions
        if bf_ratio["benefits"] < bf_ratio["features"]:
            suggestions.append(
                f"Too many features ({bf_ratio['features']}) vs benefits ({bf_ratio['benefits']}). "
                "Rewrite features as customer benefits."
            )

        # Structure suggestions
        if '•' not in text and '-' not in text and '✓' not in text:
            suggestions.append("Add bullet points to improve scannability")
        if '?' not in text:
            suggestions.append("Add a question to engage the reader")

        return suggestions[:8]
