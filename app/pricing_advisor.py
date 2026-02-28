"""Pricing Psychology & Strategy Advisor.

Analyze product pricing and recommend strategies based on:
- Psychological pricing tactics (charm pricing, anchor pricing, etc.)
- Platform-specific pricing norms
- Competitive positioning (premium/mid/budget)
- Bundle/tier suggestions
- Currency and market-specific formatting
- Price elasticity hints based on product category

Works entirely offline — no API calls needed for core analysis.
"""
import re
import math
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class PriceStrategy(str, Enum):
    CHARM = "charm"  # $9.99 instead of $10
    PRESTIGE = "prestige"  # Round numbers for luxury ($100, $500)
    ANCHOR = "anchor"  # Show high price first, then actual
    BUNDLE = "bundle"  # Bundle discounts
    TIER = "tier"  # Good/Better/Best
    DECOY = "decoy"  # Add an option to make another look better
    LOSS_LEADER = "loss_leader"  # Below cost to attract customers
    PENETRATION = "penetration"  # Low initial price for market entry
    SKIMMING = "skimming"  # High initial price, lower over time
    FREEMIUM = "freemium"  # Free base + paid upgrades


class PriceTier(str, Enum):
    BUDGET = "budget"
    VALUE = "value"
    MID_RANGE = "mid_range"
    PREMIUM = "premium"
    LUXURY = "luxury"


class MarketPosition(str, Enum):
    UNDERCUT = "undercut"  # Below market average
    COMPETITIVE = "competitive"  # At market average
    PREMIUM_POSITION = "premium"  # Above market average


@dataclass
class CompetitorPrice:
    """A competitor's price data point."""
    name: str
    price: float
    currency: str = "USD"
    url: str = ""
    notes: str = ""


@dataclass
class PriceSuggestion:
    """A specific pricing suggestion with rationale."""
    strategy: PriceStrategy
    suggested_price: float
    original_price: float
    rationale: str
    confidence: float = 0.0  # 0-1
    potential_uplift: str = ""  # e.g. "+12-15% conversions"


@dataclass
class BundleSuggestion:
    """A product bundle pricing suggestion."""
    items: list[str]
    individual_total: float
    bundle_price: float
    savings_percent: float
    rationale: str

    @property
    def savings_amount(self) -> float:
        return self.individual_total - self.bundle_price


@dataclass
class TierSuggestion:
    """Good/Better/Best tier pricing."""
    name: str
    price: float
    features: list[str]
    target: str  # Who this tier is for
    is_recommended: bool = False  # The "most popular" tier


@dataclass
class PricingReport:
    """Complete pricing analysis report."""
    product_name: str
    base_price: float
    currency: str = "USD"
    tier: PriceTier = PriceTier.MID_RANGE
    market_position: MarketPosition = MarketPosition.COMPETITIVE
    suggestions: list[PriceSuggestion] = field(default_factory=list)
    bundles: list[BundleSuggestion] = field(default_factory=list)
    tiers: list[TierSuggestion] = field(default_factory=list)
    competitor_prices: list[CompetitorPrice] = field(default_factory=list)
    market_avg: float = 0.0
    market_min: float = 0.0
    market_max: float = 0.0
    psychological_notes: list[str] = field(default_factory=list)
    platform_notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"💰 Pricing Report: {self.product_name}",
            f"{'─' * 50}",
            f"  Base Price: {self.currency} {self.base_price:.2f}",
            f"  Tier: {self.tier.value} | Position: {self.market_position.value}",
        ]

        if self.market_avg > 0:
            lines.append(f"  Market: avg {self.currency} {self.market_avg:.2f} "
                         f"(range: {self.market_min:.2f} – {self.market_max:.2f})")

        if self.suggestions:
            lines.append("")
            lines.append("  📊 Strategy Suggestions:")
            for s in self.suggestions[:5]:
                delta = s.suggested_price - s.original_price
                lines.append(f"    • {s.strategy.value}: {self.currency} {s.suggested_price:.2f} "
                             f"({delta:+.2f}) — {s.rationale}")
                if s.potential_uplift:
                    lines.append(f"      Expected: {s.potential_uplift}")

        if self.tiers:
            lines.append("")
            lines.append("  🏷️ Tier Pricing:")
            for t in self.tiers:
                star = "⭐" if t.is_recommended else "  "
                lines.append(f"    {star} {t.name}: {self.currency} {t.price:.2f} ({t.target})")

        if self.bundles:
            lines.append("")
            lines.append("  📦 Bundle Suggestions:")
            for b in self.bundles:
                lines.append(f"    • {' + '.join(b.items)}: {self.currency} {b.bundle_price:.2f} "
                             f"(save {b.savings_percent:.0f}%)")

        if self.psychological_notes:
            lines.append("")
            lines.append("  🧠 Psychology Notes:")
            for note in self.psychological_notes:
                lines.append(f"    → {note}")

        return "\n".join(lines)


