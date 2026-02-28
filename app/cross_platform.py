"""Cross-Platform Listing Adapter.

Automatically adapt a single listing to multiple marketplace formats:
- Amazon (title limits, bullet points, backend keywords)
- Shopify (HTML descriptions, SEO meta, tags)
- eBay (item specifics, condition descriptions)
- AliExpress (long descriptions, specifications table)
- Etsy (tags limit 13, materials, occasion)
- Walmart (shelf/rich descriptions, key features)

Handles character limits, formatting rules, and platform-specific best practices.
"""
import re
import html
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Platform(str, Enum):
    AMAZON = "amazon"
    SHOPIFY = "shopify"
    EBAY = "ebay"
    ALIEXPRESS = "aliexpress"
    ETSY = "etsy"
    WALMART = "walmart"


@dataclass
class PlatformLimits:
    """Character/count limits for a marketplace."""
    title_max_chars: int = 200
    title_min_chars: int = 10
    bullet_count: int = 5
    bullet_max_chars: int = 500
    description_max_chars: int = 2000
    keyword_max_count: int = 50
    keyword_max_chars: int = 250
    tag_max_count: int = 0  # 0 = no tag field
    image_min_count: int = 1
    image_max_count: int = 9
    allows_html: bool = False
    allows_emoji: bool = True


PLATFORM_LIMITS = {
    Platform.AMAZON: PlatformLimits(
        title_max_chars=200,
        title_min_chars=50,
        bullet_count=5,
        bullet_max_chars=500,
        description_max_chars=2000,
        keyword_max_chars=249,
        keyword_max_count=0,  # Amazon uses byte-count keywords
        allows_html=False,
        allows_emoji=False,
    ),
    Platform.SHOPIFY: PlatformLimits(
        title_max_chars=255,
        title_min_chars=10,
        bullet_count=0,  # Shopify uses HTML description
        description_max_chars=50000,
        keyword_max_count=0,
        tag_max_count=250,
        allows_html=True,
        allows_emoji=True,
    ),
    Platform.EBAY: PlatformLimits(
        title_max_chars=80,
        title_min_chars=20,
        bullet_count=0,
        description_max_chars=50000,
        keyword_max_count=0,
        allows_html=True,
        allows_emoji=False,
    ),
    Platform.ALIEXPRESS: PlatformLimits(
        title_max_chars=128,
        title_min_chars=10,
        bullet_count=0,
        description_max_chars=50000,
        keyword_max_count=0,
        allows_html=True,
        allows_emoji=True,
    ),
    Platform.ETSY: PlatformLimits(
        title_max_chars=140,
        title_min_chars=10,
        bullet_count=0,
        description_max_chars=10000,
        keyword_max_count=0,
        tag_max_count=13,
        allows_html=False,
        allows_emoji=True,
    ),
    Platform.WALMART: PlatformLimits(
        title_max_chars=200,
        title_min_chars=25,
        bullet_count=5,
        bullet_max_chars=1000,
        description_max_chars=4000,
        keyword_max_count=0,
        allows_html=True,
        allows_emoji=False,
    ),
}


@dataclass
class UniversalListing:
    """A platform-agnostic listing that can be adapted to any marketplace."""
    title: str = ""
    brand: str = ""
    bullets: list[str] = field(default_factory=list)
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    price: float = 0.0
    images: list[str] = field(default_factory=list)
    category: str = ""
    attributes: dict = field(default_factory=dict)
    # Raw material for adaptation
    features: list[str] = field(default_factory=list)
    materials: list[str] = field(default_factory=list)
    dimensions: dict = field(default_factory=dict)


