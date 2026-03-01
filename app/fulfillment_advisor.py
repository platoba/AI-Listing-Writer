"""Fulfillment Advisor — FBA/FBM cost estimation, shipping strategy, storage fee prediction."""

from __future__ import annotations

import math
import re
import sqlite3
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------------

class FulfillmentMethod(str, Enum):
    FBA = "fba"           # Fulfillment by Amazon
    FBM = "fbm"           # Fulfillment by Merchant
    SFP = "sfp"           # Seller Fulfilled Prime
    DROPSHIP = "dropship"
    THREE_PL = "3pl"      # Third-party logistics


class SizeTier(str, Enum):
    SMALL_STANDARD = "small_standard"       # ≤15oz, ≤15×12×0.75"
    LARGE_STANDARD = "large_standard"       # ≤20lb, ≤18×14×8"
    SMALL_OVERSIZE = "small_oversize"       # ≤70lb, ≤60×30"
    MEDIUM_OVERSIZE = "medium_oversize"     # ≤150lb, ≤108"
    LARGE_OVERSIZE = "large_oversize"       # ≤150lb, ≤108×girth≤165"
    SPECIAL_OVERSIZE = "special_oversize"   # >150lb or >108"


class ShippingSpeed(str, Enum):
    STANDARD = "standard"     # 5-8 days
    EXPEDITED = "expedited"   # 3-5 days
    PRIORITY = "priority"     # 1-2 days
    SAME_DAY = "same_day"


class StorageSeason(str, Enum):
    STANDARD = "standard"     # Jan-Sep
    PEAK = "peak"             # Oct-Dec


class Marketplace(str, Enum):
    US = "us"
    UK = "uk"
    DE = "de"
    JP = "jp"
    CA = "ca"
    AU = "au"
    FR = "fr"
    IT = "it"
    ES = "es"
    MX = "mx"


# FBA fulfillment fee table (US, 2025 rates approximation)
FBA_FEES_US: dict[SizeTier, list[tuple[float, float]]] = {
    # (weight_up_to_oz, fee_usd)
    SizeTier.SMALL_STANDARD: [
        (2, 3.22), (4, 3.40), (6, 3.58), (8, 3.77),
        (10, 3.92), (12, 4.08), (14, 4.24), (16, 4.75),
    ],
    SizeTier.LARGE_STANDARD: [
        (4, 3.86), (8, 4.08), (12, 4.24), (16, 4.75),
        (24, 5.40), (32, 5.69), (48, 6.10), (64, 6.39),
        (80, 6.75), (96, 7.25), (128, 7.97), (160, 8.29),
        (192, 9.08), (224, 9.56), (256, 10.22), (288, 10.89),
        (320, 11.37),
    ],
    SizeTier.SMALL_OVERSIZE: [
        (1120, 9.73),  # base + per-lb over 1lb
    ],
    SizeTier.MEDIUM_OVERSIZE: [
        (2400, 19.05),
    ],
    SizeTier.LARGE_OVERSIZE: [
        (2400, 89.98),
    ],
    SizeTier.SPECIAL_OVERSIZE: [
        (2400, 158.49),
    ],
}

# Monthly storage fees per cubic foot (US)
STORAGE_FEES_US: dict[StorageSeason, float] = {
    StorageSeason.STANDARD: 0.87,   # Jan-Sep per cubic ft
    StorageSeason.PEAK: 2.40,       # Oct-Dec per cubic ft
}

# Long-term storage fee (per cubic ft, monthly for items > 365 days)
LONG_TERM_STORAGE_FEE = 6.90

# FBM shipping cost estimates (per lb, US domestic)
FBM_SHIPPING_RATES: dict[ShippingSpeed, float] = {
    ShippingSpeed.STANDARD: 0.55,
    ShippingSpeed.EXPEDITED: 0.85,
    ShippingSpeed.PRIORITY: 1.30,
    ShippingSpeed.SAME_DAY: 2.50,
}

# 3PL average rates
THREE_PL_RATES = {
    "pick_and_pack": 3.00,       # per order
    "storage_per_pallet": 25.00,  # per pallet/month
    "storage_per_bin": 8.00,     # per bin/month
    "receiving_per_unit": 0.35,
    "return_processing": 4.50,
}

