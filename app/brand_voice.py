"""Brand Voice Analyzer & Profile Manager.

Maintain brand consistency across all product listings with:
- Brand voice profile definition (tone, vocabulary, style rules)
- Listing compliance checking against brand voice
- Tone detection and scoring
- Vocabulary whitelist/blacklist enforcement
- Style consistency metrics
- Brand voice templates for different market segments

Supports both English and Chinese brand voices.
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Tone(str, Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    LUXURY = "luxury"
    PLAYFUL = "playful"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    AUTHORITATIVE = "authoritative"
    MINIMALIST = "minimalist"


class ViolationType(str, Enum):
    FORBIDDEN_WORD = "forbidden_word"
    TONE_MISMATCH = "tone_mismatch"
    STYLE_VIOLATION = "style_violation"
    VOCABULARY_MISS = "vocabulary_miss"
    LENGTH_VIOLATION = "length_violation"
    EMOJI_VIOLATION = "emoji_violation"


@dataclass
class BrandVoiceProfile:
    """Define a brand's voice and style rules."""
    name: str
    tone: Tone = Tone.PROFESSIONAL
    description: str = ""

    # Vocabulary rules
    preferred_words: list[str] = field(default_factory=list)
    forbidden_words: list[str] = field(default_factory=list)
    required_phrases: list[str] = field(default_factory=list)

    # Style rules
    max_sentence_length: int = 30  # words
    min_sentence_length: int = 3
    max_exclamation_marks: int = 2
    allow_emojis: bool = True
    max_emoji_count: int = 10
    allow_all_caps: bool = False
    max_bullet_length: int = 200  # chars
    preferred_bullet_start: list[str] = field(default_factory=list)  # e.g. ["✓", "•"]

    # Formatting rules
    title_case: bool = True  # Enforce title case in titles
    use_numerals: bool = True  # "5" vs "five"
    oxford_comma: bool = True

    # Tone markers - words/patterns associated with the target tone
    tone_markers: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "tone": self.tone.value,
            "description": self.description,
            "preferred_words": self.preferred_words,
            "forbidden_words": self.forbidden_words,
            "required_phrases": self.required_phrases,
            "max_sentence_length": self.max_sentence_length,
            "allow_emojis": self.allow_emojis,
            "max_emoji_count": self.max_emoji_count,
            "allow_all_caps": self.allow_all_caps,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BrandVoiceProfile":
        tone = Tone(data.get("tone", "professional"))
        return cls(
            name=data.get("name", "Untitled"),
            tone=tone,
            description=data.get("description", ""),
            preferred_words=data.get("preferred_words", []),
            forbidden_words=data.get("forbidden_words", []),
            required_phrases=data.get("required_phrases", []),
            max_sentence_length=data.get("max_sentence_length", 30),
            allow_emojis=data.get("allow_emojis", True),
            max_emoji_count=data.get("max_emoji_count", 10),
            allow_all_caps=data.get("allow_all_caps", False),
        )


@dataclass
class BrandViolation:
    """A single brand voice violation."""
    violation_type: ViolationType
    severity: str  # "error", "warning", "info"
    message: str
    location: str = ""  # Where in the listing
    suggestion: str = ""


