"""Multi-Platform Profit Calculator.

Calculate comprehensive profitability across e-commerce platforms including:
- Platform fees (referral, subscription, payment processing)
- Shipping costs (domestic and international)
- Import duties and customs
- Currency conversion
- ROI and margin analysis
- Break-even analysis

Supports: Amazon, eBay, Shopify, Walmart, Etsy, AliExpress, and more.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Platform(str, Enum):
    AMAZON_US = "amazon_us"
    AMAZON_UK = "amazon_uk"
    AMAZON_DE = "amazon_de"
    EBAY = "ebay"
    SHOPIFY = "shopify"
    WALMART = "walmart"
    ETSY = "etsy"
    ALIEXPRESS = "aliexpress"
    TIKTOK_SHOP = "tiktok_shop"
    TEMU = "temu"


class Currency(str, Enum):
    USD = "usd"
    GBP = "gbp"
    EUR = "eur"
    CNY = "cny"
    JPY = "jpy"
    CAD = "cad"


# Platform fee structures
PLATFORM_FEES = {
    Platform.AMAZON_US: {
        "referral_rate": 0.15,  # 15% for most categories
        "fba_fee_per_unit": 3.50,  # Average FBA fee
        "monthly_subscription": 39.99,  # Professional seller
        "payment_processing": 0.0,  # Included in referral
    },
    Platform.AMAZON_UK: {
        "referral_rate": 0.15,
        "fba_fee_per_unit": 3.00,
        "monthly_subscription": 25.00,
        "payment_processing": 0.0,
    },
    Platform.AMAZON_DE: {
        "referral_rate": 0.15,
        "fba_fee_per_unit": 3.20,
        "monthly_subscription": 39.00,
        "payment_processing": 0.0,
    },
    Platform.EBAY: {
        "referral_rate": 0.129,  # 12.9% final value fee
        "insertion_fee": 0.35,
        "payment_processing": 0.029 + 0.30,  # 2.9% + $0.30
        "monthly_subscription": 0.0,  # Basic store free
    },
    Platform.SHOPIFY: {
        "referral_rate": 0.0,  # No platform commission
        "payment_processing": 0.029 + 0.30,  # Shopify Payments
        "monthly_subscription": 29.00,  # Basic plan
        "transaction_fee": 0.0,  # If using Shopify Payments
    },
    Platform.WALMART: {
        "referral_rate": 0.15,  # 15% for most categories
        "payment_processing": 0.0,
        "monthly_subscription": 0.0,
        "wfs_fee": 3.00,  # Walmart Fulfillment Services avg
    },
    Platform.ETSY: {
        "referral_rate": 0.065,  # 6.5% transaction fee
        "listing_fee": 0.20,
        "payment_processing": 0.03 + 0.25,  # 3% + $0.25
        "monthly_subscription": 0.0,
    },
    Platform.TIKTOK_SHOP: {
        "referral_rate": 0.05,  # 5% commission (promotional rate)
        "payment_processing": 0.029,
        "monthly_subscription": 0.0,
    },
}

# Exchange rates (to USD)
EXCHANGE_RATES = {
    Currency.USD: 1.0,
    Currency.GBP: 1.27,
    Currency.EUR: 1.08,
    Currency.CNY: 0.14,
    Currency.JPY: 0.0067,
    Currency.CAD: 0.74,
}

# Import duty rates by country (average estimates)
IMPORT_DUTIES = {
    "us": 0.05,  # 5% average
    "uk": 0.04,
    "de": 0.04,
    "cn": 0.10,
    "jp": 0.06,
}

# Shipping cost estimates (per kg, international)
SHIPPING_RATES = {
    "economy": 8.00,    # 15-30 days
    "standard": 15.00,  # 7-15 days
    "express": 30.00,   # 3-7 days
}


@dataclass
class ProfitBreakdown:
    """Detailed profit breakdown."""
    selling_price: float
    cost_of_goods: float
    platform_fees: float
    shipping_cost: float
    import_duty: float
    payment_processing: float
    other_costs: float
    total_costs: float
    gross_profit: float
    net_profit: float
    profit_margin_pct: float
    roi_pct: float
    break_even_units: int


@dataclass
class MultiPlatformComparison:
    """Compare profitability across platforms."""
    product_name: str
    platforms: dict[str, ProfitBreakdown] = field(default_factory=dict)
    best_platform: str = ""
    best_profit: float = 0.0
    worst_platform: str = ""
    worst_profit: float = 0.0


class ProfitCalculator:
    """Calculate profitability across platforms."""

    def __init__(self):
        self.platform_fees = PLATFORM_FEES
        self.exchange_rates = EXCHANGE_RATES
        self.import_duties = IMPORT_DUTIES
        self.shipping_rates = SHIPPING_RATES

    def calculate_profit(
        self,
        selling_price: float,
        cost_of_goods: float,
        platform: Platform = Platform.AMAZON_US,
        shipping_cost: float = 0.0,
        import_duty_rate: Optional[float] = None,
        currency: Currency = Currency.USD,
        monthly_sales_volume: int = 100,
        product_weight_kg: float = 0.5,
        shipping_method: str = "standard",
        other_costs: float = 0.0
    ) -> ProfitBreakdown:
        """Calculate comprehensive profit breakdown for a single platform."""
        # Convert price to USD if needed
        if currency != Currency.USD:
            exchange_rate = self.exchange_rates.get(currency, 1.0)
            selling_price_usd = selling_price * exchange_rate
            cogs_usd = cost_of_goods * exchange_rate
        else:
            selling_price_usd = selling_price
            cogs_usd = cost_of_goods

        # Platform fees
        fees = self.platform_fees.get(platform, {})
        referral_fee = selling_price_usd * fees.get("referral_rate", 0.15)

        # FBA/fulfillment fee (if applicable)
        fulfillment_fee = fees.get("fba_fee_per_unit", 0.0)
        if platform == Platform.WALMART and "wfs_fee" in fees:
            fulfillment_fee = fees["wfs_fee"]

        # Monthly subscription (prorated per unit)
        monthly_sub = fees.get("monthly_subscription", 0.0)
        sub_per_unit = monthly_sub / max(monthly_sales_volume, 1)

        # Payment processing
        payment_fee = 0.0
        if "payment_processing" in fees:
            pp = fees["payment_processing"]
            if isinstance(pp, float):
                payment_fee = selling_price_usd * pp
            else:
                # Handle "rate + fixed" structure
                payment_fee = selling_price_usd * 0.029 + 0.30

        # Insertion/listing fees
        insertion_fee = fees.get("insertion_fee", 0.0)

        total_platform_fees = referral_fee + fulfillment_fee + sub_per_unit + insertion_fee

        # Shipping cost (if not provided, estimate)
        if shipping_cost == 0.0:
            shipping_cost = self.shipping_rates.get(shipping_method, 15.0) * product_weight_kg

        # Import duty (if applicable)
        if import_duty_rate is None:
            import_duty_rate = 0.0  # Assume domestic
        import_duty = cogs_usd * import_duty_rate

        # Total costs
        total_costs = (cogs_usd + total_platform_fees + shipping_cost +
                      import_duty + payment_fee + other_costs)

        # Profits
        gross_profit = selling_price_usd - cogs_usd
        net_profit = selling_price_usd - total_costs

        # Margins
        profit_margin = (net_profit / selling_price_usd * 100) if selling_price_usd > 0 else 0
        roi = (net_profit / cogs_usd * 100) if cogs_usd > 0 else 0

        # Break-even
        if net_profit > 0:
            break_even = max(1, int(1 / (profit_margin / 100)))
        else:
            break_even = 9999

        return ProfitBreakdown(
            selling_price=round(selling_price_usd, 2),
            cost_of_goods=round(cogs_usd, 2),
            platform_fees=round(total_platform_fees, 2),
            shipping_cost=round(shipping_cost, 2),
            import_duty=round(import_duty, 2),
            payment_processing=round(payment_fee, 2),
            other_costs=round(other_costs, 2),
            total_costs=round(total_costs, 2),
            gross_profit=round(gross_profit, 2),
            net_profit=round(net_profit, 2),
            profit_margin_pct=round(profit_margin, 2),
            roi_pct=round(roi, 2),
            break_even_units=break_even
        )

    def compare_platforms(
        self,
        product_name: str,
        selling_price: float,
        cost_of_goods: float,
        platforms: Optional[list[Platform]] = None,
        **kwargs
    ) -> MultiPlatformComparison:
        """Compare profitability across multiple platforms."""
        if platforms is None:
            platforms = [Platform.AMAZON_US, Platform.EBAY, Platform.SHOPIFY,
                        Platform.WALMART, Platform.ETSY]

        comparison = MultiPlatformComparison(product_name=product_name)

        for platform in platforms:
            breakdown = self.calculate_profit(
                selling_price=selling_price,
                cost_of_goods=cost_of_goods,
                platform=platform,
                **kwargs
            )
            comparison.platforms[platform.value] = breakdown

        # Find best and worst
        sorted_platforms = sorted(
            comparison.platforms.items(),
            key=lambda x: x[1].net_profit,
            reverse=True
        )

        if sorted_platforms:
            comparison.best_platform = sorted_platforms[0][0]
            comparison.best_profit = sorted_platforms[0][1].net_profit
            comparison.worst_platform = sorted_platforms[-1][0]
            comparison.worst_profit = sorted_platforms[-1][1].net_profit

        return comparison

    def format_breakdown(self, breakdown: ProfitBreakdown) -> str:
        """Format profit breakdown as readable text."""
        lines = [
            "═══ Profit Breakdown ═══",
            f"Selling Price:       ${breakdown.selling_price:.2f}",
            "",
            "Costs:",
            f"  Cost of Goods:     ${breakdown.cost_of_goods:.2f}",
            f"  Platform Fees:     ${breakdown.platform_fees:.2f}",
            f"  Shipping:          ${breakdown.shipping_cost:.2f}",
            f"  Import Duty:       ${breakdown.import_duty:.2f}",
            f"  Payment Processing:${breakdown.payment_processing:.2f}",
            f"  Other Costs:       ${breakdown.other_costs:.2f}",
            "─" * 30,
            f"  Total Costs:       ${breakdown.total_costs:.2f}",
            "",
            f"Gross Profit:        ${breakdown.gross_profit:.2f}",
            f"Net Profit:          ${breakdown.net_profit:.2f}",
            f"Profit Margin:       {breakdown.profit_margin_pct:.1f}%",
            f"ROI:                 {breakdown.roi_pct:.1f}%",
            f"Break-even Units:    {breakdown.break_even_units}",
        ]

        if breakdown.profit_margin_pct < 15:
            lines.append("\n⚠️ Margin below 15% — consider raising price or reducing costs")
        elif breakdown.profit_margin_pct > 40:
            lines.append("\n✅ Healthy margin — good product economics")

        return "\n".join(lines)

    def format_comparison(self, comparison: MultiPlatformComparison) -> str:
        """Format multi-platform comparison."""
        lines = [
            "═══ Multi-Platform Profitability Comparison ═══",
            f"Product: {comparison.product_name}",
            "",
            f"{'Platform':<20} {'Net Profit':>12} {'Margin':>10} {'ROI':>8}",
            "─" * 55,
        ]

        sorted_platforms = sorted(
            comparison.platforms.items(),
            key=lambda x: x[1].net_profit,
            reverse=True
        )

        for platform, breakdown in sorted_platforms:
            marker = " ⭐" if platform == comparison.best_platform else ""
            lines.append(
                f"{platform:<20} ${breakdown.net_profit:>10.2f}  "
                f"{breakdown.profit_margin_pct:>8.1f}% {breakdown.roi_pct:>7.0f}%{marker}"
            )

        lines.extend([
            "─" * 55,
            f"\n🏆 Best Platform: {comparison.best_platform} (${comparison.best_profit:.2f} profit)",
            f"📉 Worst Platform: {comparison.worst_platform} (${comparison.worst_profit:.2f} profit)",
            f"💰 Profit Delta: ${comparison.best_profit - comparison.worst_profit:.2f}",
        ])

        return "\n".join(lines)

    def convert_currency(self, amount: float, from_currency: Currency,
                         to_currency: Currency = Currency.USD) -> float:
        """Convert currency."""
        from_rate = self.exchange_rates.get(from_currency, 1.0)
        to_rate = self.exchange_rates.get(to_currency, 1.0)
        usd_amount = amount * from_rate
        converted = usd_amount / to_rate
        return round(converted, 2)

    def calculate_import_duty(self, product_value: float,
                               destination_country: str) -> float:
        """Calculate estimated import duty."""
        duty_rate = self.import_duties.get(destination_country.lower(), 0.05)
        return round(product_value * duty_rate, 2)


def quick_profit_check(selling_price: float, cost_of_goods: float,
                        platform: str = "amazon_us") -> dict:
    """Quick profit check (convenience function)."""
    calc = ProfitCalculator()
    platform_enum = Platform(platform)
    breakdown = calc.calculate_profit(selling_price, cost_of_goods, platform_enum)
    return {
        "net_profit": breakdown.net_profit,
        "margin_pct": breakdown.profit_margin_pct,
        "roi_pct": breakdown.roi_pct,
        "viable": breakdown.profit_margin_pct >= 15
    }