# Marketplace-specific multipliers
MARKETPLACE_MULTIPLIERS: dict[Marketplace, float] = {
    Marketplace.US: 1.0,
    Marketplace.UK: 1.05,
    Marketplace.DE: 1.08,
    Marketplace.JP: 0.95,
    Marketplace.CA: 0.92,
    Marketplace.AU: 1.15,
    Marketplace.FR: 1.08,
    Marketplace.IT: 1.10,
    Marketplace.ES: 1.06,
    Marketplace.MX: 0.80,
}


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ProductDimensions:
    length_inches: float
    width_inches: float
    height_inches: float
    weight_oz: float

    @property
    def weight_lb(self) -> float:
        return self.weight_oz / 16.0

    @property
    def girth(self) -> float:
        dims = sorted([self.length_inches, self.width_inches, self.height_inches])
        return dims[2] + 2 * (dims[0] + dims[1])

    @property
    def cubic_feet(self) -> float:
        return (self.length_inches * self.width_inches * self.height_inches) / 1728.0

    @property
    def dimensional_weight_oz(self) -> float:
        """Dimensional weight: (L×W×H) / 139 in lb, converted to oz."""
        dim_lb = (self.length_inches * self.width_inches * self.height_inches) / 139.0
        return dim_lb * 16

    @property
    def billable_weight_oz(self) -> float:
        return max(self.weight_oz, self.dimensional_weight_oz)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FulfillmentCost:
    method: FulfillmentMethod
    fulfillment_fee: float
    shipping_fee: float
    storage_monthly: float
    total_per_unit: float
    breakdown: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "method": self.method.value,
            "fulfillment_fee": round(self.fulfillment_fee, 2),
            "shipping_fee": round(self.shipping_fee, 2),
            "storage_monthly": round(self.storage_monthly, 2),
            "total_per_unit": round(self.total_per_unit, 2),
            "breakdown": self.breakdown,
            "notes": self.notes,
        }


@dataclass
class ShippingStrategy:
    recommended: FulfillmentMethod
    costs: list[FulfillmentCost]
    savings_vs_worst: float
    recommendation_reason: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class ProfitAnalysis:
    selling_price: float
    cost_of_goods: float
    fulfillment_cost: float
    referral_fee: float
    storage_cost: float
    total_costs: float
    profit: float
    margin_pct: float
    roi_pct: float
    break_even_units: int


# ---------------------------------------------------------------------------
# Size Tier Classifier
# ---------------------------------------------------------------------------

class SizeTierClassifier:
    """Classify product into Amazon size tier."""

    def classify(self, dims: ProductDimensions) -> SizeTier:
        l, w, h = dims.length_inches, dims.width_inches, dims.height_inches
        wt = dims.weight_oz
        longest = max(l, w, h)
        median = sorted([l, w, h])[1]
        shortest = min(l, w, h)

        # Small standard: ≤15oz, ≤15×12×0.75"
        if wt <= 15 and longest <= 15 and median <= 12 and shortest <= 0.75:
            return SizeTier.SMALL_STANDARD

        # Large standard: ≤20lb (320oz), ≤18×14×8"
        if wt <= 320 and longest <= 18 and median <= 14 and shortest <= 8:
            return SizeTier.LARGE_STANDARD

        # Small oversize: ≤70lb (1120oz), longest ≤60, median ≤30
        if wt <= 1120 and longest <= 60 and median <= 30:
            return SizeTier.SMALL_OVERSIZE

        # Medium oversize: ≤150lb (2400oz), longest ≤108
        if wt <= 2400 and longest <= 108:
            return SizeTier.MEDIUM_OVERSIZE

        # Large oversize: ≤150lb, ≤108 + girth ≤ 165
        if wt <= 2400 and longest <= 108 and dims.girth <= 165:
            return SizeTier.LARGE_OVERSIZE

        return SizeTier.SPECIAL_OVERSIZE


# ---------------------------------------------------------------------------
# FBA Calculator
# ---------------------------------------------------------------------------

