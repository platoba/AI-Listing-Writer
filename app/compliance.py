"""Platform compliance checker for product listings.

Validates listings against platform-specific rules:
- Character limits (title, description, bullets, search terms)
- Prohibited words and phrases
- Required fields and sections
- Category-specific restrictions
- HTML/formatting rules
- Image requirements metadata
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    ERROR = "error"        # Must fix - listing will be rejected
    WARNING = "warning"    # Should fix - may reduce visibility
    INFO = "info"          # Nice to fix - best practice


@dataclass
class ComplianceIssue:
    """A single compliance violation."""
    rule_id: str
    platform: str
    severity: Severity
    field: str
    message: str
    suggestion: str = ""
    current_value: str = ""
    limit: Optional[int] = None

    def __str__(self) -> str:
        icon = {"error": "❌", "warning": "⚠️", "info": "💡"}[self.severity.value]
        s = f"{icon} [{self.rule_id}] {self.field}: {self.message}"
        if self.suggestion:
            s += f"\n   → {self.suggestion}"
        return s


@dataclass
class ComplianceReport:
    """Full compliance report for a listing."""
    platform: str
    issues: list[ComplianceIssue] = field(default_factory=list)
    checked_rules: int = 0
    passed_rules: int = 0

    @property
    def errors(self) -> list[ComplianceIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ComplianceIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def infos(self) -> list[ComplianceIssue]:
        return [i for i in self.issues if i.severity == Severity.INFO]

    @property
    def score(self) -> float:
        """Compliance score 0-100."""
        if self.checked_rules == 0:
            return 100.0
        error_penalty = len(self.errors) * 10
        warning_penalty = len(self.warnings) * 3
        info_penalty = len(self.infos) * 1
        total_penalty = error_penalty + warning_penalty + info_penalty
        return max(0, min(100, 100 - total_penalty))

    @property
    def is_compliant(self) -> bool:
        """True if no errors."""
        return len(self.errors) == 0

    def format_report(self) -> str:
        """Format as readable text report."""
        grade = "✅ PASS" if self.is_compliant else "❌ FAIL"
        lines = [
            f"📋 Compliance Report: {self.platform.upper()}",
            f"Score: {self.score:.0f}/100 | {grade}",
            f"Rules checked: {self.checked_rules} | Passed: {self.passed_rules}",
            f"Errors: {len(self.errors)} | Warnings: {len(self.warnings)} | Info: {len(self.infos)}",
            "",
        ]
        if self.errors:
            lines.append("❌ ERRORS (must fix):")
            for issue in self.errors:
                lines.append(f"  {issue}")
            lines.append("")
        if self.warnings:
            lines.append("⚠️ WARNINGS (should fix):")
            for issue in self.warnings:
                lines.append(f"  {issue}")
            lines.append("")
        if self.infos:
            lines.append("💡 SUGGESTIONS:")
            for issue in self.infos:
                lines.append(f"  {issue}")

        return "\n".join(lines)


# =============================================================================
# Platform rules definitions
# =============================================================================

@dataclass
class CharLimit:
    field: str
    min_chars: int = 0
    max_chars: int = 999999
    recommended_min: int = 0
    recommended_max: int = 999999


@dataclass
class PlatformRules:
    """Complete rule set for a platform."""
    name: str
    char_limits: list[CharLimit] = field(default_factory=list)
    prohibited_words: list[str] = field(default_factory=list)
    prohibited_patterns: list[str] = field(default_factory=list)
    required_fields: list[str] = field(default_factory=list)
    html_allowed: bool = False
    emoji_allowed: bool = True
    max_bullet_count: int = 5
    max_images: int = 9
    min_images: int = 1
    special_rules: dict[str, str] = field(default_factory=dict)


PLATFORM_RULES: dict[str, PlatformRules] = {
    "amazon": PlatformRules(
        name="Amazon",
        char_limits=[
            CharLimit("title", min_chars=50, max_chars=200,
                      recommended_min=80, recommended_max=150),
            CharLimit("bullet_point", min_chars=10, max_chars=500,
                      recommended_min=100, recommended_max=250),
            CharLimit("description", min_chars=100, max_chars=2000,
                      recommended_min=300, recommended_max=1500),
            CharLimit("search_terms", min_chars=0, max_chars=250,
                      recommended_min=100, recommended_max=249),
        ],
        prohibited_words=[
            "best seller", "best-seller", "#1", "number one", "top rated",
            "award winning", "buy now", "free shipping", "on sale",
            "limited time", "act now", "hurry", "lowest price",
            "guaranteed", "satisfaction guaranteed", "money back",
            "as seen on tv", "patent pending", "FDA approved",
            "clinically proven", "doctor recommended",
            "cheap", "cheapest", "bargain", "discount",
            "call now", "order now", "click here",
        ],
        prohibited_patterns=[
            r"[\$€£]\d+",                     # Price in title
            r"\b(sale|deal|promo)\b",          # Promotional language
            r"!!+",                            # Multiple exclamation marks
            r"ALL\s+CAPS\s+WORDS",            # Excessive caps
            r"https?://",                      # URLs
            r"\b(sexy|adult|xxx)\b",          # Restricted content
        ],
        required_fields=["title", "bullet_points", "description"],
        html_allowed=True,
        emoji_allowed=False,
        max_bullet_count=5,
        max_images=9,
        min_images=1,
        special_rules={
            "title_no_all_caps": "Title must not be in ALL CAPS",
            "title_capitalize_first": "Capitalize first letter of each major word",
            "no_html_in_title": "HTML tags not allowed in title",
            "search_terms_no_asin": "Do not include ASINs in search terms",
            "search_terms_no_brand": "Do not repeat brand name in search terms",
            "bullets_no_shipping": "Do not mention shipping info in bullets",
            "no_time_sensitive": "No time-sensitive language (today only, etc.)",
        },
    ),

    "shopee": PlatformRules(
        name="Shopee",
        char_limits=[
            CharLimit("title", min_chars=20, max_chars=120,
                      recommended_min=50, recommended_max=100),
            CharLimit("description", min_chars=50, max_chars=3000,
                      recommended_min=300, recommended_max=2000),
        ],
        prohibited_words=[
            "fake", "replica", "counterfeit", "knockoff", "imitation",
            "aaa quality", "1:1 copy", "mirror quality",
            "whatsapp", "wechat", "line", "contact me",
            "other shop", "competitor", "cheaper elsewhere",
        ],
        prohibited_patterns=[
            r"[\+]?\d{8,}",                   # Phone numbers
            r"https?://(?!shopee)",            # External URLs
            r"\b(wa|whatsapp|wechat|line)\s*:?\s*\d+",
        ],
        required_fields=["title", "description"],
        html_allowed=False,
        emoji_allowed=True,
        max_bullet_count=10,
        max_images=9,
        min_images=3,
        special_rules={
            "emoji_encouraged": "Use emojis to improve engagement",
            "hashtags_in_desc": "Add relevant hashtags in description",
            "local_language": "Match language to target market",
        },
    ),

    "lazada": PlatformRules(
        name="Lazada",
        char_limits=[
            CharLimit("title", min_chars=20, max_chars=150,
                      recommended_min=60, recommended_max=120),
            CharLimit("short_description", min_chars=50, max_chars=500,
                      recommended_min=100, recommended_max=400),
            CharLimit("long_description", min_chars=100, max_chars=5000,
                      recommended_min=500, recommended_max=3000),
        ],
        prohibited_words=[
            "cheapest", "lowest price", "number 1", "#1 selling",
            "guaranteed delivery", "free gift", "buy 1 get 1",
            "contact seller", "off-platform", "whatsapp", "wechat",
        ],
        required_fields=["title", "short_description", "long_description"],
        html_allowed=True,
        emoji_allowed=True,
        max_images=8,
        min_images=3,
    ),

    "aliexpress": PlatformRules(
        name="AliExpress",
        char_limits=[
            CharLimit("title", min_chars=10, max_chars=128,
                      recommended_min=60, recommended_max=120),
            CharLimit("description", min_chars=100, max_chars=10000,
                      recommended_min=500, recommended_max=5000),
        ],
        prohibited_words=[
            "branded", "original brand", "genuine brand",  # IP sensitive
            "replica", "copy", "fake", "1:1",
            "dropship", "dropshipping",
            "contact us on whatsapp", "off platform",
        ],
        prohibited_patterns=[
            r"[\+]?\d{10,}",                  # Phone numbers
            r"https?://(?!aliexpress)",        # External URLs
        ],
        required_fields=["title", "description", "keywords"],
        html_allowed=True,
        emoji_allowed=True,
        max_images=6,
        min_images=1,
        special_rules={
            "multi_language_title": "Consider English + Russian/Spanish keywords",
            "shipping_in_desc": "Include estimated shipping time",
            "voltage_warning": "Mention voltage/plug type for electronics",
        },
    ),

    "tiktok_shop": PlatformRules(
        name="TikTok Shop",
        char_limits=[
            CharLimit("title", min_chars=10, max_chars=100,
                      recommended_min=30, recommended_max=80),
            CharLimit("description", min_chars=50, max_chars=2000,
                      recommended_min=200, recommended_max=1000),
        ],
        prohibited_words=[
            "link in bio", "click link", "DM me", "comment to buy",
            "free", "giveaway", "raffle", "lottery",
            "fake", "counterfeit", "replica", "knockoff",
            "cure", "treat", "diagnose", "FDA",
            "weight loss guaranteed", "overnight results",
        ],
        prohibited_patterns=[
            r"https?://",                      # All URLs
            r"@\w+",                           # Competitor handles
        ],
        required_fields=["title", "description"],
        html_allowed=False,
        emoji_allowed=True,
        max_images=9,
        min_images=1,
        special_rules={
            "video_first": "TikTok listings perform best with video",
            "trending_sounds": "Reference trending sounds in scripts",
            "short_punchy": "Keep descriptions short and punchy",
        },
    ),

    "shopify": PlatformRules(
        name="Shopify / Independent Store",
        char_limits=[
            CharLimit("seo_title", min_chars=30, max_chars=70,
                      recommended_min=50, recommended_max=60),
            CharLimit("meta_description", min_chars=50, max_chars=160,
                      recommended_min=120, recommended_max=155),
            CharLimit("description", min_chars=100, max_chars=50000,
                      recommended_min=300, recommended_max=5000),
        ],
        prohibited_words=[],  # Shopify is permissive
        required_fields=["seo_title", "meta_description", "description"],
        html_allowed=True,
        emoji_allowed=True,
        max_images=250,
        min_images=1,
        special_rules={
            "schema_markup": "Include structured data / JSON-LD for products",
            "alt_text": "All images need descriptive alt text",
            "canonical_url": "Set canonical URL for SEO",
            "faq_section": "FAQ schema improves search visibility",
        },
    ),

    "ebay": PlatformRules(
        name="eBay",
        char_limits=[
            CharLimit("title", min_chars=20, max_chars=80,
                      recommended_min=60, recommended_max=80),
            CharLimit("description", min_chars=100, max_chars=50000,
                      recommended_min=500, recommended_max=5000),
        ],
        prohibited_words=[
            "buy it now only", "no returns accepted",
            "as-is no warranty", "contact outside ebay",
            "paypal only", "cashier's check only",
            "fake", "replica", "knockoff", "bootleg",
        ],
        prohibited_patterns=[
            r"https?://(?!ebay)",              # External URLs
            r"<script",                         # Active content
            r"<iframe",                         # Embedded frames
            r"<form",                           # Forms
        ],
        required_fields=["title", "description", "item_specifics"],
        html_allowed=True,
        emoji_allowed=True,
        max_images=24,
        min_images=1,
        special_rules={
            "item_specifics_required": "Fill all relevant item specifics",
            "no_active_content": "No JavaScript/iframes/forms in description",
            "condition_accuracy": "Accurately describe item condition",
            "shipping_clarity": "Clear shipping cost and timeframe",
        },
    ),

    "walmart": PlatformRules(
        name="Walmart Marketplace",
        char_limits=[
            CharLimit("product_name", min_chars=25, max_chars=75,
                      recommended_min=50, recommended_max=75),
            CharLimit("shelf_description", min_chars=500, max_chars=4000,
                      recommended_min=1000, recommended_max=3000),
            CharLimit("short_description", min_chars=50, max_chars=1000,
                      recommended_min=100, recommended_max=500),
            CharLimit("key_feature", min_chars=10, max_chars=500,
                      recommended_min=50, recommended_max=200),
        ],
        prohibited_words=[
            "best seller", "#1", "top rated", "guaranteed",
            "free shipping", "on sale", "limited time", "act now",
            "as seen on tv", "patent pending",
            "price match", "lowest price", "beat any price",
            "used", "refurbished", "open box",
        ],
        prohibited_patterns=[
            r"[\$€£]\d+",                     # Prices
            r"!!+",                            # Multiple exclamation marks
            r"ALL\s+CAPS",                     # Excessive caps
            r"https?://",                      # URLs
        ],
        required_fields=["product_name", "shelf_description", "short_description", "key_features"],
        html_allowed=True,
        emoji_allowed=False,
        max_bullet_count=10,
        max_images=15,
        min_images=2,
        special_rules={
            "no_competitor_names": "Do not mention competitor brand names",
            "attribute_accuracy": "Product attributes must match actual product",
            "upc_required": "UPC/GTIN required for most categories",
        },
    ),
}


# =============================================================================
# Universal prohibited patterns (all platforms)
# =============================================================================

UNIVERSAL_PROHIBITED = [
    (r"\b(fuck|shit|damn|hell|ass|bitch)\b", "profanity", Severity.ERROR),
    (r"\b(nigger|faggot|retard)\b", "hate speech", Severity.ERROR),
    (r"\b(kill|murder|weapon|bomb|drug|narcotic)\b", "restricted content", Severity.WARNING),
    (r"<script[\s>]", "active content (XSS risk)", Severity.ERROR),
    (r"javascript:", "javascript injection", Severity.ERROR),
    (r"(password|credit.?card|ssn|social.?security)\s*[:=]", "PII exposure", Severity.ERROR),
]


# =============================================================================
# Compliance checker engine
# =============================================================================

class ComplianceChecker:
    """Check listings against platform rules."""

    def __init__(self):
        self.rules = PLATFORM_RULES

    @property
    def platforms(self) -> list[str]:
        return list(self.rules.keys())

    def get_rules(self, platform: str) -> Optional[PlatformRules]:
        return self.rules.get(platform.lower().replace(" ", "_"))

    def check(self, listing: dict[str, str], platform: str) -> ComplianceReport:
        """Run full compliance check on a listing.

        listing: dict mapping field names to their text content
                 e.g. {"title": "...", "description": "...", "bullet_points": "..."}
        """
        platform_key = platform.lower().replace(" ", "_")
        rules = self.rules.get(platform_key)
        if not rules:
            report = ComplianceReport(platform=platform)
            report.issues.append(ComplianceIssue(
                rule_id="UNKNOWN_PLATFORM",
                platform=platform,
                severity=Severity.WARNING,
                field="platform",
                message=f"Unknown platform: {platform}. Cannot validate rules.",
                suggestion=f"Supported: {', '.join(self.platforms)}",
            ))
            return report

        report = ComplianceReport(platform=platform)

        # 1. Check required fields
        self._check_required_fields(listing, rules, report)

        # 2. Check character limits
        self._check_char_limits(listing, rules, report)

        # 3. Check prohibited words
        self._check_prohibited_words(listing, rules, report)

        # 4. Check prohibited patterns
        self._check_prohibited_patterns(listing, rules, report)

        # 5. Check universal prohibited content
        self._check_universal(listing, report, platform_key)

        # 6. Check emoji compliance
        self._check_emoji(listing, rules, report)

        # 7. Check HTML compliance
        self._check_html(listing, rules, report)

        # 8. Check title quality
        self._check_title_quality(listing, rules, report)

        # 9. Check bullet count
        self._check_bullet_count(listing, rules, report)

        report.passed_rules = report.checked_rules - len(report.issues)
        return report

    def _check_required_fields(self, listing: dict, rules: PlatformRules,
                                report: ComplianceReport) -> None:
        for field in rules.required_fields:
            report.checked_rules += 1
            # Normalize field matching
            field_variants = [field, field.replace("_", " "), field.replace(" ", "_")]
            found = False
            for variant in field_variants:
                if variant in listing and listing[variant].strip():
                    found = True
                    break
            if not found:
                report.issues.append(ComplianceIssue(
                    rule_id="REQUIRED_FIELD",
                    platform=rules.name,
                    severity=Severity.ERROR,
                    field=field,
                    message=f"Required field '{field}' is missing or empty",
                    suggestion=f"Add content for '{field}'",
                ))

    def _check_char_limits(self, listing: dict, rules: PlatformRules,
                            report: ComplianceReport) -> None:
        for limit in rules.char_limits:
            report.checked_rules += 1
            field_value = listing.get(limit.field, "")
            if not field_value:
                continue

            char_count = len(field_value)

            # Hard limit violations
            if char_count > limit.max_chars:
                report.issues.append(ComplianceIssue(
                    rule_id="CHAR_LIMIT_MAX",
                    platform=rules.name,
                    severity=Severity.ERROR,
                    field=limit.field,
                    message=f"Exceeds maximum: {char_count}/{limit.max_chars} chars",
                    suggestion=f"Reduce to {limit.max_chars} chars or fewer",
                    current_value=f"{char_count} chars",
                    limit=limit.max_chars,
                ))
            elif char_count < limit.min_chars:
                report.issues.append(ComplianceIssue(
                    rule_id="CHAR_LIMIT_MIN",
                    platform=rules.name,
                    severity=Severity.ERROR,
                    field=limit.field,
                    message=f"Below minimum: {char_count}/{limit.min_chars} chars",
                    suggestion=f"Expand to at least {limit.min_chars} chars",
                    current_value=f"{char_count} chars",
                    limit=limit.min_chars,
                ))

            # Recommended range warnings
            if char_count > limit.recommended_max and char_count <= limit.max_chars:
                report.issues.append(ComplianceIssue(
                    rule_id="CHAR_RECOMMENDED_MAX",
                    platform=rules.name,
                    severity=Severity.INFO,
                    field=limit.field,
                    message=f"Above recommended: {char_count} chars (recommended ≤{limit.recommended_max})",
                    suggestion=f"Trim to ~{limit.recommended_max} chars for best results",
                ))
            elif char_count < limit.recommended_min and char_count >= limit.min_chars:
                report.issues.append(ComplianceIssue(
                    rule_id="CHAR_RECOMMENDED_MIN",
                    platform=rules.name,
                    severity=Severity.INFO,
                    field=limit.field,
                    message=f"Below recommended: {char_count} chars (recommended ≥{limit.recommended_min})",
                    suggestion=f"Expand to ~{limit.recommended_min} chars for better SEO",
                ))

    def _check_prohibited_words(self, listing: dict, rules: PlatformRules,
                                 report: ComplianceReport) -> None:
        report.checked_rules += 1
        for field_name, field_value in listing.items():
            if not field_value:
                continue
            text_lower = field_value.lower()
            for word in rules.prohibited_words:
                if word.lower() in text_lower:
                    report.issues.append(ComplianceIssue(
                        rule_id="PROHIBITED_WORD",
                        platform=rules.name,
                        severity=Severity.ERROR,
                        field=field_name,
                        message=f"Contains prohibited phrase: '{word}'",
                        suggestion=f"Remove or rephrase '{word}'",
                    ))

    def _check_prohibited_patterns(self, listing: dict, rules: PlatformRules,
                                    report: ComplianceReport) -> None:
        report.checked_rules += 1
        # Patterns that are always errors (price, URLs in content)
        error_patterns = {r"[\$€£]\d+", r"https?://"}
        all_patterns = rules.prohibited_patterns
        for field_name, field_value in listing.items():
            if not field_value:
                continue
            for pattern in all_patterns:
                matches = re.findall(pattern, field_value, re.IGNORECASE)
                if matches:
                    severity = Severity.ERROR if pattern in error_patterns else Severity.WARNING
                    report.issues.append(ComplianceIssue(
                        rule_id="PROHIBITED_PATTERN",
                        platform=rules.name,
                        severity=severity,
                        field=field_name,
                        message=f"Matches prohibited pattern: {pattern}",
                        suggestion=f"Remove content matching: {matches[:3]}",
                    ))

    def _check_universal(self, listing: dict, report: ComplianceReport,
                          platform: str) -> None:
        report.checked_rules += 1
        for field_name, field_value in listing.items():
            if not field_value:
                continue
            for pattern, desc, severity in UNIVERSAL_PROHIBITED:
                if re.search(pattern, field_value, re.IGNORECASE):
                    report.issues.append(ComplianceIssue(
                        rule_id="UNIVERSAL_PROHIBITED",
                        platform=platform,
                        severity=severity,
                        field=field_name,
                        message=f"Contains {desc}",
                        suggestion=f"Remove {desc} content immediately",
                    ))

    def _check_emoji(self, listing: dict, rules: PlatformRules,
                      report: ComplianceReport) -> None:
        report.checked_rules += 1
        if rules.emoji_allowed:
            return

        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0001F900-\U0001F9FF"
            "\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF]+",
            flags=re.UNICODE,
        )
        for field_name, field_value in listing.items():
            if not field_value:
                continue
            if emoji_pattern.search(field_value):
                report.issues.append(ComplianceIssue(
                    rule_id="EMOJI_NOT_ALLOWED",
                    platform=rules.name,
                    severity=Severity.WARNING,
                    field=field_name,
                    message=f"Emojis not recommended on {rules.name}",
                    suggestion="Remove emojis from this platform's listing",
                ))

    def _check_html(self, listing: dict, rules: PlatformRules,
                     report: ComplianceReport) -> None:
        report.checked_rules += 1
        html_pattern = re.compile(r"<[a-zA-Z][^>]*>")

        title_field = listing.get("title", "") or listing.get("product_name", "")
        if title_field and html_pattern.search(title_field):
            report.issues.append(ComplianceIssue(
                rule_id="HTML_IN_TITLE",
                platform=rules.name,
                severity=Severity.ERROR,
                field="title",
                message="HTML tags found in title",
                suggestion="Remove all HTML tags from title",
            ))

        if not rules.html_allowed:
            for field_name, field_value in listing.items():
                if not field_value or field_name in ("title", "product_name"):
                    continue
                if html_pattern.search(field_value):
                    report.issues.append(ComplianceIssue(
                        rule_id="HTML_NOT_ALLOWED",
                        platform=rules.name,
                        severity=Severity.WARNING,
                        field=field_name,
                        message=f"HTML tags not supported on {rules.name}",
                        suggestion="Use plain text or platform-specific formatting",
                    ))

    def _check_title_quality(self, listing: dict, rules: PlatformRules,
                              report: ComplianceReport) -> None:
        title = listing.get("title", "") or listing.get("product_name", "")
        if not title:
            return

        report.checked_rules += 1

        # All caps check
        words = title.split()
        caps_words = [w for w in words if w.isupper() and len(w) > 2]
        if len(caps_words) > len(words) * 0.5:
            report.issues.append(ComplianceIssue(
                rule_id="TITLE_ALL_CAPS",
                platform=rules.name,
                severity=Severity.WARNING,
                field="title",
                message="Title has excessive CAPS (>50% of words)",
                suggestion="Use title case instead of ALL CAPS",
            ))

        # Repeated characters
        if re.search(r"(.)\1{3,}", title):
            report.issues.append(ComplianceIssue(
                rule_id="TITLE_REPEATED_CHARS",
                platform=rules.name,
                severity=Severity.WARNING,
                field="title",
                message="Title contains repeated characters (e.g., '!!!!')",
                suggestion="Remove repeated characters",
            ))

        # Keyword stuffing (same word 3+ times)
        word_freq: dict[str, int] = {}
        for w in words:
            w_lower = w.lower().strip(",.;:-!?")
            if len(w_lower) > 2:
                word_freq[w_lower] = word_freq.get(w_lower, 0) + 1
        stuffed = [w for w, c in word_freq.items() if c >= 3]
        if stuffed:
            report.issues.append(ComplianceIssue(
                rule_id="TITLE_KEYWORD_STUFFING",
                platform=rules.name,
                severity=Severity.WARNING,
                field="title",
                message=f"Possible keyword stuffing: {', '.join(stuffed)}",
                suggestion="Use each keyword once or twice maximum",
            ))

    def _check_bullet_count(self, listing: dict, rules: PlatformRules,
                             report: ComplianceReport) -> None:
        bullets = listing.get("bullet_points", "")
        if not bullets:
            return

        report.checked_rules += 1
        # Count bullets by newlines or bullet markers
        bullet_lines = [
            line.strip() for line in bullets.split("\n")
            if line.strip() and (
                line.strip().startswith(("-", "•", "★", "✓", "✔", "·", "⚡", "🔋", "🎯", "📦", "💡"))
                or re.match(r"^\d+[\.\)]\s", line.strip())
            )
        ]
        if not bullet_lines:
            bullet_lines = [l.strip() for l in bullets.split("\n") if l.strip()]

        if len(bullet_lines) > rules.max_bullet_count:
            report.issues.append(ComplianceIssue(
                rule_id="BULLET_COUNT_MAX",
                platform=rules.name,
                severity=Severity.WARNING,
                field="bullet_points",
                message=f"Too many bullets: {len(bullet_lines)}/{rules.max_bullet_count}",
                suggestion=f"Reduce to {rules.max_bullet_count} or fewer bullet points",
            ))

    def check_multi_platform(self, listing: dict[str, str],
                              platforms: list[str]) -> dict[str, ComplianceReport]:
        """Check listing against multiple platforms."""
        return {p: self.check(listing, p) for p in platforms}

    def get_platform_summary(self, platform: str) -> str:
        """Get human-readable summary of platform rules."""
        rules = self.get_rules(platform)
        if not rules:
            return f"Unknown platform: {platform}"

        lines = [
            f"📋 **{rules.name} Compliance Rules**",
            "",
            "**Character Limits:**",
        ]
        for cl in rules.char_limits:
            lines.append(f"  - {cl.field}: {cl.min_chars}-{cl.max_chars} "
                        f"(recommended {cl.recommended_min}-{cl.recommended_max})")

        lines.extend([
            "",
            f"**Required Fields:** {', '.join(rules.required_fields)}",
            f"**HTML Allowed:** {'Yes' if rules.html_allowed else 'No'}",
            f"**Emoji Allowed:** {'Yes' if rules.emoji_allowed else 'No'}",
            f"**Max Bullets:** {rules.max_bullet_count}",
            f"**Images:** {rules.min_images}-{rules.max_images}",
            f"**Prohibited Words:** {len(rules.prohibited_words)} terms",
        ])

        if rules.special_rules:
            lines.extend(["", "**Special Rules:**"])
            for key, desc in rules.special_rules.items():
                lines.append(f"  - {desc}")

        return "\n".join(lines)