@dataclass
class BrandVoiceReport:
    """Brand voice compliance report."""
    profile_name: str
    violations: list[BrandViolation] = field(default_factory=list)
    tone_scores: dict[str, float] = field(default_factory=dict)
    compliance_score: float = 100.0
    preferred_words_used: list[str] = field(default_factory=list)
    preferred_words_missing: list[str] = field(default_factory=list)
    required_phrases_found: list[str] = field(default_factory=list)
    required_phrases_missing: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(v.severity == "error" for v in self.violations)

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "warning")

    def summary(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        lines = [
            f"🎨 Brand Voice Report: {self.profile_name}",
            f"{'─' * 50}",
            f"  Status: {status} | Score: {self.compliance_score:.0f}/100",
            f"  Errors: {self.error_count} | Warnings: {self.warning_count}",
            "",
        ]

        if self.tone_scores:
            lines.append("  Tone Analysis:")
            for tone, score in sorted(self.tone_scores.items(),
                                       key=lambda x: x[1], reverse=True)[:5]:
                bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
                lines.append(f"    {tone}: [{bar}] {score:.0%}")
            lines.append("")

        if self.preferred_words_used:
            lines.append(f"  ✓ Preferred words used: {', '.join(self.preferred_words_used[:10])}")
        if self.preferred_words_missing:
            lines.append(f"  ✗ Preferred words missing: {', '.join(self.preferred_words_missing[:10])}")
        if self.required_phrases_missing:
            lines.append(f"  ❌ Required phrases missing: {', '.join(self.required_phrases_missing[:5])}")

        if self.violations:
            lines.append("")
            lines.append("  Violations:")
            for v in self.violations[:15]:
                icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}[v.severity]
                lines.append(f"    {icon} [{v.violation_type.value}] {v.message}")
                if v.suggestion:
                    lines.append(f"       💡 {v.suggestion}")

        return "\n".join(lines)


# ── Tone Detection ───────────────────────────────────────────

TONE_INDICATORS = {
    Tone.PROFESSIONAL: {
        "en": ["designed", "engineered", "quality", "premium", "durable",
               "performance", "specification", "ensures", "provides", "optimal",
               "efficient", "suitable", "compatible", "features", "manufactured"],
        "cn": ["专业", "品质", "精工", "工艺", "性能", "规格", "高效",
               "可靠", "耐用", "精密", "标准", "认证"],
    },
    Tone.CASUAL: {
        "en": ["awesome", "cool", "love", "great", "super", "totally",
               "basically", "gonna", "stuff", "things", "really", "pretty",
               "honestly", "huge", "grab"],
        "cn": ["超赞", "好用", "太棒", "超级", "买它", "真的", "简直",
               "绝绝子", "yyds", "冲", "种草", "安利"],
    },
    Tone.LUXURY: {
        "en": ["exquisite", "artisan", "handcrafted", "heritage", "elegant",
               "refined", "bespoke", "timeless", "curated", "exclusive",
               "opulent", "sublime", "impeccable", "prestige", "luxurious"],
        "cn": ["奢华", "臻品", "匠心", "典雅", "尊贵", "精奢", "珍稀",
               "传承", "限量", "高定", "私享", "至臻"],
    },
    Tone.PLAYFUL: {
        "en": ["fun", "wow", "yay", "quirky", "adorable", "pop", "boom",
               "splash", "party", "magic", "sparkle", "whimsical", "groovy"],
        "cn": ["可爱", "萌", "哇", "耶", "趣味", "酷", "潮",
               "炫", "嗨", "有趣", "好玩", "童趣"],
    },
    Tone.TECHNICAL: {
        "en": ["specifications", "dimensions", "material", "voltage", "capacity",
               "resolution", "bandwidth", "compatible", "interface", "protocol",
               "algorithm", "processor", "calibrated", "tolerance", "rated"],
        "cn": ["参数", "规格", "尺寸", "材质", "电压", "容量", "分辨率",
               "接口", "协议", "兼容", "处理器", "技术"],
    },
    Tone.FRIENDLY: {
        "en": ["you'll", "your", "enjoy", "perfect", "easy", "simple",
               "help", "welcome", "happy", "thanks", "share", "family",
               "together", "comfort", "cozy"],
        "cn": ["亲", "宝贝", "温馨", "舒适", "轻松", "简单", "家庭",
               "贴心", "暖心", "好评", "满意", "放心"],
    },
    Tone.AUTHORITATIVE: {
        "en": ["research", "proven", "clinical", "certified", "tested",
               "awarded", "patented", "recognized", "endorsed", "industry-leading",
               "breakthrough", "validated", "peer-reviewed", "benchmark"],
        "cn": ["权威", "认证", "专利", "检测", "获奖", "领先", "突破",
               "验证", "标杆", "实验", "临床", "推荐"],
    },
    Tone.MINIMALIST: {
        "en": ["simple", "clean", "essential", "pure", "minimal", "less",
               "streamlined", "refined", "understated", "sleek", "uncluttered"],
        "cn": ["简约", "纯粹", "极简", "精简", "素雅", "留白", "简洁",
               "质朴", "原色", "无印"],
    },
}