class FBACalculator:
    """Calculate FBA fulfillment fees."""

    def __init__(self):
        self.classifier = SizeTierClassifier()

    def fulfillment_fee(self, dims: ProductDimensions, marketplace: Marketplace = Marketplace.US) -> float:
        tier = self.classifier.classify(dims)
        weight = dims.billable_weight_oz
        fee_table = FBA_FEES_US.get(tier, [])

        base_fee = 0.0
        for max_wt, fee in fee_table:
            if weight <= max_wt:
                base_fee = fee
                break
        else:
            if fee_table:
                base_fee = fee_table[-1][1]
                # Oversize: add per-lb surcharge
                if tier in (SizeTier.SMALL_OVERSIZE, SizeTier.MEDIUM_OVERSIZE):
                    extra_lb = max(0, dims.weight_lb - 1)
                    base_fee += extra_lb * 0.42
                elif tier in (SizeTier.LARGE_OVERSIZE, SizeTier.SPECIAL_OVERSIZE):
                    extra_lb = max(0, dims.weight_lb - 90)
                    base_fee += extra_lb * 0.83

        multiplier = MARKETPLACE_MULTIPLIERS.get(marketplace, 1.0)
        return round(base_fee * multiplier, 2)

    def storage_fee(
        self, dims: ProductDimensions, season: StorageSeason = StorageSeason.STANDARD,
        units: int = 1, days_in_storage: int = 30,
    ) -> float:
        cubic_ft = dims.cubic_feet * units
        rate = STORAGE_FEES_US[season]
        months = days_in_storage / 30.0
        fee = cubic_ft * rate * months

        # Long-term storage surcharge
        if days_in_storage > 365:
            long_term_months = (days_in_storage - 365) / 30.0
            fee += cubic_ft * LONG_TERM_STORAGE_FEE * long_term_months

        return round(fee, 2)

    def estimate(
        self, dims: ProductDimensions,
        marketplace: Marketplace = Marketplace.US,
        season: StorageSeason = StorageSeason.STANDARD,
        monthly_units: int = 100,
    ) -> FulfillmentCost:
        ff = self.fulfillment_fee(dims, marketplace)
        storage = self.storage_fee(dims, season, units=monthly_units)
        storage_per_unit = storage / max(monthly_units, 1)

        tier = self.classifier.classify(dims)
        notes = [f"Size tier: {tier.value}"]
        if tier in (SizeTier.LARGE_OVERSIZE, SizeTier.SPECIAL_OVERSIZE):
            notes.append("⚠️ Oversize item — consider FBM for lower fees")
        if season == StorageSeason.PEAK:
            notes.append("⚠️ Peak season storage rates (Oct-Dec) — 2.76x standard")

        return FulfillmentCost(
            method=FulfillmentMethod.FBA,
            fulfillment_fee=ff,
            shipping_fee=0.0,  # included in FBA fee
            storage_monthly=storage_per_unit,
            total_per_unit=round(ff + storage_per_unit, 2),
            breakdown={
                "fulfillment": ff,
                "storage_per_unit": round(storage_per_unit, 2),
                "tier": tier.value,
                "marketplace": marketplace.value,
            },
            notes=notes,
        )


# ---------------------------------------------------------------------------
# FBM Calculator
# ---------------------------------------------------------------------------

