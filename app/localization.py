"""Listing Localization Engine.

Adapts product listings for different locales, marketplaces, and cultural contexts.

Features:
- Unit conversion (imperial ↔ metric)
- Currency formatting for 20+ currencies
- Cultural adaptation rules per marketplace
- Locale-specific compliance checks
- Measurement unit standardization
- Date/number format localization
- Cultural sensitivity analysis
- Marketplace-specific content guidelines
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ── Locale Definitions ─────────────────────────────────────

@dataclass
class LocaleConfig:
    code: str           # e.g., "en-US"
    language: str       # e.g., "English"
    country: str        # e.g., "United States"
    currency: str       # e.g., "USD"
    currency_symbol: str  # e.g., "$"
    currency_position: str  # "before" or "after"
    decimal_separator: str  # "." or ","
    thousands_separator: str  # "," or "."
    measurement: str    # "imperial" or "metric"
    date_format: str    # e.g., "MM/DD/YYYY"
    paper_size: str     # "letter" or "a4"
    voltage: str        # e.g., "120V/60Hz"
    plug_type: str      # e.g., "A/B"


LOCALES = {
    "en-US": LocaleConfig("en-US", "English", "United States", "USD", "$", "before", ".", ",", "imperial", "MM/DD/YYYY", "letter", "120V/60Hz", "A/B"),
    "en-GB": LocaleConfig("en-GB", "English", "United Kingdom", "GBP", "£", "before", ".", ",", "metric", "DD/MM/YYYY", "a4", "230V/50Hz", "G"),
    "en-AU": LocaleConfig("en-AU", "English", "Australia", "AUD", "A$", "before", ".", ",", "metric", "DD/MM/YYYY", "a4", "230V/50Hz", "I"),
    "en-CA": LocaleConfig("en-CA", "English", "Canada", "CAD", "C$", "before", ".", ",", "metric", "YYYY-MM-DD", "letter", "120V/60Hz", "A/B"),
    "de-DE": LocaleConfig("de-DE", "German", "Germany", "EUR", "€", "after", ",", ".", "metric", "DD.MM.YYYY", "a4", "230V/50Hz", "C/F"),
    "fr-FR": LocaleConfig("fr-FR", "French", "France", "EUR", "€", "after", ",", " ", "metric", "DD/MM/YYYY", "a4", "230V/50Hz", "C/E"),
    "es-ES": LocaleConfig("es-ES", "Spanish", "Spain", "EUR", "€", "after", ",", ".", "metric", "DD/MM/YYYY", "a4", "230V/50Hz", "C/F"),
    "it-IT": LocaleConfig("it-IT", "Italian", "Italy", "EUR", "€", "after", ",", ".", "metric", "DD/MM/YYYY", "a4", "230V/50Hz", "C/F/L"),
    "ja-JP": LocaleConfig("ja-JP", "Japanese", "Japan", "JPY", "¥", "before", ".", ",", "metric", "YYYY/MM/DD", "a4", "100V/50-60Hz", "A/B"),
    "zh-CN": LocaleConfig("zh-CN", "Chinese", "China", "CNY", "¥", "before", ".", ",", "metric", "YYYY-MM-DD", "a4", "220V/50Hz", "A/C/I"),
    "zh-TW": LocaleConfig("zh-TW", "Chinese", "Taiwan", "TWD", "NT$", "before", ".", ",", "metric", "YYYY/MM/DD", "a4", "110V/60Hz", "A/B"),
    "ko-KR": LocaleConfig("ko-KR", "Korean", "South Korea", "KRW", "₩", "before", ".", ",", "metric", "YYYY.MM.DD", "a4", "220V/60Hz", "C/F"),
    "pt-BR": LocaleConfig("pt-BR", "Portuguese", "Brazil", "BRL", "R$", "before", ",", ".", "metric", "DD/MM/YYYY", "a4", "127/220V/60Hz", "N"),
    "ru-RU": LocaleConfig("ru-RU", "Russian", "Russia", "RUB", "₽", "after", ",", " ", "metric", "DD.MM.YYYY", "a4", "220V/50Hz", "C/F"),
    "ar-SA": LocaleConfig("ar-SA", "Arabic", "Saudi Arabia", "SAR", "ر.س", "after", ".", ",", "metric", "DD/MM/YYYY", "a4", "220V/60Hz", "G"),
    "hi-IN": LocaleConfig("hi-IN", "Hindi", "India", "INR", "₹", "before", ".", ",", "metric", "DD/MM/YYYY", "a4", "230V/50Hz", "C/D/M"),
    "th-TH": LocaleConfig("th-TH", "Thai", "Thailand", "THB", "฿", "before", ".", ",", "metric", "DD/MM/YYYY", "a4", "220V/50Hz", "A/B/C/O"),
    "vi-VN": LocaleConfig("vi-VN", "Vietnamese", "Vietnam", "VND", "₫", "after", ",", ".", "metric", "DD/MM/YYYY", "a4", "220V/50Hz", "A/C"),
    "id-ID": LocaleConfig("id-ID", "Indonesian", "Indonesia", "IDR", "Rp", "before", ",", ".", "metric", "DD/MM/YYYY", "a4", "230V/50Hz", "C/F"),
    "ms-MY": LocaleConfig("ms-MY", "Malay", "Malaysia", "MYR", "RM", "before", ".", ",", "metric", "DD/MM/YYYY", "a4", "240V/50Hz", "G"),
    "tl-PH": LocaleConfig("tl-PH", "Filipino", "Philippines", "PHP", "₱", "before", ".", ",", "metric", "MM/DD/YYYY", "a4", "220V/60Hz", "A/B/C"),
    "nl-NL": LocaleConfig("nl-NL", "Dutch", "Netherlands", "EUR", "€", "before", ",", ".", "metric", "DD-MM-YYYY", "a4", "230V/50Hz", "C/F"),
    "pl-PL": LocaleConfig("pl-PL", "Polish", "Poland", "PLN", "zł", "after", ",", " ", "metric", "DD.MM.YYYY", "a4", "230V/50Hz", "C/E"),
    "sv-SE": LocaleConfig("sv-SE", "Swedish", "Sweden", "SEK", "kr", "after", ",", " ", "metric", "YYYY-MM-DD", "a4", "230V/50Hz", "C/F"),
    "tr-TR": LocaleConfig("tr-TR", "Turkish", "Turkey", "TRY", "₺", "before", ",", ".", "metric", "DD.MM.YYYY", "a4", "220V/50Hz", "C/F"),
    "mx-MX": LocaleConfig("mx-MX", "Spanish", "Mexico", "MXN", "MX$", "before", ".", ",", "metric", "DD/MM/YYYY", "letter", "127V/60Hz", "A/B"),
    "he-IL": LocaleConfig("he-IL", "Hebrew", "Israel", "ILS", "₪", "after", ".", ",", "metric", "DD/MM/YYYY", "a4", "230V/50Hz", "C/H"),
    "uk-UA": LocaleConfig("uk-UA", "Ukrainian", "Ukraine", "UAH", "₴", "after", ",", " ", "metric", "DD.MM.YYYY", "a4", "220V/50Hz", "C/F"),
}

# ── Marketplace → Locale Mapping ──────────────────────────

MARKETPLACE_LOCALES = {
    "amazon.com": "en-US",
    "amazon.co.uk": "en-GB",
    "amazon.de": "de-DE",
    "amazon.fr": "fr-FR",
    "amazon.es": "es-ES",
    "amazon.it": "it-IT",
    "amazon.co.jp": "ja-JP",
    "amazon.com.au": "en-AU",
    "amazon.ca": "en-CA",
    "amazon.com.br": "pt-BR",
    "amazon.nl": "nl-NL",
    "amazon.pl": "pl-PL",
    "amazon.se": "sv-SE",
    "amazon.com.tr": "tr-TR",
    "amazon.com.mx": "mx-MX",
    "amazon.in": "hi-IN",
    "amazon.sa": "ar-SA",
    "shopee.sg": "en-US",
    "shopee.co.th": "th-TH",
    "shopee.vn": "vi-VN",
    "shopee.co.id": "id-ID",
    "shopee.com.my": "ms-MY",
    "shopee.com.ph": "tl-PH",
    "shopee.tw": "zh-TW",
    "shopee.com.br": "pt-BR",
    "lazada.co.th": "th-TH",
    "lazada.vn": "vi-VN",
    "lazada.co.id": "id-ID",
    "lazada.com.my": "ms-MY",
    "lazada.com.ph": "tl-PH",
    "lazada.sg": "en-US",
    "aliexpress.com": "en-US",
    "temu.com": "en-US",
    "ebay.com": "en-US",
    "ebay.co.uk": "en-GB",
    "ebay.de": "de-DE",
    "ebay.com.au": "en-AU",
    "walmart.com": "en-US",
    "etsy.com": "en-US",
}


# ── Unit Conversion ────────────────────────────────────────

# Conversion factors: metric_value = imperial_value * factor
CONVERSIONS = {
    # Length
    "in_to_cm": 2.54,
    "ft_to_m": 0.3048,
    "yd_to_m": 0.9144,
    "mi_to_km": 1.60934,
    "cm_to_in": 1 / 2.54,
    "m_to_ft": 1 / 0.3048,
    "m_to_yd": 1 / 0.9144,
    "km_to_mi": 1 / 1.60934,
    # Weight
    "oz_to_g": 28.3495,
    "lb_to_kg": 0.453592,
    "g_to_oz": 1 / 28.3495,
    "kg_to_lb": 1 / 0.453592,
    # Volume
    "fl_oz_to_ml": 29.5735,
    "cup_to_ml": 236.588,
    "gal_to_l": 3.78541,
    "ml_to_fl_oz": 1 / 29.5735,
    "l_to_gal": 1 / 3.78541,
    # Temperature
    # Handled separately (non-linear)
    # Area
    "sq_ft_to_sq_m": 0.092903,
    "sq_m_to_sq_ft": 1 / 0.092903,
    "sq_in_to_sq_cm": 6.4516,
    "sq_cm_to_sq_in": 1 / 6.4516,
}

# Unit patterns for regex detection
IMPERIAL_PATTERNS = [
    (r'(\d+\.?\d*)\s*(?:inches|inch|in\.?|")', "in", "cm", "in_to_cm"),
    (r'(\d+\.?\d*)\s*(?:feet|foot|ft\.?|\')', "ft", "m", "ft_to_m"),
    (r'(\d+\.?\d*)\s*(?:yards?|yd\.?)', "yd", "m", "yd_to_m"),
    (r'(\d+\.?\d*)\s*(?:miles?|mi\.?)', "mi", "km", "mi_to_km"),
    (r'(\d+\.?\d*)\s*(?:ounces?|oz\.?)', "oz", "g", "oz_to_g"),
    (r'(\d+\.?\d*)\s*(?:pounds?|lbs?\.?)', "lb", "kg", "lb_to_kg"),
    (r'(\d+\.?\d*)\s*(?:fluid\s+ounces?|fl\.?\s*oz\.?)', "fl oz", "ml", "fl_oz_to_ml"),
    (r'(\d+\.?\d*)\s*(?:gallons?|gal\.?)', "gal", "L", "gal_to_l"),
    (r'(\d+\.?\d*)\s*(?:sq\.?\s*ft\.?|square\s+feet)', "sq ft", "sq m", "sq_ft_to_sq_m"),
]

METRIC_PATTERNS = [
    (r'(\d+\.?\d*)\s*(?:centimeters?|cm)', "cm", "in", "cm_to_in"),
    (r'(\d+\.?\d*)\s*(?:meters?|m)(?!\w)', "m", "ft", "m_to_ft"),
    (r'(\d+\.?\d*)\s*(?:kilometers?|km)', "km", "mi", "km_to_mi"),
    (r'(\d+\.?\d*)\s*(?:grams?|g)(?!\w)', "g", "oz", "g_to_oz"),
    (r'(\d+\.?\d*)\s*(?:kilograms?|kg)', "kg", "lb", "kg_to_lb"),
    (r'(\d+\.?\d*)\s*(?:milliliters?|ml|mL)', "ml", "fl oz", "ml_to_fl_oz"),
    (r'(\d+\.?\d*)\s*(?:liters?|litres?|l|L)(?!\w)', "L", "gal", "l_to_gal"),
]


def convert_unit(value: float, conversion_key: str) -> float:
    """Convert a value using the specified conversion."""
    factor = CONVERSIONS.get(conversion_key)
    if factor is None:
        return value
    return round(value * factor, 2)


def fahrenheit_to_celsius(f: float) -> float:
    return round((f - 32) * 5 / 9, 1)


def celsius_to_fahrenheit(c: float) -> float:
    return round(c * 9 / 5 + 32, 1)


# ── Cultural Adaptation Rules ──────────────────────────────

@dataclass
class CulturalRule:
    locale: str
    category: str
    rule: str
    severity: str  # "required", "recommended", "tip"


CULTURAL_RULES = [
    # Japan
    CulturalRule("ja-JP", "general", "Use polite/formal language (敬語). Avoid casual tone.", "required"),
    CulturalRule("ja-JP", "general", "Include detailed specifications - Japanese customers value precision.", "recommended"),
    CulturalRule("ja-JP", "sizing", "Use Japanese sizing (S/M/L runs smaller than US). Add size chart.", "required"),
    CulturalRule("ja-JP", "color", "Use Japanese color names alongside English. Some colors have cultural meanings.", "recommended"),
    CulturalRule("ja-JP", "electronics", "Specify 100V compatibility. Japan uses Type A/B plugs.", "required"),

    # China
    CulturalRule("zh-CN", "general", "Use simplified Chinese (简体中文). Include 卖点 (selling points) prominently.", "required"),
    CulturalRule("zh-CN", "general", "Emphasize value-for-money (性价比). Chinese consumers are price-conscious.", "recommended"),
    CulturalRule("zh-CN", "number", "Lucky numbers: 6, 8, 9. Avoid 4 (death). Consider in pricing.", "tip"),
    CulturalRule("zh-CN", "color", "Red = luck/prosperity. White = mourning. Avoid white packaging for gifts.", "recommended"),
    CulturalRule("zh-CN", "electronics", "Specify 220V/50Hz. Mention CCC certification if applicable.", "required"),

    # Germany
    CulturalRule("de-DE", "general", "Germans value factual, detailed descriptions. Avoid superlatives.", "recommended"),
    CulturalRule("de-DE", "general", "Include all legal disclaimers (Impressum, Widerrufsrecht).", "required"),
    CulturalRule("de-DE", "sizing", "Use EU sizing. Always include cm measurements.", "required"),
    CulturalRule("de-DE", "compliance", "CE marking required. WEEE registration for electronics.", "required"),
    CulturalRule("de-DE", "environmental", "Eco-friendliness is a strong selling point. Mention recyclability.", "recommended"),

    # France
    CulturalRule("fr-FR", "general", "Use formal French. Quality and craftsmanship resonate strongly.", "recommended"),
    CulturalRule("fr-FR", "compliance", "French product descriptions must be in French (Toubon Law).", "required"),
    CulturalRule("fr-FR", "sizing", "Use EU sizing with cm measurements.", "required"),

    # Brazil
    CulturalRule("pt-BR", "general", "Use Brazilian Portuguese (not European). Informal tone is OK.", "required"),
    CulturalRule("pt-BR", "pricing", "Include installment options (parcelas). Very important for Brazilian market.", "recommended"),
    CulturalRule("pt-BR", "compliance", "INMETRO certification required for many products.", "required"),
    CulturalRule("pt-BR", "electronics", "Voltage varies (127V/220V) by region. Always specify.", "required"),

    # Middle East
    CulturalRule("ar-SA", "general", "Right-to-left text. Ensure proper RTL formatting.", "required"),
    CulturalRule("ar-SA", "general", "Modesty in images and descriptions for clothing/beauty.", "required"),
    CulturalRule("ar-SA", "food", "Halal certification is essential for food products.", "required"),
    CulturalRule("ar-SA", "compliance", "SASO certification required for many product categories.", "required"),

    # South Korea
    CulturalRule("ko-KR", "general", "Korean consumers research extensively. Include detailed specs and reviews.", "recommended"),
    CulturalRule("ko-KR", "beauty", "K-beauty standards apply. Emphasize skincare ingredients.", "recommended"),
    CulturalRule("ko-KR", "general", "Include Korean reviews/ratings if available.", "recommended"),

    # Southeast Asia
    CulturalRule("th-TH", "general", "Thai consumers love promotions and free gifts. Highlight deals.", "recommended"),
    CulturalRule("id-ID", "general", "Halal certification important for cosmetics and food.", "required"),
    CulturalRule("tl-PH", "general", "English widely accepted. Mix of English and Filipino is common.", "tip"),
    CulturalRule("vi-VN", "general", "Price sensitivity is high. Emphasize value and discounts.", "recommended"),

    # India
    CulturalRule("hi-IN", "general", "English is widely used for e-commerce. Hindi optional.", "tip"),
    CulturalRule("hi-IN", "pricing", "EMI/installment options are important. Mention if available.", "recommended"),
    CulturalRule("hi-IN", "general", "Festive season (Diwali, etc.) is crucial for sales. Plan seasonal content.", "recommended"),

    # UK
    CulturalRule("en-GB", "general", "Use British English spelling (colour, catalogue, centre).", "required"),
    CulturalRule("en-GB", "sizing", "UK sizing differs from US. Include size conversion chart.", "required"),
    CulturalRule("en-GB", "compliance", "UKCA marking required post-Brexit for many categories.", "required"),
    CulturalRule("en-GB", "electronics", "UK uses Type G plug (3-pin). Specify compatibility.", "required"),

    # Australia
    CulturalRule("en-AU", "general", "Use Australian English. Informal tone is acceptable.", "recommended"),
    CulturalRule("en-AU", "compliance", "Australian safety standards (AS/NZS) required.", "required"),
    CulturalRule("en-AU", "electronics", "Australia uses Type I plug. 230V/50Hz.", "required"),

    # Mexico
    CulturalRule("mx-MX", "general", "Use Latin American Spanish (not Castilian).", "required"),
    CulturalRule("mx-MX", "pricing", "Show MSI (months without interest) payment options.", "recommended"),
    CulturalRule("mx-MX", "electronics", "Mexico uses 127V/60Hz, Type A/B plugs.", "required"),
]


# ── Localization Engine ────────────────────────────────────

@dataclass
class UnitConversion:
    original: str
    converted: str
    original_value: float
    converted_value: float
    from_unit: str
    to_unit: str


@dataclass
class LocalizationIssue:
    category: str
    severity: str  # "error", "warning", "info"
    message: str
    suggestion: str = ""


@dataclass
class LocalizationResult:
    source_locale: str
    target_locale: str
    original_text: str
    localized_text: str
    unit_conversions: list[UnitConversion] = field(default_factory=list)
    currency_changes: list[str] = field(default_factory=list)
    cultural_rules: list[CulturalRule] = field(default_factory=list)
    issues: list[LocalizationIssue] = field(default_factory=list)
    quality_score: float = 0.0  # 0-100

    def summary(self) -> str:
        lines = [
            f"🌐 Localization Report",
            f"Source: {self.source_locale} → Target: {self.target_locale}",
            f"Quality Score: {self.quality_score:.0f}/100",
            "",
        ]

        if self.unit_conversions:
            lines.append(f"📏 Unit Conversions ({len(self.unit_conversions)}):")
            for uc in self.unit_conversions[:10]:
                lines.append(f"  {uc.original} → {uc.converted}")

        if self.cultural_rules:
            lines.append("")
            lines.append(f"🎌 Cultural Rules ({len(self.cultural_rules)}):")
            for rule in self.cultural_rules:
                icon = {"required": "🔴", "recommended": "🟡", "tip": "🟢"}.get(rule.severity, "ℹ️")
                lines.append(f"  {icon} [{rule.category}] {rule.rule}")

        if self.issues:
            lines.append("")
            lines.append(f"⚠️ Issues ({len(self.issues)}):")
            for issue in self.issues:
                icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(issue.severity, "ℹ️")
                lines.append(f"  {icon} {issue.message}")
                if issue.suggestion:
                    lines.append(f"     💡 {issue.suggestion}")

        return "\n".join(lines)


class LocalizationEngine:
    """Localize product listings for different markets."""

    def __init__(self):
        pass

    def get_locale(self, code: str) -> Optional[LocaleConfig]:
        """Get locale configuration by code."""
        return LOCALES.get(code)

    def get_marketplace_locale(self, marketplace: str) -> Optional[LocaleConfig]:
        """Get locale for a marketplace domain."""
        code = MARKETPLACE_LOCALES.get(marketplace.lower())
        if code:
            return LOCALES.get(code)
        return None

    def localize(self, text: str, source_locale: str = "en-US",
                  target_locale: str = "de-DE",
                  product_category: str = "general") -> LocalizationResult:
        """Localize listing text from source to target locale.

        Handles unit conversion, currency notation, and cultural checks.
        Does NOT translate language (use translator module for that).
        """
        source = LOCALES.get(source_locale)
        target = LOCALES.get(target_locale)

        if not source or not target:
            return LocalizationResult(
                source_locale=source_locale,
                target_locale=target_locale,
                original_text=text,
                localized_text=text,
                issues=[LocalizationIssue("locale", "error",
                                           f"Unknown locale: {source_locale if not source else target_locale}")],
            )

        result = LocalizationResult(
            source_locale=source_locale,
            target_locale=target_locale,
            original_text=text,
            localized_text=text,
        )

        # Unit conversions
        if source.measurement != target.measurement:
            result.localized_text, result.unit_conversions = self._convert_units(
                result.localized_text, source.measurement, target.measurement
            )

        # Temperature conversions
        result.localized_text, temp_convs = self._convert_temperatures(
            result.localized_text, source_locale, target_locale
        )
        result.unit_conversions.extend(temp_convs)

        # Number format
        if source.decimal_separator != target.decimal_separator:
            result.localized_text = self._localize_numbers(
                result.localized_text, source, target
            )

        # Cultural rules
        result.cultural_rules = self._get_cultural_rules(target_locale, product_category)

        # Compliance issues
        result.issues = self._check_issues(text, source, target, product_category)

        # Quality score
        result.quality_score = self._calculate_quality(result)

        return result

    def _convert_units(self, text: str, from_system: str,
                        to_system: str) -> tuple[str, list[UnitConversion]]:
        """Convert measurement units in text."""
        conversions = []
        patterns = IMPERIAL_PATTERNS if from_system == "imperial" else METRIC_PATTERNS

        for pattern, from_unit, to_unit, conv_key in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = float(match.group(1))
                converted = convert_unit(value, conv_key)

                original_str = match.group(0)
                # Format nicely
                if converted == int(converted):
                    converted_str = f"{int(converted)} {to_unit}"
                else:
                    converted_str = f"{converted:.1f} {to_unit}"

                # Replace with both (original + converted)
                replacement = f"{original_str} ({converted_str})"
                text = text.replace(original_str, replacement, 1)

                conversions.append(UnitConversion(
                    original=original_str,
                    converted=converted_str,
                    original_value=value,
                    converted_value=converted,
                    from_unit=from_unit,
                    to_unit=to_unit,
                ))

        return text, conversions

    def _convert_temperatures(self, text: str, source: str,
                               target: str) -> tuple[str, list[UnitConversion]]:
        """Convert temperature values."""
        conversions = []

        # Detect if source uses Fahrenheit (US) or Celsius
        source_f = source.startswith("en-US")
        target_f = target.startswith("en-US")

        if source_f == target_f:
            return text, conversions

        if source_f:
            # F → C
            for match in re.finditer(r'(\d+\.?\d*)\s*°?\s*F(?:ahrenheit)?', text, re.IGNORECASE):
                f_val = float(match.group(1))
                c_val = fahrenheit_to_celsius(f_val)
                original = match.group(0)
                converted = f"{c_val}°C"
                text = text.replace(original, f"{original} ({converted})", 1)
                conversions.append(UnitConversion(original, converted, f_val, c_val, "°F", "°C"))
        else:
            # C → F
            for match in re.finditer(r'(\d+\.?\d*)\s*°?\s*C(?:elsius)?', text, re.IGNORECASE):
                c_val = float(match.group(1))
                f_val = celsius_to_fahrenheit(c_val)
                original = match.group(0)
                converted = f"{f_val}°F"
                text = text.replace(original, f"{original} ({converted})", 1)
                conversions.append(UnitConversion(original, converted, c_val, f_val, "°C", "°F"))

        return text, conversions

    def _localize_numbers(self, text: str, source: LocaleConfig,
                           target: LocaleConfig) -> str:
        """Convert number formatting (decimal/thousands separators)."""
        # This is tricky because we can't blindly replace separators
        # Only convert numbers that look like prices/measurements
        # Pattern: digits with source separators
        if source.decimal_separator == "." and target.decimal_separator == ",":
            # 1,234.56 → 1.234,56
            def replace_number(m):
                num = m.group(0)
                # Temporarily replace
                num = num.replace(",", "THOU")
                num = num.replace(".", ",")
                num = num.replace("THOU", ".")
                return num
            text = re.sub(r'\d{1,3}(?:,\d{3})*\.\d+', replace_number, text)

        return text

    def _get_cultural_rules(self, locale: str, category: str) -> list[CulturalRule]:
        """Get applicable cultural rules for locale and category."""
        rules = []
        for rule in CULTURAL_RULES:
            if rule.locale == locale:
                if rule.category in ("general", category):
                    rules.append(rule)
        return sorted(rules, key=lambda r: {"required": 0, "recommended": 1, "tip": 2}.get(r.severity, 3))

    def _check_issues(self, text: str, source: LocaleConfig,
                       target: LocaleConfig,
                       category: str) -> list[LocalizationIssue]:
        """Check for localization issues."""
        issues = []

        # Voltage/plug mismatch
        if source.voltage != target.voltage:
            voltage_mentioned = bool(re.search(r'\d{2,3}\s*V', text))
            if voltage_mentioned:
                issues.append(LocalizationIssue(
                    "electrical", "warning",
                    f"Source voltage ({source.voltage}) differs from target ({target.voltage})",
                    f"Add compatibility note: '{target.voltage}, {target.plug_type} plug'"
                ))
            elif category in ("electronics", "appliance", "tools"):
                issues.append(LocalizationIssue(
                    "electrical", "error",
                    f"No voltage info for electronics product. Target: {target.voltage}",
                    f"Add voltage compatibility: '{target.voltage}'"
                ))

        # Paper size (for stationery/office)
        if source.paper_size != target.paper_size and category in ("office", "stationery"):
            issues.append(LocalizationIssue(
                "sizing", "warning",
                f"Paper size differs: {source.paper_size} → {target.paper_size}",
                f"Specify '{target.paper_size}' paper size for {target.country}"
            ))

        # Currency symbols in text
        if source.currency_symbol in text and source.currency_symbol != target.currency_symbol:
            issues.append(LocalizationIssue(
                "currency", "info",
                f"Source currency symbol ({source.currency_symbol}) found in text",
                f"Consider converting to {target.currency_symbol} ({target.currency})"
            ))

        # Date format check
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',
            r'\d{1,2}-\d{1,2}-\d{2,4}',
            r'\d{1,2}\.\d{1,2}\.\d{2,4}',
        ]
        for pattern in date_patterns:
            if re.search(pattern, text):
                if source.date_format != target.date_format:
                    issues.append(LocalizationIssue(
                        "date", "warning",
                        f"Date format may need adjustment: {source.date_format} → {target.date_format}",
                        "Verify date format matches target locale"
                    ))
                break

        # Right-to-left check
        if target.code.startswith("ar") or target.code.startswith("he"):
            if not re.search(r'[\u0600-\u06FF\u0590-\u05FF]', text):
                issues.append(LocalizationIssue(
                    "direction", "warning",
                    "Target locale uses RTL text direction",
                    "Ensure proper RTL formatting in final rendering"
                ))

        # Imperial units in metric target
        if target.measurement == "metric":
            for pattern, from_unit, _, _ in IMPERIAL_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    issues.append(LocalizationIssue(
                        "units", "warning",
                        f"Imperial units ({from_unit}) found. Target uses metric system.",
                        "Convert or add metric equivalents"
                    ))
                    break

        # Metric units in imperial target
        if target.measurement == "imperial":
            for pattern, from_unit, _, _ in METRIC_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    issues.append(LocalizationIssue(
                        "units", "warning",
                        f"Metric units ({from_unit}) found. Target uses imperial system.",
                        "Convert or add imperial equivalents"
                    ))
                    break

        return issues

    def _calculate_quality(self, result: LocalizationResult) -> float:
        """Calculate localization quality score."""
        score = 100.0

        # Deduct for issues
        for issue in result.issues:
            if issue.severity == "error":
                score -= 15
            elif issue.severity == "warning":
                score -= 5
            elif issue.severity == "info":
                score -= 2

        # Deduct for unaddressed required cultural rules
        required_rules = [r for r in result.cultural_rules if r.severity == "required"]
        if required_rules:
            score -= len(required_rules) * 3  # Minor deduction as reminder

        # Bonus for unit conversions done
        if result.unit_conversions:
            score = min(100, score + 5)

        return max(0, min(100, score))

    def format_price(self, amount: float, locale_code: str) -> str:
        """Format a price according to locale conventions.

        Args:
            amount: Numeric price value.
            locale_code: Target locale code.

        Returns:
            Formatted price string.
        """
        locale = LOCALES.get(locale_code)
        if not locale:
            return f"${amount:.2f}"

        # Format number part
        if locale.currency == "JPY" or locale.currency == "KRW":
            # No decimal places
            formatted = f"{int(amount):,}"
        elif locale.currency == "VND":
            formatted = f"{int(amount):,}"
        else:
            formatted = f"{amount:,.2f}"

        # Replace separators
        if locale.decimal_separator == ",":
            formatted = formatted.replace(",", "TEMP")
            formatted = formatted.replace(".", ",")
            formatted = formatted.replace("TEMP", locale.thousands_separator)
        else:
            formatted = formatted.replace(",", locale.thousands_separator)

        # Position currency symbol
        if locale.currency_position == "before":
            return f"{locale.currency_symbol}{formatted}"
        else:
            return f"{formatted} {locale.currency_symbol}"

    def batch_localize(self, text: str, source_locale: str,
                        target_locales: list[str],
                        category: str = "general") -> dict[str, LocalizationResult]:
        """Localize text for multiple target locales at once.

        Returns:
            Dict of locale_code -> LocalizationResult.
        """
        results = {}
        for target in target_locales:
            results[target] = self.localize(text, source_locale, target, category)
        return results

    def format_batch_report(self, results: dict[str, LocalizationResult]) -> str:
        """Format batch localization results as a report."""
        lines = [
            "🌍 Batch Localization Report",
            f"Locales: {len(results)}",
            "",
            f"{'Locale':<10} {'Country':<20} {'Quality':>8} {'Issues':>7} {'Conversions':>12}",
            "─" * 60,
        ]

        for code, result in sorted(results.items(), key=lambda x: -x[1].quality_score):
            locale = LOCALES.get(code)
            country = locale.country if locale else code
            lines.append(
                f"{code:<10} {country:<20} {result.quality_score:>7.0f}% "
                f"{len(result.issues):>6} {len(result.unit_conversions):>11}"
            )

        avg_quality = sum(r.quality_score for r in results.values()) / len(results) if results else 0
        lines.extend([
            "─" * 60,
            f"{'Average':<31} {avg_quality:>7.0f}%",
        ])

        # Highlight critical issues
        critical = [(code, issue) for code, r in results.items()
                     for issue in r.issues if issue.severity == "error"]
        if critical:
            lines.extend(["", "🚨 Critical Issues:"])
            for code, issue in critical:
                lines.append(f"  [{code}] {issue.message}")

        return "\n".join(lines)


def localize_listing(text: str, source: str = "en-US",
                      target: str = "de-DE",
                      category: str = "general") -> LocalizationResult:
    """Convenience function for quick localization."""
    engine = LocalizationEngine()
    return engine.localize(text, source, target, category)