# ── Pricing Psychology Helpers ───────────────────────────────

def charm_price(price: float) -> float:
    """Convert to charm pricing (.99 or .95 ending).

    $10.00 → $9.99
    $25.50 → $24.99
    $100 → $99.99
    """
    if price <= 0:
        return price
    if price < 1:
        return round(price - 0.01, 2) if price >= 0.02 else price
    # Find the nearest .99 below
    base = math.floor(price)
    if price == base:
        return base - 0.01
    return base + 0.99 if (base + 0.99) < price else base - 0.01


def prestige_price(price: float) -> float:
    """Convert to prestige/round pricing for luxury items.

    $99.99 → $100
    $247 → $250
    $1,234 → $1,250
    """
    if price <= 0:
        return price
    if price < 10:
        return round(price)
    if price < 100:
        return round(price / 5) * 5  # Round to nearest 5
    if price < 1000:
        return round(price / 10) * 10  # Round to nearest 10
    return round(price / 50) * 50  # Round to nearest 50


def anchor_price(price: float, markup_pct: float = 40) -> tuple[float, float]:
    """Generate anchor price (original/strikethrough) and sale price.

    Returns (anchor_price, sale_price).
    """
    anchor = price * (1 + markup_pct / 100)
    # Make anchor look natural
    if anchor < 100:
        anchor = math.ceil(anchor) - 0.01  # e.g. 49.99
    else:
        anchor = round(anchor / 10) * 10  # e.g. 200
    return (anchor, price)


def classify_price_tier(price: float, category_avg: float = 0) -> PriceTier:
    """Classify a price into tiers based on absolute value or category average."""
    if category_avg > 0:
        ratio = price / category_avg
        if ratio < 0.5:
            return PriceTier.BUDGET
        if ratio < 0.8:
            return PriceTier.VALUE
        if ratio < 1.2:
            return PriceTier.MID_RANGE
        if ratio < 2.0:
            return PriceTier.PREMIUM
        return PriceTier.LUXURY

    # Absolute classification (USD-based heuristic)
    if price < 10:
        return PriceTier.BUDGET
    if price < 30:
        return PriceTier.VALUE
    if price < 100:
        return PriceTier.MID_RANGE
    if price < 500:
        return PriceTier.PREMIUM
    return PriceTier.LUXURY


def suggest_tier_pricing(base_price: float, product_name: str = "") -> list[TierSuggestion]:
    """Generate Good/Better/Best tier suggestions."""
    return [
        TierSuggestion(
            name="Basic",
            price=round(base_price * 0.7, 2),
            features=["Core features", "Standard warranty"],
            target="Budget-conscious buyers",
            is_recommended=False,
        ),
        TierSuggestion(
            name="Standard",
            price=base_price,
            features=["All Basic features", "Premium materials", "Extended warranty"],
            target="Most buyers",
            is_recommended=True,
        ),
        TierSuggestion(
            name="Premium",
            price=round(base_price * 1.6, 2),
            features=["All Standard features", "Exclusive additions",
                       "Priority support", "Gift packaging"],
            target="Quality-first buyers",
            is_recommended=False,
        ),
    ]