class FBMCalculator:
    """Calculate FBM (self-fulfillment) costs."""

    def __init__(
        self,
        packaging_cost: float = 0.50,
        labor_cost_per_min: float = 0.30,
        avg_pack_minutes: float = 3.0,
    ):
        self.packaging_cost = packaging_cost
        self.labor_cost_per_min = labor_cost_per_min
        self.avg_pack_minutes = avg_pack_minutes

    def shipping_cost(
        self, dims: ProductDimensions,
        speed: ShippingSpeed = ShippingSpeed.STANDARD,
        zone: int = 5,
    ) -> float:
        rate = FBM_SHIPPING_RATES[speed]
        weight_lb = max(dims.weight_lb, dims.dimensional_weight_oz / 16)
        base = rate * max(weight_lb, 1.0)
        # Zone surcharge (each zone adds ~10%)
        zone_mult = 1.0 + (zone - 1) * 0.10
        return round(base * zone_mult, 2)

    def estimate(
        self, dims: ProductDimensions,
        speed: ShippingSpeed = ShippingSpeed.STANDARD,
        zone: int = 5,
        monthly_units: int = 100,
    ) -> FulfillmentCost:
        ship = self.shipping_cost(dims, speed, zone)
        labor = self.labor_cost_per_min * self.avg_pack_minutes
        pick_pack = self.packaging_cost + labor
        # Storage (assume home/garage, $0.10/cubic ft)
        storage = dims.cubic_feet * 0.10 * monthly_units / max(monthly_units, 1)

        notes = []
        if speed == ShippingSpeed.PRIORITY:
            notes.append("Priority shipping — consider FBA for consistent 2-day delivery")
        if dims.weight_lb > 10:
            notes.append("Heavy item — negotiate carrier bulk rates")

        return FulfillmentCost(
            method=FulfillmentMethod.FBM,
            fulfillment_fee=round(pick_pack, 2),
            shipping_fee=ship,
            storage_monthly=round(storage, 2),
            total_per_unit=round(pick_pack + ship + storage, 2),
            breakdown={
                "packaging": self.packaging_cost,
                "labor": round(labor, 2),
                "shipping": ship,
                "storage_per_unit": round(storage, 2),
                "speed": speed.value,
                "zone": zone,
            },
            notes=notes,
        )


# ---------------------------------------------------------------------------
# 3PL Calculator
# ---------------------------------------------------------------------------

class ThreePLCalculator:
    """Estimate third-party logistics costs."""

    def __init__(self, custom_rates: Optional[dict] = None):
        self.rates = dict(THREE_PL_RATES)
        if custom_rates:
            self.rates.update(custom_rates)

    def estimate(
        self, dims: ProductDimensions,
        monthly_units: int = 100,
        monthly_orders: int = 80,
    ) -> FulfillmentCost:
        pick_pack = self.rates["pick_and_pack"]
        receiving = self.rates["receiving_per_unit"]

        # Storage: pallets for large, bins for small
        if dims.cubic_feet > 1.0:
            units_per_pallet = max(1, int(40 / dims.cubic_feet))
            pallets = math.ceil(monthly_units / units_per_pallet)
            storage_total = pallets * self.rates["storage_per_pallet"]
        else:
            units_per_bin = max(1, int(2 / dims.cubic_feet))
            bins = math.ceil(monthly_units / units_per_bin)
            storage_total = bins * self.rates["storage_per_bin"]

        storage_per_unit = storage_total / max(monthly_units, 1)
        total = pick_pack + receiving + storage_per_unit

        return FulfillmentCost(
            method=FulfillmentMethod.THREE_PL,
            fulfillment_fee=round(pick_pack + receiving, 2),
            shipping_fee=0.0,  # varies by 3PL
            storage_monthly=round(storage_per_unit, 2),
            total_per_unit=round(total, 2),
            breakdown={
                "pick_and_pack": pick_pack,
                "receiving": receiving,
                "storage_per_unit": round(storage_per_unit, 2),
                "storage_total": round(storage_total, 2),
            },
            notes=["Shipping cost varies by 3PL partner and carrier contract"],
        )


# ---------------------------------------------------------------------------
# Profit Calculator
# ---------------------------------------------------------------------------

# Amazon referral fee percentages by category
REFERRAL_FEES: dict[str, float] = {
    "general": 0.15,
    "electronics": 0.08,
    "computers": 0.08,
    "clothing": 0.17,
    "shoes": 0.15,
    "jewelry": 0.20,
    "watches": 0.16,
    "furniture": 0.15,
    "grocery": 0.08,
    "health": 0.08,
    "beauty": 0.08,
    "toys": 0.15,
    "sports": 0.15,
    "automotive": 0.12,
    "books": 0.15,
    "media": 0.15,
    "tools": 0.15,
    "pet": 0.15,
    "baby": 0.08,
    "industrial": 0.12,
}


