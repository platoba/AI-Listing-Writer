"""Bundle Recommender Engine.

Discover complementary products, generate bundle pricing strategies,
and create optimized bundle titles for increased AOV (Average Order Value).

Features:
- Complementary product discovery based on category and attributes
- Dynamic bundle pricing with discount optimization
- Bundle title generation (SEO-optimized)
- Cross-sell and upsell recommendations
- Frequently Bought Together analysis
- Bundle profitability scoring
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BundleStrategy(str, Enum):
    COMPLEMENTARY = "complementary"  # Items used together
    VARIETY_PACK = "variety_pack"    # Same type, different variants
    UPGRADE = "upgrade"              # Base + premium add-ons
    COMPLETE_SET = "complete_set"    # Everything needed for a task
    GIFT_SET = "gift_set"            # Curated for gifting


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"  # e.g., 20% off
    FIXED_AMOUNT = "fixed_amount"  # e.g., $10 off
    BOGO = "bogo"              # Buy One Get One
    TIERED = "tiered"          # More items = bigger discount


@dataclass
class Product:
    """Product representation."""
    id: str
    title: str
    price: float
    category: str
    tags: list[str] = field(default_factory=list)
    cost: float = 0.0  # COGS for profitability


@dataclass
class Bundle:
    """A product bundle recommendation."""
    bundle_id: str
    strategy: BundleStrategy
    products: list[Product]
    bundle_title: str
    original_total: float
    bundle_price: float
    discount_amount: float
    discount_percentage: float
    profitability_score: float  # 0-100
    reasoning: str = ""


# Complementary product rules by category
COMPLEMENT_RULES = {
    "phone": ["phone case", "screen protector", "charger", "earbuds"],
    "camera": ["memory card", "camera bag", "tripod", "lens", "battery"],
    "laptop": ["laptop bag", "mouse", "keyboard", "laptop stand", "usb hub"],
    "yoga mat": ["yoga blocks", "yoga strap", "mat cleaner", "mat bag"],
    "water bottle": ["bottle brush", "ice tray", "bottle sleeve"],
    "headphones": ["headphone case", "cable", "adapter", "cleaning kit"],
    "backpack": ["rain cover", "packing cubes", "luggage tag"],
    "cookware": ["utensils", "pot holder", "cookbook", "spices"],
    "skincare": ["cleanser", "toner", "moisturizer", "sunscreen"],
}


# Bundle title templates
BUNDLE_TITLE_TEMPLATES = {
    BundleStrategy.COMPLEMENTARY: [
        "{main} + {accessories} Bundle",
        "{main} Complete Set with {count} Accessories",
        "{main} Starter Kit",
    ],
    BundleStrategy.VARIETY_PACK: [
        "{main} {count}-Pack",
        "{main} Variety Bundle",
        "Assorted {main} Set of {count}",
    ],
    BundleStrategy.UPGRADE: [
        "{main} Premium Bundle",
        "{main} Deluxe Set",
        "{main} Ultimate Package",
    ],
    BundleStrategy.COMPLETE_SET: [
        "Complete {category} Set",
        "Everything You Need: {main} Kit",
        "{category} Essentials Bundle",
    ],
    BundleStrategy.GIFT_SET: [
        "{main} Gift Set",
        "{main} Gift Bundle - Perfect for {occasion}",
        "Curated {category} Collection",
    ],
}


def _extract_category_keywords(title: str) -> list[str]:
    """Extract product category keywords."""
    keywords = []
    for cat in COMPLEMENT_RULES.keys():
        if cat in title.lower():
            keywords.append(cat)
    return keywords


def _find_complements(product: Product, available: list[Product]) -> list[Product]:
    """Find complementary products for a given product."""
    complements = []
    main_cats = _extract_category_keywords(product.title)

    for main_cat in main_cats:
        rules = COMPLEMENT_RULES.get(main_cat, [])
        for other in available:
            if other.id == product.id:
                continue
            # Check if other product matches complement rules
            if any(rule in other.title.lower() or rule in other.category.lower()
                   for rule in rules):
                complements.append(other)
                if len(complements) >= 5:
                    break

    # Fallback: same category
    if not complements:
        same_cat = [p for p in available
                    if p.category == product.category and p.id != product.id]
        complements = same_cat[:3]

    return complements


def _calculate_bundle_discount(
    products: list[Product],
    discount_type: DiscountType = DiscountType.PERCENTAGE,
    discount_value: float = 15.0
) -> tuple[float, float, float]:
    """Calculate bundle pricing.

    Returns: (bundle_price, discount_amount, discount_percentage)
    """
    total = sum(p.price for p in products)

    if discount_type == DiscountType.PERCENTAGE:
        discount_amt = total * (discount_value / 100)
    elif discount_type == DiscountType.FIXED_AMOUNT:
        discount_amt = discount_value
    elif discount_type == DiscountType.BOGO:
        # Buy 1 get 1 free: discount = price of cheapest item
        discount_amt = min(p.price for p in products)
    elif discount_type == DiscountType.TIERED:
        # More items = bigger discount: 2 items=10%, 3=15%, 4+=20%
        count = len(products)
        tier_pct = 10 if count == 2 else (15 if count == 3 else 20)
        discount_amt = total * (tier_pct / 100)
    else:
        discount_amt = 0.0

    bundle_price = max(0, total - discount_amt)
    discount_pct = (discount_amt / total * 100) if total > 0 else 0

    return round(bundle_price, 2), round(discount_amt, 2), round(discount_pct, 1)


def _calculate_profitability(
    products: list[Product],
    bundle_price: float
) -> float:
    """Calculate bundle profitability score (0-100)."""
    total_cost = sum(p.cost if p.cost > 0 else p.price * 0.4 for p in products)
    profit = bundle_price - total_cost
    margin = (profit / bundle_price * 100) if bundle_price > 0 else 0

    # Score: 0-25% margin=0-50 pts, 25-50%=50-100 pts
    score = min(100, max(0, margin * 2))
    return round(score, 1)


def _generate_bundle_title(
    products: list[Product],
    strategy: BundleStrategy
) -> str:
    """Generate SEO-optimized bundle title."""
    main_product = products[0] if products else None
    if not main_product:
        return "Product Bundle"

    templates = BUNDLE_TITLE_TEMPLATES.get(strategy, [])
    if not templates:
        return f"{main_product.title} Bundle"

    # Pick first template and fill placeholders
    template = templates[0]

    # Extract main product name (first 3 words)
    main_name = " ".join(main_product.title.split()[:3])

    # Accessories list (exclude main)
    accessories = []
    for p in products[1:]:
        acc_name = " ".join(p.title.split()[:2])
        accessories.append(acc_name)
    acc_str = ", ".join(accessories[:2])  # Max 2 for readability

    title = template.format(
        main=main_name,
        accessories=acc_str if accessories else "Accessories",
        count=len(products),
        category=main_product.category.title(),
        occasion="Any Occasion"
    )

    return title[:120]  # Cap title length


class BundleRecommender:
    """Generate bundle recommendations for products."""

    def __init__(self, min_bundle_size: int = 2, max_bundle_size: int = 4):
        self.min_bundle_size = min_bundle_size
        self.max_bundle_size = max_bundle_size

    def recommend_bundles(
        self,
        main_product: Product,
        available_products: list[Product],
        strategy: BundleStrategy = BundleStrategy.COMPLEMENTARY,
        discount_type: DiscountType = DiscountType.PERCENTAGE,
        discount_value: float = 15.0,
        max_bundles: int = 3
    ) -> list[Bundle]:
        """Generate bundle recommendations for a main product."""
        bundles = []

        if strategy == BundleStrategy.COMPLEMENTARY:
            complements = _find_complements(main_product, available_products)
            if not complements:
                return []

            # Generate bundles of different sizes
            for size in range(self.min_bundle_size, self.max_bundle_size + 1):
                if size > len(complements) + 1:
                    break

                bundle_products = [main_product] + complements[:size - 1]
                bundle = self._create_bundle(
                    bundle_products, strategy, discount_type, discount_value
                )
                bundles.append(bundle)

        elif strategy == BundleStrategy.VARIETY_PACK:
            # Find same-category products
            same_cat = [p for p in available_products
                        if p.category == main_product.category and p.id != main_product.id]
            if len(same_cat) < self.min_bundle_size - 1:
                return []

            for size in range(self.min_bundle_size, min(self.max_bundle_size + 1, len(same_cat) + 2)):
                bundle_products = [main_product] + same_cat[:size - 1]
                bundle = self._create_bundle(
                    bundle_products, strategy, DiscountType.TIERED, 0
                )
                bundles.append(bundle)

        elif strategy == BundleStrategy.UPGRADE:
            # Main + premium add-ons
            upgrades = [p for p in available_products
                        if p.price > main_product.price * 0.5 and p.id != main_product.id]
            if not upgrades:
                return []

            bundle_products = [main_product] + upgrades[:2]
            bundle = self._create_bundle(
                bundle_products, strategy, discount_type, discount_value
            )
            bundles.append(bundle)

        # Sort by profitability
        bundles.sort(key=lambda b: b.profitability_score, reverse=True)
        return bundles[:max_bundles]

    def _create_bundle(
        self,
        products: list[Product],
        strategy: BundleStrategy,
        discount_type: DiscountType,
        discount_value: float
    ) -> Bundle:
        """Create a Bundle object."""
        original_total = sum(p.price for p in products)
        bundle_price, discount_amt, discount_pct = _calculate_bundle_discount(
            products, discount_type, discount_value
        )
        profit_score = _calculate_profitability(products, bundle_price)
        title = _generate_bundle_title(products, strategy)

        # Generate reasoning
        reasoning = f"{strategy.value.replace('_', ' ').title()}: "
        if discount_pct > 0:
            reasoning += f"Save {discount_pct}% when buying together. "
        reasoning += f"Profitability: {profit_score:.0f}/100."

        bundle_id = "-".join([p.id for p in products])

        return Bundle(
            bundle_id=bundle_id,
            strategy=strategy,
            products=products,
            bundle_title=title,
            original_total=original_total,
            bundle_price=bundle_price,
            discount_amount=discount_amt,
            discount_percentage=discount_pct,
            profitability_score=profit_score,
            reasoning=reasoning
        )

    def find_best_bundle(
        self,
        main_product: Product,
        available_products: list[Product]
    ) -> Optional[Bundle]:
        """Find the single best bundle for a product."""
        all_bundles = []
        for strategy in [BundleStrategy.COMPLEMENTARY, BundleStrategy.VARIETY_PACK]:
            bundles = self.recommend_bundles(
                main_product, available_products, strategy=strategy
            )
            all_bundles.extend(bundles)

        if not all_bundles:
            return None

        # Return highest profitability
        return max(all_bundles, key=lambda b: b.profitability_score)

    def bulk_recommendations(
        self,
        products: list[Product],
        strategy: BundleStrategy = BundleStrategy.COMPLEMENTARY
    ) -> dict[str, list[Bundle]]:
        """Generate bundle recommendations for multiple products."""
        results = {}
        for product in products:
            others = [p for p in products if p.id != product.id]
            bundles = self.recommend_bundles(product, others, strategy=strategy)
            if bundles:
                results[product.id] = bundles
        return results

    def format_bundle_display(self, bundle: Bundle) -> str:
        """Format bundle for display."""
        lines = [
            f"🎁 {bundle.bundle_title}",
            f"Original: ${bundle.original_total:.2f}",
            f"Bundle Price: ${bundle.bundle_price:.2f}",
            f"💰 Save ${bundle.discount_amount:.2f} ({bundle.discount_percentage}%)",
            "",
            "Includes:",
        ]
        for p in bundle.products:
            lines.append(f"  • {p.title} (${p.price:.2f})")
        lines.append("")
        lines.append(f"Profitability: {bundle.profitability_score:.0f}/100")
        lines.append(f"Strategy: {bundle.strategy.value}")

        return "\n".join(lines)