@dataclass
class AdaptedListing:
    """A listing adapted to a specific platform."""
    platform: Platform
    title: str = ""
    bullets: list[str] = field(default_factory=list)
    description: str = ""
    keywords: str = ""  # Platform-formatted keyword string
    tags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    truncations: list[str] = field(default_factory=list)
    score: float = 100.0  # Compliance score

    def is_compliant(self) -> bool:
        return len(self.warnings) == 0

    def summary(self) -> str:
        lines = [
            f"Platform: {self.platform.value.upper()}",
            f"Title ({len(self.title)} chars): {self.title}",
            f"Bullets: {len(self.bullets)}",
            f"Description: {len(self.description)} chars",
            f"Keywords: {len(self.keywords)} chars",
            f"Tags: {len(self.tags)}",
            f"Score: {self.score:.0f}/100",
        ]
        if self.warnings:
            lines.append(f"⚠️ Warnings: {len(self.warnings)}")
            for w in self.warnings:
                lines.append(f"  - {w}")
        if self.truncations:
            lines.append(f"✂️ Truncations: {len(self.truncations)}")
            for t in self.truncations:
                lines.append(f"  - {t}")
        return "\n".join(lines)


EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251"
    "\U0001f926-\U0001f937\U00010000-\U0010ffff\u2640-\u2642\u2600-\u2B55"
    "\u200d\u23cf\u23e9\u231a\ufe0f\u3030\u2764\u2714\u2716]+",
    flags=re.UNICODE
)


def strip_emojis(text: str) -> str:
    """Remove all emojis from text."""
    return EMOJI_RE.sub("", text).strip()


def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text).strip()


def smart_truncate(text: str, max_chars: int, suffix: str = "...") -> str:
    """Truncate text at word boundary."""
    if len(text) <= max_chars:
        return text
    truncated = text[: max_chars - len(suffix)]
    # Cut at last space
    last_space = truncated.rfind(" ")
    if last_space > max_chars // 2:
        truncated = truncated[:last_space]
    return truncated.rstrip() + suffix


def text_to_html_description(text: str, bullets: list[str]) -> str:
    """Convert plain text + bullets to HTML description."""
    parts = []
    if bullets:
        parts.append("<ul>")
        for b in bullets:
            parts.append(f"  <li>{html.escape(b)}</li>")
        parts.append("</ul>")
    if text:
        paragraphs = text.split("\n\n")
        for p in paragraphs:
            p = p.strip()
            if p:
                parts.append(f"<p>{html.escape(p)}</p>")
    return "\n".join(parts)


def extract_keywords_from_text(text: str, max_keywords: int = 50) -> list[str]:
    """Extract potential keywords from listing text."""
    words = re.findall(r"[a-zA-Z\u4e00-\u9fff]{2,}", text.lower())
    # Simple frequency-based extraction
    freq: dict[str, int] = {}
    stop_words = {
        "the", "and", "for", "with", "this", "that", "your", "our",
        "from", "are", "was", "will", "can", "has", "have", "been",
        "its", "not", "but", "all", "their", "each", "which",
    }
    for w in words:
        if w not in stop_words:
            freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, _ in sorted_words[:max_keywords]]


def adapt_for_amazon(listing: UniversalListing) -> AdaptedListing:
    """Adapt listing for Amazon marketplace."""
    limits = PLATFORM_LIMITS[Platform.AMAZON]
    result = AdaptedListing(platform=Platform.AMAZON)
    warnings = []
    truncations = []

    # Title: Brand + Key Features, no emojis
    title = strip_emojis(listing.title)
    if listing.brand and listing.brand.lower() not in title.lower():
        title = f"{listing.brand} {title}"
    if len(title) > limits.title_max_chars:
        title = smart_truncate(title, limits.title_max_chars, "")
        truncations.append(f"Title truncated to {limits.title_max_chars} chars")
    if len(title) < limits.title_min_chars:
        warnings.append(f"Title too short ({len(title)} chars, min {limits.title_min_chars})")
    result.title = title

    # Bullets: max 5, each under 500 chars
    bullets = listing.bullets[:limits.bullet_count] if listing.bullets else []
    if not bullets and listing.features:
        bullets = listing.features[:limits.bullet_count]
    adapted_bullets = []
    for i, b in enumerate(bullets):
        b = strip_emojis(b)
        if len(b) > limits.bullet_max_chars:
            b = smart_truncate(b, limits.bullet_max_chars)
            truncations.append(f"Bullet {i+1} truncated")
        adapted_bullets.append(b)
    if len(adapted_bullets) < limits.bullet_count:
        warnings.append(f"Only {len(adapted_bullets)} bullets (recommended {limits.bullet_count})")
    result.bullets = adapted_bullets

    # Description
    desc = strip_emojis(strip_html(listing.description))
    if len(desc) > limits.description_max_chars:
        desc = smart_truncate(desc, limits.description_max_chars)
        truncations.append("Description truncated")
    result.description = desc

    # Backend keywords: max 249 bytes, comma-separated, no brand/ASIN
    kws = listing.keywords[:]
    kw_str = ",".join(kws)
    while len(kw_str.encode("utf-8")) > limits.keyword_max_chars and kws:
        kws.pop()
        kw_str = ",".join(kws)
    result.keywords = kw_str

    result.warnings = warnings
    result.truncations = truncations
    result.score = max(0, 100 - len(warnings) * 10 - len(truncations) * 5)
    return result


