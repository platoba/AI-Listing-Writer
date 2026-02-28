"""Platform-specific listing validator.

Validates listings against each platform's rules:
- Character/length limits
- Required sections
- Forbidden characters/patterns
- SEO compliance checks
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    severity: Severity
    field: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    platform: str
    issues: list[ValidationIssue] = field(default_factory=list)
    score: int = 100  # 0-100, deducted per issue

    @property
    def passed(self) -> bool:
        return not any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    def summary(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return (
            f"{status} | Score: {self.score}/100 | "
            f"Errors: {self.error_count} | Warnings: {self.warning_count}"
        )


# ── Platform Rules ────────────────────────────────────────────

PLATFORM_RULES = {
    "amazon": {
        "title_max": 200,
        "title_min": 30,
        "bullets_count": 5,
        "bullet_max": 500,
        "description_max": 2000,
        "search_terms_max": 250,
        "required_sections": ["title", "bullet", "description", "search terms"],
        "forbidden_title_chars": ["!", "★", "☆", "❤", "$", "FREE"],
        "forbidden_title_patterns": [
            r"best\s+seller",
            r"#\d+",
            r"free\s+shipping",
            r"sale|discount|cheap",
        ],
    },
    "shopee": {
        "title_max": 120,
        "title_min": 10,
        "description_max": 3000,
        "tags_count": 10,
        "required_sections": ["标题", "描述", "标签"],
        "forbidden_title_chars": [],
        "forbidden_title_patterns": [],
    },
    "lazada": {
        "title_max": 150,
        "title_min": 20,
        "short_desc_bullets": 5,
        "long_desc_max": 5000,
        "keywords_count": 15,
        "required_sections": ["title", "short description", "long description", "keywords"],
        "forbidden_title_chars": [],
        "forbidden_title_patterns": [],
    },
    "aliexpress": {
        "title_max": 128,
        "title_min": 10,
        "description_max": 5000,
        "keywords_count": 20,
        "required_sections": ["title", "description", "keywords", "selling points"],
        "forbidden_title_chars": [],
        "forbidden_title_patterns": [r"replica|fake|copy"],
    },
    "tiktok": {
        "title_max": 100,
        "title_min": 5,
        "selling_points": 3,
        "tags_count": 10,
        "required_sections": ["标题", "卖点", "描述", "标签"],
        "forbidden_title_chars": [],
        "forbidden_title_patterns": [],
    },
    "独立站": {
        "seo_title_max": 60,
        "meta_desc_max": 155,
        "description_max": 5000,
        "faq_count": 5,
        "required_sections": ["seo title", "meta description", "description", "faq"],
        "forbidden_title_chars": [],
        "forbidden_title_patterns": [],
    },
    "ebay": {
        "title_max": 80,
        "title_min": 20,
        "description_max": 4000,
        "required_sections": ["title", "item specifics", "description"],
        "forbidden_title_chars": ["★", "☆", "❤", "✅", "🔥"],
        "forbidden_title_patterns": [r"L@@K", r"WOW", r"!!!+", r"MUST SEE"],
    },
    "walmart": {
        "title_max": 75,
        "title_min": 15,
        "features_count": 5,
        "shelf_desc_max": 150,
        "long_desc_max": 4000,
        "required_sections": ["product name", "key features", "shelf description", "long description"],
        "forbidden_title_chars": [],
        "forbidden_title_patterns": [r"best|top|#1|leading"],
    },
}


def _extract_sections(text: str) -> dict[str, str]:
    """Extract **Section Name** blocks from listing text."""
    sections = {}
    pattern = r'\*\*(.+?)\*\*\s*(?:\(.*?\))?\s*[:：]?\s*(.*?)(?=\*\*[^*]|\Z)'
    for m in re.finditer(pattern, text, re.DOTALL):
        key = m.group(1).strip().lower()
        val = m.group(2).strip()
        sections[key] = val
    return sections


def _check_length(
    result: ValidationResult,
    field_name: str,
    text: str,
    max_len: Optional[int] = None,
    min_len: Optional[int] = None,
):
    """Check text length bounds."""
    length = len(text)
    if max_len and length > max_len:
        result.issues.append(
            ValidationIssue(
                Severity.ERROR,
                field_name,
                f"Exceeds {max_len} char limit ({length} chars)",
                f"Trim to {max_len} characters",
            )
        )
        result.score -= 15
    if min_len and length < min_len:
        result.issues.append(
            ValidationIssue(
                Severity.WARNING,
                field_name,
                f"Too short ({length} chars, minimum suggested: {min_len})",
                f"Expand to at least {min_len} characters for better SEO",
            )
        )
        result.score -= 5


def _check_forbidden(
    result: ValidationResult,
    field_name: str,
    text: str,
    forbidden_chars: list[str],
    forbidden_patterns: list[str],
):
    """Check for forbidden characters and patterns."""
    for ch in forbidden_chars:
        if ch.lower() in text.lower():
            result.issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    field_name,
                    f"Contains forbidden character/word: '{ch}'",
                    f"Remove '{ch}' to avoid policy violations",
                )
            )
            result.score -= 10
    for pat in forbidden_patterns:
        if re.search(pat, text, re.IGNORECASE):
            result.issues.append(
                ValidationIssue(
                    Severity.WARNING,
                    field_name,
                    f"Matches restricted pattern: '{pat}'",
                    "Rephrase to avoid potential policy flags",
                )
            )
            result.score -= 5


def _check_required_sections(
    result: ValidationResult,
    sections: dict[str, str],
    required: list[str],
):
    """Check that all required sections are present."""
    for req in required:
        found = any(req in k for k in sections)
        if not found:
            result.issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    "structure",
                    f"Missing required section: '{req}'",
                    f"Add a **{req.title()}** section",
                )
            )
            result.score -= 10


def _check_keyword_stuffing(
    result: ValidationResult,
    text: str,
    field_name: str = "content",
):
    """Detect potential keyword stuffing."""
    words = re.findall(r'[\w\u4e00-\u9fff]+', text.lower())
    if len(words) < 10:
        return
    from collections import Counter
    freq = Counter(words)
    total = len(words)
    for word, count in freq.most_common(5):
        density = count / total
        if density > 0.08 and len(word) > 2:
            result.issues.append(
                ValidationIssue(
                    Severity.WARNING,
                    field_name,
                    f"Potential keyword stuffing: '{word}' appears {count}x ({density:.1%})",
                    "Vary language to avoid search engine penalties",
                )
            )
            result.score -= 3


def _check_all_caps(result: ValidationResult, text: str, field_name: str):
    """Check for excessive ALL CAPS."""
    words = text.split()
    if len(words) < 5:
        return
    caps_count = sum(1 for w in words if w.isupper() and len(w) > 2)
    ratio = caps_count / len(words)
    if ratio > 0.3:
        result.issues.append(
            ValidationIssue(
                Severity.WARNING,
                field_name,
                f"Excessive ALL CAPS ({caps_count}/{len(words)} words)",
                "Use title case or sentence case for better readability",
            )
        )
        result.score -= 5


def validate_listing(text: str, platform: str) -> ValidationResult:
    """Validate a generated listing against platform-specific rules.

    Args:
        text: The full generated listing text.
        platform: Platform key (e.g. 'amazon', 'ebay').

    Returns:
        ValidationResult with issues and score.
    """
    platform_key = platform.lower()
    result = ValidationResult(platform=platform_key)

    rules = PLATFORM_RULES.get(platform_key)
    if rules is None:
        result.issues.append(
            ValidationIssue(
                Severity.INFO,
                "platform",
                f"No validation rules for '{platform}' — skipping",
            )
        )
        return result

    sections = _extract_sections(text)

    # Required sections
    _check_required_sections(result, sections, rules.get("required_sections", []))

    # Title checks
    title_keys = ["title", "标题", "product name", "seo title"]
    title_text = ""
    for tk in title_keys:
        for sk, sv in sections.items():
            if tk in sk:
                title_text = sv.split("\n")[0]
                break
        if title_text:
            break

    if title_text:
        _check_length(
            result, "title", title_text,
            max_len=rules.get("title_max"),
            min_len=rules.get("title_min"),
        )
        _check_forbidden(
            result, "title", title_text,
            rules.get("forbidden_title_chars", []),
            rules.get("forbidden_title_patterns", []),
        )
        _check_all_caps(result, title_text, "title")

    # Full text checks
    _check_keyword_stuffing(result, text)

    # Clamp score
    result.score = max(0, min(100, result.score))

    return result


def validate_batch(listings: list[dict]) -> list[ValidationResult]:
    """Validate multiple listings. Each item: {'text': ..., 'platform': ...}."""
    return [
        validate_listing(item["text"], item["platform"])
        for item in listings
    ]