class ProfitCalculator:
    """Calculate per-unit profitability."""

    def calculate(
        self,
        selling_price: float,
        cost_of_goods: float,
        fulfillment_cost: float,
        category: str = "general",
        storage_cost: float = 0.0,
        extra_fees: float = 0.0,
    ) -> ProfitAnalysis:
        ref_rate = REFERRAL_FEES.get(category.lower(), 0.15)
        referral_fee = selling_price * ref_rate

        total_costs = cost_of_goods + fulfillment_cost + referral_fee + storage_cost + extra_fees
        profit = selling_price - total_costs
        margin = (profit / selling_price * 100) if selling_price > 0 else 0
        roi = (profit / cost_of_goods * 100) if cost_of_goods > 0 else 0

        # Break-even units (fixed costs assumed = $0 for simplicity)
        break_even = math.ceil(1 / max(margin / 100, 0.001)) if margin > 0 else 9999

        return ProfitAnalysis(
            selling_price=round(selling_price, 2),
            cost_of_goods=round(cost_of_goods, 2),
            fulfillment_cost=round(fulfillment_cost, 2),
            referral_fee=round(referral_fee, 2),
            storage_cost=round(storage_cost, 2),
            total_costs=round(total_costs, 2),
            profit=round(profit, 2),
            margin_pct=round(margin, 2),
            roi_pct=round(roi, 2),
            break_even_units=break_even,
        )


# ---------------------------------------------------------------------------
# Fulfillment Store (SQLite)
# ---------------------------------------------------------------------------

class FulfillmentStore:
    """Persist fulfillment analyses."""

    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS fulfillment_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                method TEXT NOT NULL,
                total_cost REAL NOT NULL,
                fulfillment_fee REAL,
                shipping_fee REAL,
                storage_fee REAL,
                details_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_fulfill_product ON fulfillment_analyses(product_id);
        """)
        self._conn.commit()

    def save(self, product_id: str, cost: FulfillmentCost) -> int:
        cur = self._conn.execute("""
            INSERT INTO fulfillment_analyses
            (product_id, method, total_cost, fulfillment_fee, shipping_fee, storage_fee, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id, cost.method.value, cost.total_per_unit,
            cost.fulfillment_fee, cost.shipping_fee, cost.storage_monthly,
            json.dumps(cost.breakdown),
        ))
        self._conn.commit()
        return cur.lastrowid  # type: ignore

    def history(self, product_id: str) -> list[dict]:
        rows = self._conn.execute("""
            SELECT * FROM fulfillment_analyses WHERE product_id = ?
            ORDER BY created_at DESC LIMIT 50
        """, (product_id,)).fetchall()
        return [dict(r) for r in rows]

    def cheapest_method(self, product_id: str) -> Optional[dict]:
        row = self._conn.execute("""
            SELECT method, MIN(total_cost) as min_cost
            FROM fulfillment_analyses
            WHERE product_id = ?
            GROUP BY method
            ORDER BY min_cost ASC
            LIMIT 1
        """, (product_id,)).fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Fulfillment Advisor (Main Class)
# ---------------------------------------------------------------------------

