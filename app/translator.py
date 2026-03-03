"""Multi-language listing translator with locale-specific optimization.

Goes beyond simple translation — adapts listings for cultural norms,
search behavior, and platform conventions in each market.
"""
from dataclasses import dataclass, field

from app.ai_engine import call_ai


@dataclass
class LocaleProfile:
    code: str        # e.g. 'ja-JP'
    name: str        # e.g. 'Japanese (Japan)'
    currency: str    # e.g. '¥'
    platform_notes: str  # Cultural/platform tips
    search_behavior: str  # How users search in this locale


LOCALES = {
    "en-US": LocaleProfile(
        code="en-US",
        name="English (United States)",
        currency="$",
        platform_notes="Americans value convenience, free shipping, fast delivery. "
                       "Use imperial units (inches, pounds). Star ratings are critical.",
        search_behavior="Long-tail queries, specific model numbers, brand + product type.",
    ),
    "en-UK": LocaleProfile(
        code="en-UK",
        name="English (United Kingdom)",
        currency="£",
        platform_notes="British shoppers value quality, understatement, and trustworthiness. "
                       "Use metric units. Avoid over-hyped American-style copy.",
        search_behavior="Similar to US but with British spelling (colour, favourite).",
    ),
    "zh-CN": LocaleProfile(
        code="zh-CN",
        name="简体中文 (中国大陆)",
        currency="¥",
        platform_notes="中国消费者重视性价比、品牌背书、社交证明。用四字成语增强文案力度。"
                       "强调正品保障、售后服务。",
        search_behavior="关键词简短直接，品牌+品类+属性，如'华为手机128G'。",
    ),
    "zh-TW": LocaleProfile(
        code="zh-TW",
        name="繁體中文 (台灣)",
        currency="NT$",
        platform_notes="台灣消費者重視品質和CP值。用繁體字。避免大陸用語。"
                       "蝦皮平台用語與淘寶不同。",
        search_behavior="繁體關鍵字，品牌+類別，注意台灣用語差異。",
    ),
    "ja-JP": LocaleProfile(
        code="ja-JP",
        name="日本語 (日本)",
        currency="¥",
        platform_notes="Japanese buyers are detail-oriented. Include precise specs, "
                       "warranty info. Polite language (敬語). Seasonal relevance matters.",
        search_behavior="カタカナ for foreign brands, very specific searches.",
    ),
    "ko-KR": LocaleProfile(
        code="ko-KR",
        name="한국어 (한국)",
        currency="₩",
        platform_notes="Korean shoppers are trend-sensitive. K-beauty/K-style references work. "
                       "Social proof from Korean influencers. Review screenshots.",
        search_behavior="Brand-aware, trend keywords, influencer product names.",
    ),
    "de-DE": LocaleProfile(
        code="de-DE",
        name="Deutsch (Deutschland)",
        currency="€",
        platform_notes="German buyers value technical accuracy, quality certifications (TÜV, GS), "
                       "environmental sustainability. Formal tone.",
        search_behavior="Compound nouns, technical terms, certification keywords.",
    ),
    "fr-FR": LocaleProfile(
        code="fr-FR",
        name="Français (France)",
        currency="€",
        platform_notes="French consumers appreciate elegance, lifestyle context. "
                       "Made-in-France is a selling point. Avoid aggressive sales language.",
        search_behavior="Brand-focused, lifestyle keywords, fewer technical specs in search.",
    ),
    "es-ES": LocaleProfile(
        code="es-ES",
        name="Español (España)",
        currency="€",
        platform_notes="Spanish buyers value social recommendations and visual appeal. "
                       "Warm, friendly tone. Emphasize value for money.",
        search_behavior="Descriptive queries, less brand-focused than northern Europe.",
    ),
    "pt-BR": LocaleProfile(
        code="pt-BR",
        name="Português (Brasil)",
        currency="R$",
        platform_notes="Brazilian shoppers love promotions, installment payments (parcelamento). "
                       "Emotional copy works well. Frete grátis is king.",
        search_behavior="Portuguese keywords, often informal/colloquial queries.",
    ),
    "ar-AE": LocaleProfile(
        code="ar-AE",
        name="العربية (الإمارات)",
        currency="AED",
        platform_notes="UAE shoppers value luxury, premium brands, and fast delivery. "
                       "RTL text. Include both Arabic and English keywords.",
        search_behavior="Mix of Arabic and English, brand-heavy searches.",
    ),
    "th-TH": LocaleProfile(
        code="th-TH",
        name="ไทย (ประเทศไทย)",
        currency="฿",
        platform_notes="Thai shoppers are price-sensitive and love promotions. "
                       "Shopee/Lazada conventions. Cute/playful tone. Emoji-heavy.",
        search_behavior="Thai keywords, brand + product type, short queries.",
    ),
    "vi-VN": LocaleProfile(
        code="vi-VN",
        name="Tiếng Việt (Việt Nam)",
        currency="₫",
        platform_notes="Vietnamese shoppers compare extensively. Flash sales work well. "
                       "Shopee dominates. Detailed specs and real photos matter.",
        search_behavior="Vietnamese keywords, practical search terms.",
    ),
    "id-ID": LocaleProfile(
        code="id-ID",
        name="Bahasa Indonesia",
        currency="Rp",
        platform_notes="Indonesian shoppers value affordability and social proof. "
                       "Tokopedia/Shopee conventions. Include size charts.",
        search_behavior="Bahasa keywords mixed with English brand names.",
    ),
    "ms-MY": LocaleProfile(
        code="ms-MY",
        name="Bahasa Melayu (Malaysia)",
        currency="RM",
        platform_notes="Malaysian shoppers are multicultural (Malay/Chinese/Indian). "
                       "Shopee dominates. Bilingual listings perform well.",
        search_behavior="Mix of Malay and English, brand-focused.",
    ),
}