def suggest_bundles(products: list[tuple[str, float]],
                    discount_pct: float = 15) -> list[BundleSuggestion]:
    """Suggest product bundles from a list of (name, price) tuples."""
    if len(products) < 2:
        return []

    bundles = []

    # Bundle all items
    if len(products) >= 2:
        total = sum(p[1] for p in products)
        bundle_price = round(total * (1 - discount_pct / 100), 2)
        bundles.append(BundleSuggestion(
            items=[p[0] for p in products],
            individual_total=total,
            bundle_price=bundle_price,
            savings_percent=discount_pct,
            rationale=f"Complete set bundle — {discount_pct}% off encourages full purchase",
        ))

    # Pair bundles (first 2 items if more than 2)
    if len(products) >= 3:
        # Most expensive + cheapest pair
        sorted_products = sorted(products, key=lambda x: x[1], reverse=True)
        pair = [sorted_products[0], sorted_products[-1]]
        pair_total = sum(p[1] for p in pair)
        pair_discount = discount_pct * 0.7  # Less discount for pairs
        pair_price = round(pair_total * (1 - pair_discount / 100), 2)
        bundles.append(BundleSuggestion(
            items=[p[0] for p in pair],
            individual_total=pair_total,
            bundle_price=pair_price,
            savings_percent=round(pair_discount, 1),
            rationale="High + low price pair — anchoring effect increases perceived value",
        ))

    return bundles


# ── Platform-Specific Pricing Notes ──────────────────────────

PLATFORM_PRICING_NOTES = {
    "amazon": [
        "Amazon Buy Box favors competitive pricing (within 2% of lowest)",
        "Use Subscribe & Save for recurring products (5-15% discount)",
        "Lightning Deals work well with 20%+ discounts",
        "Keep price ending in .99 for most categories",
        "Avoid frequent price changes — Amazon tracks price history",
    ],
    "shopee": [
        "Shopee buyers are very price-sensitive — flash sales drive traffic",
        "Use Shopee Coins cashback as a virtual discount",
        "Bundle deals (e.g., 'Buy 2 Get 5% Off') increase AOV",
        "Free shipping threshold should be just above your AOV",
        "Round pricing works in SEA markets for local currencies",
    ],
    "aliexpress": [
        "AliExpress buyers expect 30-50% markup from factory price",
        "Use tiered quantity pricing (1pc / 5pc / 10pc)",
        "Cents pricing (.99) works for USD listings",
        "Factor in platform commission (5-8%) when setting price",
        "Flash deals and coupons are essential for visibility",
    ],
    "ebay": [
        "Best Offer listings get 25% more engagement",
        "Free shipping + higher price outperforms low price + paid shipping",
        "Auction starting price should be 50-60% of target",
        "Volume pricing (quantity discounts) improves search ranking",
        "Promoted listings cost 2-5% — factor into margin",
    ],
    "etsy": [
        "Etsy buyers pay premium for handmade — don't underprice",
        "Price in increments of $5 for items over $20",
        "Include material + labor + overhead + 30% profit minimum",
        "Personalization commands 20-40% premium",
        "Free shipping over $35 gets Etsy search boost",
    ],
    "temu": [
        "Temu is ultra-price-competitive — razor-thin margins",
        "Price must be at or below AliExpress equivalent",
        "Focus on volume — low per-unit profit, high quantity",
        "Factory-direct pricing expected by platform buyers",
    ],
    "walmart": [
        "Match or beat Amazon pricing for Buy Box equivalent",
        "Use Rollback pricing for seasonal items",
        "Walmart+ member pricing for customer retention",
        "Keep pricing transparent — hidden fees hurt rankings",
    ],
}