class FulfillmentAdvisor:
    """Main entry point: compare fulfillment methods and recommend strategy."""

    def __init__(self, db_path: str = ":memory:"):
        self.fba = FBACalculator()
        self.fbm = FBMCalculator()
        self.three_pl = ThreePLCalculator()
        self.profit_calc = ProfitCalculator()
        self.store = FulfillmentStore(db_path)

    def compare_methods(
        self,
        dims: ProductDimensions,
        marketplace: Marketplace = Marketplace.US,
        season: StorageSeason = StorageSeason.STANDARD,
        monthly_units: int = 100,
        shipping_speed: ShippingSpeed = ShippingSpeed.STANDARD,
    ) -> ShippingStrategy:
        fba_cost = self.fba.estimate(dims, marketplace, season, monthly_units)
        fbm_cost = self.fbm.estimate(dims, shipping_speed, zone=5, monthly_units=monthly_units)
        tpl_cost = self.three_pl.estimate(dims, monthly_units)

        costs = [fba_cost, fbm_cost, tpl_cost]
        costs_sorted = sorted(costs, key=lambda c: c.total_per_unit)

        best = costs_sorted[0]
        worst = costs_sorted[-1]
        savings = round(worst.total_per_unit - best.total_per_unit, 2)

        # Generate recommendation reason
        reasons = []
        if best.method == FulfillmentMethod.FBA:
            reasons.append("FBA offers Prime badge, better Buy Box chance, and hassle-free logistics")
        elif best.method == FulfillmentMethod.FBM:
            reasons.append("FBM is cheapest — good for slow sellers or oversized items")
        else:
            reasons.append("3PL balances cost and scalability — good for growing brands")

        warnings = []
        tier = self.fba.classifier.classify(dims)
        if tier in (SizeTier.SPECIAL_OVERSIZE, SizeTier.LARGE_OVERSIZE):
            warnings.append("Oversize product: FBA fees are very high")
        if monthly_units < 30:
            warnings.append("Low volume: FBM may be more practical (no IPI score risk)")
        if season == StorageSeason.PEAK:
            warnings.append("Peak season: FBA storage fees 2.76x higher")

        return ShippingStrategy(
            recommended=best.method,
            costs=costs,
            savings_vs_worst=savings,
            recommendation_reason=reasons[0],
            warnings=warnings,
        )

    def profit_analysis(
        self,
        dims: ProductDimensions,
        selling_price: float,
        cost_of_goods: float,
        method: FulfillmentMethod = FulfillmentMethod.FBA,
        category: str = "general",
        marketplace: Marketplace = Marketplace.US,
    ) -> ProfitAnalysis:
        if method == FulfillmentMethod.FBA:
            cost = self.fba.estimate(dims, marketplace)
        elif method == FulfillmentMethod.FBM:
            cost = self.fbm.estimate(dims)
        else:
            cost = self.three_pl.estimate(dims)

        return self.profit_calc.calculate(
            selling_price=selling_price,
            cost_of_goods=cost_of_goods,
            fulfillment_cost=cost.total_per_unit,
            category=category,
            storage_cost=cost.storage_monthly,
        )

    def report(self, strategy: ShippingStrategy) -> str:
        lines = [
            "=" * 50,
            "FULFILLMENT STRATEGY REPORT",
            "=" * 50,
            f"Recommended: {strategy.recommended.value.upper()}",
            f"Reason: {strategy.recommendation_reason}",
            f"Savings vs worst: ${strategy.savings_vs_worst:.2f}/unit",
            "",
            "Cost Comparison:",
        ]
        for c in sorted(strategy.costs, key=lambda x: x.total_per_unit):
            marker = " ⭐" if c.method == strategy.recommended else ""
            lines.append(f"  {c.method.value.upper():>8}: ${c.total_per_unit:.2f}/unit{marker}")
            lines.append(f"           Fulfillment: ${c.fulfillment_fee:.2f}  Shipping: ${c.shipping_fee:.2f}  Storage: ${c.storage_monthly:.2f}")
            for note in c.notes:
                lines.append(f"           {note}")

        if strategy.warnings:
            lines.append("")
            lines.append("Warnings:")
            for w in strategy.warnings:
                lines.append(f"  ⚠️ {w}")

        lines.append("=" * 50)
        return "\n".join(lines)

    def profit_report(self, analysis: ProfitAnalysis) -> str:
        lines = [
            "=" * 50,
            "PROFIT ANALYSIS",
            "=" * 50,
            f"Selling Price:    ${analysis.selling_price:.2f}",
            f"Cost of Goods:   -${analysis.cost_of_goods:.2f}",
            f"Fulfillment:     -${analysis.fulfillment_cost:.2f}",
            f"Referral Fee:    -${analysis.referral_fee:.2f}",
            f"Storage:         -${analysis.storage_cost:.2f}",
            "-" * 30,
            f"Total Costs:     -${analysis.total_costs:.2f}",
            f"Profit:           ${analysis.profit:.2f}",
            f"Margin:           {analysis.margin_pct:.1f}%",
            f"ROI:              {analysis.roi_pct:.1f}%",
            "",
        ]
        if analysis.margin_pct < 15:
            lines.append("⚠️ Low margin — consider raising price or reducing COGS")
        elif analysis.margin_pct > 40:
            lines.append("✅ Healthy margin — good product economics")
        if analysis.roi_pct < 50:
            lines.append("⚠️ Low ROI — capital efficiency is poor")
        lines.append("=" * 50)
        return "\n".join(lines)