# Emoji pattern
EMOJI_PATTERN = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251"
    "\U0001f926-\U0001f937\U00010000-\U0010ffff\u2640-\u2642\u2600-\u2B55"
    "\u200d\u23cf\u23e9\u231a\ufe0f\u3030\u2764\u2714\u2716\u26A0"
    "\u25AA\u25AB\u25B6\u25C0\u2660\u2663\u2665\u2666]+",
    flags=re.UNICODE
)


def count_emojis(text: str) -> int:
    """Count emojis in text."""
    return len(EMOJI_PATTERN.findall(text))


def detect_tone(text: str) -> dict[str, float]:
    """Detect the tone of a text by analyzing word usage.

    Returns a dict of tone → confidence score (0.0-1.0).
    """
    text_lower = text.lower()
    words = set(re.findall(r'[\w\u4e00-\u9fff]+', text_lower))
    total_words = max(len(words), 1)

    scores = {}
    for tone, langs in TONE_INDICATORS.items():
        indicators = set(langs.get("en", []) + langs.get("cn", []))
        matches = words & {w.lower() for w in indicators}
        # Also check multi-word phrases
        phrase_matches = sum(1 for ind in indicators if ' ' in ind and ind.lower() in text_lower)
        hit_count = len(matches) + phrase_matches
        # Normalize to 0-1 range, with diminishing returns
        raw_score = hit_count / max(len(indicators), 1)
        scores[tone.value] = min(raw_score * 3, 1.0)  # Scale up, cap at 1.0

    return scores