def get_platform_notes(platform: str) -> list[str]:
    """Get platform-specific pricing notes."""
    return PLATFORM_PRICING_NOTES.get(platform.lower(), [
        f"No specific notes for '{platform}' — apply general e-commerce pricing best practices",
    ])


# ── Core Analysis Engine ─────────────────────────────────────

def analyze_pricing(
    price: float,
    product_name: str = "",
    currency: str = "USD",
    platform: str = "amazon",
    competitors: Optional[list[CompetitorPrice]] = None,
    related_products: Optional[list[tuple[str, float]]] = None,
) -> PricingReport:
    """Analyze a product's pricing and generate comprehensive recommendations.

    Args:
        price: The product's current or planned price
        product_name: Product name for context
        currency: Currency code
        platform: Target e-commerce platform
        competitors: Optional list of competitor prices
        related_products: Optional list of (name, price) for bundle suggestions

    Returns:
        PricingReport with strategies, bundles, tiers, and notes
    """
    suggestions = []
    psychological_notes = []

    # Calculate market stats from competitors
    market_avg = 0.0
    market_min = 0.0
    market_max = 0.0
    market_position = MarketPosition.COMPETITIVE

    if competitors:
        comp_prices = [c.price for c in competitors if c.price > 0]
        if comp_prices:
            market_avg = sum(comp_prices) / len(comp_prices)
            market_min = min(comp_prices)
            market_max = max(comp_prices)

            if price < market_avg * 0.85:
                market_position = MarketPosition.UNDERCUT
            elif price > market_avg * 1.15:
                market_position = MarketPosition.PREMIUM_POSITION
            else:
                market_position = MarketPosition.COMPETITIVE

    # Classify tier
    tier = classify_price_tier(price, market_avg)

    # 1. Charm pricing suggestion
    charm = charm_price(price)
    if charm != price:
        suggestions.append(PriceSuggestion(
            strategy=PriceStrategy.CHARM,
            suggested_price=charm,
            original_price=price,
            rationale="Left-digit effect makes price feel significantly lower",
            confidence=0.85,
            potential_uplift="+8-12% conversion rate",
        ))
        psychological_notes.append(
            f"Charm pricing ({currency} {charm:.2f}) exploits left-digit bias — "
            f"buyers perceive ${charm:.2f} as closer to ${math.floor(charm):.0f} than ${price:.2f}"
        )

    # 2. Prestige pricing (for premium/luxury items)
    if tier in (PriceTier.PREMIUM, PriceTier.LUXURY):
        prestige = prestige_price(price)
        if prestige != price:
            suggestions.append(PriceSuggestion(
                strategy=PriceStrategy.PRESTIGE,
                suggested_price=prestige,
                original_price=price,
                rationale="Round numbers signal quality and luxury",
                confidence=0.70,
                potential_uplift="+5-10% perceived value for premium positioning",
            ))
            psychological_notes.append(
                "Premium buyers prefer round numbers — signals confidence and quality"
            )

    # 3. Anchor pricing
    anchor_high, anchor_sale = anchor_price(price)
    suggestions.append(PriceSuggestion(
        strategy=PriceStrategy.ANCHOR,
        suggested_price=price,
        original_price=anchor_high,
        rationale=f"Show 'Was {currency} {anchor_high:.2f}' to anchor higher value perception",
        confidence=0.80,
        potential_uplift="+15-25% perceived savings",
    ))
    psychological_notes.append(
        f"Anchor at {currency} {anchor_high:.2f} makes {currency} {price:.2f} feel like a deal"
    )

    # 4. Penetration pricing (if undercutting market)
    if market_avg > 0 and price >= market_avg * 0.9:
        penetration_price = round(market_avg * 0.75, 2)
        suggestions.append(PriceSuggestion(
            strategy=PriceStrategy.PENETRATION,
            suggested_price=penetration_price,
            original_price=price,
            rationale=f"Launch at 25% below market avg to gain initial reviews/sales velocity",
            confidence=0.60,
            potential_uplift="3-5x initial sales velocity, raise price after 100+ reviews",
        ))

    # 5. Bundle suggestions
    bundles = []
    if related_products:
        bundles = suggest_bundles(related_products)

    # 6. Tier pricing
    tiers = suggest_tier_pricing(price, product_name)

    # Platform-specific notes
    platform_notes = get_platform_notes(platform)

    # Additional psychological notes
    if price > 0:
        # Price ending analysis
        cents = round((price % 1) * 100)
        if cents == 99:
            psychological_notes.append("✅ Already using .99 charm pricing — optimal for most products")
        elif cents == 0:
            if tier in (PriceTier.PREMIUM, PriceTier.LUXURY):
                psychological_notes.append("✅ Round pricing appropriate for premium positioning")
            else:
                psychological_notes.append(
                    "⚠️ Round pricing may signal 'not a deal' for value/mid-range items"
                )
        elif cents == 95:
            psychological_notes.append("💡 .95 ending is slightly less effective than .99 but still works")

        # Number of digits perception
        digits = len(str(int(price)))
        if digits >= 4:
            psychological_notes.append(
                f"💡 {digits}-digit price — consider showing as '{currency} {price/1000:.1f}K' "
                f"in ads for easier processing"
            )

    return PricingReport(
        product_name=product_name or "Unknown Product",
        base_price=price,
        currency=currency,
        tier=tier,
        market_position=market_position,
        suggestions=suggestions,
        bundles=bundles,
        tiers=tiers,
        competitor_prices=competitors or [],
        market_avg=market_avg,
        market_min=market_min,
        market_max=market_max,
        psychological_notes=psychological_notes,
        platform_notes=platform_notes,
    )