def adapt_for_shopify(listing: UniversalListing) -> AdaptedListing:
    """Adapt listing for Shopify store."""
    limits = PLATFORM_LIMITS[Platform.SHOPIFY]
    result = AdaptedListing(platform=Platform.SHOPIFY)
    warnings = []
    truncations = []

    title = listing.title
    if len(title) > limits.title_max_chars:
        title = smart_truncate(title, limits.title_max_chars)
        truncations.append("Title truncated")
    result.title = title

    # Shopify uses HTML description
    result.description = text_to_html_description(listing.description, listing.bullets)
    if len(result.description) > limits.description_max_chars:
        result.description = result.description[:limits.description_max_chars]
        truncations.append("Description truncated")

    # Tags
    tags = listing.tags[:limits.tag_max_count] if listing.tags else listing.keywords[:limits.tag_max_count]
    result.tags = tags

    # SEO keywords in meta
    result.keywords = ", ".join(listing.keywords[:20])

    result.warnings = warnings
    result.truncations = truncations
    result.score = max(0, 100 - len(warnings) * 10 - len(truncations) * 5)
    return result


def adapt_for_ebay(listing: UniversalListing) -> AdaptedListing:
    """Adapt listing for eBay."""
    limits = PLATFORM_LIMITS[Platform.EBAY]
    result = AdaptedListing(platform=Platform.EBAY)
    warnings = []
    truncations = []

    title = strip_emojis(listing.title)
    if len(title) > limits.title_max_chars:
        title = smart_truncate(title, limits.title_max_chars, "")
        truncations.append(f"Title truncated to {limits.title_max_chars} chars")
    result.title = title

    # eBay allows HTML descriptions
    result.description = text_to_html_description(listing.description, listing.bullets)

    result.warnings = warnings
    result.truncations = truncations
    result.score = max(0, 100 - len(warnings) * 10 - len(truncations) * 5)
    return result


def adapt_for_etsy(listing: UniversalListing) -> AdaptedListing:
    """Adapt listing for Etsy."""
    limits = PLATFORM_LIMITS[Platform.ETSY]
    result = AdaptedListing(platform=Platform.ETSY)
    warnings = []
    truncations = []

    title = listing.title
    if len(title) > limits.title_max_chars:
        title = smart_truncate(title, limits.title_max_chars)
        truncations.append("Title truncated")
    result.title = title

    desc = listing.description
    if len(desc) > limits.description_max_chars:
        desc = smart_truncate(desc, limits.description_max_chars)
        truncations.append("Description truncated")
    result.description = desc

    # Etsy: max 13 tags
    tags = (listing.tags or listing.keywords)[:limits.tag_max_count]
    if len(tags) < limits.tag_max_count:
        warnings.append(f"Only {len(tags)} tags (Etsy allows {limits.tag_max_count})")
    result.tags = tags

    result.warnings = warnings
    result.truncations = truncations
    result.score = max(0, 100 - len(warnings) * 10 - len(truncations) * 5)
    return result