@dataclass
class TranslationResult:
    source_locale: str
    target_locale: str
    original: str
    translated: str
    adaptations: list[str] = field(default_factory=list)  # What was culturally adapted
    seo_changes: list[str] = field(default_factory=list)  # Keyword/SEO adaptations

    def summary(self) -> str:
        lines = [
            f"🌍 Translation: {self.source_locale} → {self.target_locale}",
            f"   Adaptations: {len(self.adaptations)}",
            f"   SEO changes: {len(self.seo_changes)}",
        ]
        for a in self.adaptations[:5]:
            lines.append(f"   • {a}")
        return "\n".join(lines)


def translate_listing(
    listing: str,
    target_locale: str,
    source_locale: str = "en-US",
    platform: str = "amazon",
) -> TranslationResult:
    """Translate and culturally adapt a listing for a target locale.

    Args:
        listing: Original listing text.
        target_locale: Target locale code (e.g. 'ja-JP', 'de-DE').
        source_locale: Source locale code.
        platform: Target platform.

    Returns:
        TranslationResult with adapted listing and change notes.
    """
    target_profile = LOCALES.get(target_locale)
    source_profile = LOCALES.get(source_locale)

    if not target_profile:
        # Fallback: basic translation
        translated = call_ai(
            f"Translate this {platform} product listing to {target_locale}. "
            f"Preserve formatting and SEO structure.\n\n{listing}"
        )
        return TranslationResult(
            source_locale=source_locale,
            target_locale=target_locale,
            original=listing,
            translated=translated,
            adaptations=["Basic translation (no locale profile available)"],
        )

    prompt = f"""You are an expert e-commerce localizer and cultural adapter.

TASK: Translate and adapt this product listing for {target_profile.name} market.

SOURCE LOCALE: {source_profile.name if source_profile else source_locale}
TARGET LOCALE: {target_profile.name}
PLATFORM: {platform}
CURRENCY: {target_profile.currency}

CULTURAL GUIDELINES:
{target_profile.platform_notes}

SEARCH BEHAVIOR:
{target_profile.search_behavior}

RULES:
1. Translate ALL text to {target_profile.name}
2. Adapt cultural references (units, idioms, social proof style)
3. Optimize keywords for {target_profile.name} search behavior
4. Adjust tone to match local expectations
5. Convert currency symbols to {target_profile.currency}
6. Preserve all formatting (**bold**, bullets, sections)

After the listing, add:
ADAPTATIONS:
- [list each cultural/localization change you made]

SEO_CHANGES:
- [list keyword/SEO optimizations for this locale]

ORIGINAL LISTING:
{listing}"""

    result = call_ai(prompt)

    # Parse adaptations and SEO changes from the result
    adaptations = []
    seo_changes = []
    translated = result
    in_adaptations = False
    in_seo = False
    listing_lines = []

    for line in result.split("\n"):
        stripped = line.strip()
        if stripped.upper().startswith("ADAPTATIONS:"):
            in_adaptations = True
            in_seo = False
            continue
        elif stripped.upper().startswith("SEO_CHANGES:") or stripped.upper().startswith("SEO CHANGES:"):
            in_seo = True
            in_adaptations = False
            continue

        if in_adaptations and stripped.startswith("-"):
            adaptations.append(stripped.lstrip("- "))
        elif in_seo and stripped.startswith("-"):
            seo_changes.append(stripped.lstrip("- "))
        elif not in_adaptations and not in_seo:
            listing_lines.append(line)

    translated = "\n".join(listing_lines).strip()

    return TranslationResult(
        source_locale=source_locale,
        target_locale=target_locale,
        original=listing,
        translated=translated,
        adaptations=adaptations,
        seo_changes=seo_changes,
    )


def list_locales() -> str:
    """Format available locales for display."""
    lines = ["🌍 Available Locales:", ""]
    for code, profile in sorted(LOCALES.items()):
        lines.append(f"  {profile.currency} `{code}` — {profile.name}")
    return "\n".join(lines)


def batch_translate(
    listing: str,
    target_locales: list[str],
    source_locale: str = "en-US",
    platform: str = "amazon",
) -> list[TranslationResult]:
    """Translate a listing to multiple locales.

    Args:
        listing: Original listing text.
        target_locales: List of target locale codes.
        source_locale: Source locale code.
        platform: Target platform.

    Returns:
        List of TranslationResult objects.
    """
    results = []
    for locale in target_locales:
        result = translate_listing(listing, locale, source_locale, platform)
        results.append(result)
    return results