def format_price(price: float, currency: str = "USD", locale: str = "en") -> str:
    """Format a price with proper currency symbol and locale conventions."""
    symbols = {
        "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥",
        "KRW": "₩", "THB": "฿", "INR": "₹", "BRL": "R$", "MXN": "$",
        "SGD": "S$", "AUD": "A$", "CAD": "C$", "HKD": "HK$", "TWD": "NT$",
    }
    symbol = symbols.get(currency.upper(), currency + " ")

    if currency.upper() in ("JPY", "KRW"):
        return f"{symbol}{int(price):,}"  # No decimals

    if locale.startswith("de") or locale.startswith("fr"):
        # European format: 1.234,56
        int_part = int(price)
        dec_part = round((price - int_part) * 100)
        formatted = f"{int_part:,}".replace(",", ".") + f",{dec_part:02d}"
        return f"{formatted} {symbol}"

    return f"{symbol}{price:,.2f}"


def quick_price_check(price: float) -> list[str]:
    """Quick psychological analysis of a price point — returns tip strings."""
    tips = []
    if price <= 0:
        return ["⚠️ Invalid price"]

    cents = round((price % 1) * 100)
    integer = int(price)

    # Left-digit effect
    if cents >= 95 and cents <= 99:
        tips.append(f"✅ Charm pricing active (ends in .{cents})")
    elif cents == 0 and price >= 50:
        tips.append("💡 Round price — works for luxury, not ideal for value products")
    elif cents > 0 and cents < 50:
        tips.append(f"⚠️ Odd ending (.{cents:02d}) — consider .99 or .00 instead")

    # Price threshold psychology
    thresholds = [10, 20, 25, 50, 100, 200, 500, 1000]
    for t in thresholds:
        if integer == t:
            tips.append(f"📊 Sitting at ${t} threshold — try ${t-0.01:.2f} to feel sub-${t}")
            break
        if t - 3 <= integer <= t - 1:
            tips.append(f"📊 Close to ${t} barrier — staying under ${t} helps conversion")
            break

    # Free shipping threshold hint
    if 15 <= price <= 40:
        tips.append("💡 Consider pricing at/above $25-35 (common free shipping thresholds)")

    return tips