def adapt_for_aliexpress(listing: UniversalListing) -> AdaptedListing:
    """Adapt listing for AliExpress."""
    limits = PLATFORM_LIMITS[Platform.ALIEXPRESS]
    result = AdaptedListing(platform=Platform.ALIEXPRESS)
    warnings = []
    truncations = []

    title = listing.title
    if len(title) > limits.title_max_chars:
        title = smart_truncate(title, limits.title_max_chars)
        truncations.append("Title truncated")
    result.title = title

    # AliExpress supports HTML with specs table
    desc_parts = []
    if listing.description:
        desc_parts.append(f"<p>{html.escape(listing.description)}</p>")
    if listing.dimensions:
        desc_parts.append("<h3>Specifications</h3><table>")
        for k, v in listing.dimensions.items():
            desc_parts.append(f"<tr><td>{html.escape(k)}</td><td>{html.escape(str(v))}</td></tr>")
        desc_parts.append("</table>")
    if listing.materials:
        desc_parts.append(f"<p><strong>Materials:</strong> {', '.join(listing.materials)}</p>")
    result.description = "\n".join(desc_parts)

    result.warnings = warnings
    result.truncations = truncations
    result.score = max(0, 100 - len(warnings) * 10 - len(truncations) * 5)
    return result


def adapt_for_walmart(listing: UniversalListing) -> AdaptedListing:
    """Adapt listing for Walmart Marketplace."""
    limits = PLATFORM_LIMITS[Platform.WALMART]
    result = AdaptedListing(platform=Platform.WALMART)
    warnings = []
    truncations = []

    title = strip_emojis(listing.title)
    if listing.brand and listing.brand.lower() not in title.lower():
        title = f"{listing.brand} - {title}"
    if len(title) > limits.title_max_chars:
        title = smart_truncate(title, limits.title_max_chars, "")
        truncations.append("Title truncated")
    result.title = title

    # Key features (bullets)
    bullets = listing.bullets[:limits.bullet_count] if listing.bullets else []
    adapted_bullets = []
    for b in bullets:
        b = strip_emojis(b)
        if len(b) > limits.bullet_max_chars:
            b = smart_truncate(b, limits.bullet_max_chars)
        adapted_bullets.append(b)
    result.bullets = adapted_bullets

    # Rich description (HTML)
    result.description = text_to_html_description(listing.description, [])
    if len(result.description) > limits.description_max_chars:
        result.description = result.description[:limits.description_max_chars]
        truncations.append("Description truncated")

    result.warnings = warnings
    result.truncations = truncations
    result.score = max(0, 100 - len(warnings) * 10 - len(truncations) * 5)
    return result


_ADAPTERS = {
    Platform.AMAZON: adapt_for_amazon,
    Platform.SHOPIFY: adapt_for_shopify,
    Platform.EBAY: adapt_for_ebay,
    Platform.ALIEXPRESS: adapt_for_aliexpress,
    Platform.ETSY: adapt_for_etsy,
    Platform.WALMART: adapt_for_walmart,
}


def adapt_listing(listing: UniversalListing, platform: Platform) -> AdaptedListing:
    """Adapt a universal listing to a specific platform."""
    adapter = _ADAPTERS.get(platform)
    if not adapter:
        raise ValueError(f"Unsupported platform: {platform}")
    return adapter(listing)


def adapt_all(listing: UniversalListing) -> dict[Platform, AdaptedListing]:
    """Adapt a listing to all supported platforms."""
    return {p: adapt_listing(listing, p) for p in Platform}


def cross_platform_report(listing: UniversalListing) -> str:
    """Generate a cross-platform compatibility report."""
    results = adapt_all(listing)
    lines = ["Cross-Platform Listing Report", "=" * 40]
    for platform, adapted in results.items():
        lines.append(f"\n--- {platform.value.upper()} ---")
        lines.append(f"Score: {adapted.score:.0f}/100")
        lines.append(f"Title: {adapted.title[:60]}...")
        if adapted.warnings:
            for w in adapted.warnings:
                lines.append(f"  ⚠️ {w}")
        if adapted.truncations:
            for t in adapted.truncations:
                lines.append(f"  ✂️ {t}")
        if adapted.is_compliant():
            lines.append("  ✅ Fully compliant")
    return "\n".join(lines)