def check_sentence_lengths(text: str, max_len: int, min_len: int) -> list[BrandViolation]:
    """Check all sentences against length limits."""
    violations = []
    sentences = re.split(r'[.!?。！？\n]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    for i, sentence in enumerate(sentences):
        word_count = len(re.findall(r'[\w\u4e00-\u9fff]+', sentence))
        if word_count > max_len:
            violations.append(BrandViolation(
                violation_type=ViolationType.STYLE_VIOLATION,
                severity="warning",
                message=f"Sentence {i+1} too long ({word_count} words, max {max_len})",
                location=f"sentence_{i+1}",
                suggestion=f"Break into shorter sentences for readability",
            ))
        elif 0 < word_count < min_len:
            violations.append(BrandViolation(
                violation_type=ViolationType.STYLE_VIOLATION,
                severity="info",
                message=f"Sentence {i+1} very short ({word_count} words)",
                location=f"sentence_{i+1}",
            ))

    return violations


def check_brand_voice(text: str, profile: BrandVoiceProfile) -> BrandVoiceReport:
    """Check a listing against a brand voice profile.

    Args:
        text: The listing text to check
        profile: The brand voice profile to check against

    Returns:
        BrandVoiceReport with violations, tone scores, and compliance score
    """
    violations = []
    deductions = 0
    text_lower = text.lower()

    # 1. Forbidden words check
    for word in profile.forbidden_words:
        if word.lower() in text_lower:
            count = text_lower.count(word.lower())
            violations.append(BrandViolation(
                violation_type=ViolationType.FORBIDDEN_WORD,
                severity="error",
                message=f"Forbidden word '{word}' found {count}x",
                suggestion=f"Remove or replace '{word}'",
            ))
            deductions += 10 * count

    # 2. Preferred words tracking
    preferred_used = []
    preferred_missing = []
    for word in profile.preferred_words:
        if word.lower() in text_lower:
            preferred_used.append(word)
        else:
            preferred_missing.append(word)

    if profile.preferred_words:
        miss_ratio = len(preferred_missing) / len(profile.preferred_words)
        if miss_ratio > 0.7:
            violations.append(BrandViolation(
                violation_type=ViolationType.VOCABULARY_MISS,
                severity="warning",
                message=f"Only {len(preferred_used)}/{len(profile.preferred_words)} preferred words used",
                suggestion=f"Consider using: {', '.join(preferred_missing[:5])}",
            ))
            deductions += 10

    # 3. Required phrases check
    required_found = []
    required_missing = []
    for phrase in profile.required_phrases:
        if phrase.lower() in text_lower:
            required_found.append(phrase)
        else:
            required_missing.append(phrase)

    for phrase in required_missing:
        violations.append(BrandViolation(
            violation_type=ViolationType.VOCABULARY_MISS,
            severity="error",
            message=f"Required phrase '{phrase}' not found",
            suggestion=f"Include '{phrase}' in your listing",
        ))
        deductions += 15

    # 4. Emoji check
    emoji_count = count_emojis(text)
    if not profile.allow_emojis and emoji_count > 0:
        violations.append(BrandViolation(
            violation_type=ViolationType.EMOJI_VIOLATION,
            severity="error",
            message=f"Emojis not allowed but found {emoji_count}",
            suggestion="Remove all emojis",
        ))
        deductions += 10
    elif profile.allow_emojis and emoji_count > profile.max_emoji_count:
        violations.append(BrandViolation(
            violation_type=ViolationType.EMOJI_VIOLATION,
            severity="warning",
            message=f"Too many emojis ({emoji_count}, max {profile.max_emoji_count})",
            suggestion=f"Reduce to {profile.max_emoji_count} or fewer",
        ))
        deductions += 5

    # 5. ALL CAPS check
    if not profile.allow_all_caps:
        all_caps_words = re.findall(r'\b[A-Z]{3,}\b', text)
        # Filter out common abbreviations
        abbrevs = {"USB", "LED", "LCD", "HDMI", "WiFi", "GPS", "SEO", "API",
                   "UPC", "EAN", "SKU", "HTML", "PDF", "CEO", "FAQ", "DIY",
                   "USA", "EU", "UK", "UV", "SPF", "ISO"}
        caps_violations = [w for w in all_caps_words if w not in abbrevs]
        if caps_violations:
            violations.append(BrandViolation(
                violation_type=ViolationType.STYLE_VIOLATION,
                severity="warning",
                message=f"ALL CAPS words found: {', '.join(caps_violations[:5])}",
                suggestion="Use normal case for emphasis instead",
            ))
            deductions += 3 * len(caps_violations)

    # 6. Exclamation marks check
    excl_count = text.count("!") + text.count("！")
    if excl_count > profile.max_exclamation_marks:
        violations.append(BrandViolation(
            violation_type=ViolationType.STYLE_VIOLATION,
            severity="warning",
            message=f"Too many exclamation marks ({excl_count}, max {profile.max_exclamation_marks})",
            suggestion="Reduce exclamation marks for a more refined tone",
        ))
        deductions += 3

    # 7. Sentence length check
    violations.extend(check_sentence_lengths(
        text, profile.max_sentence_length, profile.min_sentence_length
    ))

    # 8. Tone detection and scoring
    tone_scores = detect_tone(text)
    target_tone_score = tone_scores.get(profile.tone.value, 0)
    if target_tone_score < 0.1:
        violations.append(BrandViolation(
            violation_type=ViolationType.TONE_MISMATCH,
            severity="warning",
            message=f"Target tone '{profile.tone.value}' score very low ({target_tone_score:.0%})",
            suggestion=f"Use more {profile.tone.value} language and vocabulary",
        ))
        deductions += 10

    # Check if a different tone dominates
    if tone_scores:
        dominant_tone = max(tone_scores, key=tone_scores.get)
        if dominant_tone != profile.tone.value and tone_scores[dominant_tone] > target_tone_score + 0.3:
            violations.append(BrandViolation(
                violation_type=ViolationType.TONE_MISMATCH,
                severity="info",
                message=f"Dominant tone is '{dominant_tone}' ({tone_scores[dominant_tone]:.0%}), "
                        f"not target '{profile.tone.value}' ({target_tone_score:.0%})",
            ))

    # Calculate compliance score
    compliance_score = max(0, 100 - deductions)

    return BrandVoiceReport(
        profile_name=profile.name,
        violations=violations,
        tone_scores=tone_scores,
        compliance_score=compliance_score,
        preferred_words_used=preferred_used,
        preferred_words_missing=preferred_missing,
        required_phrases_found=required_found,
        required_phrases_missing=required_missing,
    )


# ── Preset Profiles ──────────────────────────────────────────

PRESET_PROFILES = {
    "luxury_brand": BrandVoiceProfile(
        name="Luxury Brand",
        tone=Tone.LUXURY,
        description="High-end, refined brand voice for premium products",
        preferred_words=["exquisite", "handcrafted", "premium", "artisan",
                         "refined", "timeless", "elegant", "curated"],
        forbidden_words=["cheap", "bargain", "discount", "deal", "budget",
                         "basic", "affordable", "economy", "low-cost"],
        max_exclamation_marks=1,
        allow_emojis=False,
        allow_all_caps=False,
        max_sentence_length=25,
    ),
    "tech_brand": BrandVoiceProfile(
        name="Tech Brand",
        tone=Tone.TECHNICAL,
        description="Technical, specification-focused brand voice",
        preferred_words=["specifications", "performance", "compatible",
                         "interface", "resolution", "capacity", "optimized"],
        forbidden_words=["magic", "miracle", "unbelievable"],
        max_exclamation_marks=2,
        allow_emojis=True,
        max_emoji_count=5,
        allow_all_caps=True,
    ),
    "casual_brand": BrandVoiceProfile(
        name="Casual Brand",
        tone=Tone.CASUAL,
        description="Friendly, relatable brand voice for everyday products",
        preferred_words=["easy", "simple", "love", "great", "perfect",
                         "enjoy", "awesome", "comfortable"],
        forbidden_words=["hereby", "therein", "forthwith", "pursuant"],
        max_exclamation_marks=5,
        allow_emojis=True,
        max_emoji_count=15,
        allow_all_caps=False,
    ),
    "cn_premium": BrandVoiceProfile(
        name="中国高端品牌",
        tone=Tone.LUXURY,
        description="中文高端品牌调性",
        preferred_words=["匠心", "臻品", "品质", "精工", "传承", "尊享"],
        forbidden_words=["便宜", "白菜价", "地摊", "垃圾", "山寨", "仿品"],
        max_exclamation_marks=2,
        allow_emojis=True,
        max_emoji_count=5,
        allow_all_caps=False,
    ),
    "cn_trendy": BrandVoiceProfile(
        name="国潮品牌",
        tone=Tone.PLAYFUL,
        description="年轻潮流品牌调性",
        preferred_words=["潮", "酷", "yyds", "种草", "安利", "绝绝子", "好物"],
        forbidden_words=["老土", "过时", "劣质"],
        max_exclamation_marks=5,
        allow_emojis=True,
        max_emoji_count=20,
        allow_all_caps=False,
    ),
}


def get_preset(name: str) -> Optional[BrandVoiceProfile]:
    """Get a preset brand voice profile by name."""
    return PRESET_PROFILES.get(name)


def list_presets() -> list[str]:
    """List all available preset profile names."""
    return list(PRESET_PROFILES.keys())
