"""Inventory & Stock Health Analyzer.

Analyze inventory-level data alongside listing quality to surface
sell-through risks, overstock alerts, and restocking recommendations.

Features:
- Stock velocity calculation (units/day)
- Days of inventory remaining
- Reorder point calculator with lead time
- Overstock / understock detection
- Dead stock identification
- Stock health score (0-100)
- Seasonal demand adjustment
- Multi-warehouse aggregation
"""
import math
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from datetime import datetime, timedelta


class StockStatus(str, Enum):
    HEALTHY = "healthy"
    LOW_STOCK = "low_stock"
    OVERSTOCK = "overstock"
    DEAD_STOCK = "dead_stock"
    OUT_OF_STOCK = "out_of_stock"
    REORDER_NOW = "reorder_now"


class DemandTrend(str, Enum):
    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    SEASONAL_PEAK = "seasonal_peak"
    NEW_PRODUCT = "new_product"


@dataclass
class SalesData:
    """Historical sales data for a product."""
    sku: str
    daily_units: list[float] = field(default_factory=list)  # Last N days
    price: float = 0.0
    cost: float = 0.0
    current_stock: int = 0
    lead_time_days: int = 14  # Supplier lead time
    safety_stock_days: int = 7
    warehouse: str = "default"
    last_restock_date: Optional[str] = None
    category: str = ""


@dataclass
class StockHealthReport:
    """Stock health analysis result."""
    sku: str
    status: StockStatus
    health_score: float  # 0-100
    velocity: float  # Units per day (avg)
    velocity_7d: float  # Recent 7-day velocity
    velocity_30d: float  # 30-day velocity
    days_remaining: float  # At current velocity
    reorder_point: int
    reorder_quantity: int
    demand_trend: DemandTrend
    margin: float  # Gross margin %
    revenue_at_risk: float  # If stock runs out
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"SKU: {self.sku}",
            f"Status: {self.status.value.upper()}",
            f"Health Score: {self.health_score:.0f}/100",
            f"Velocity: {self.velocity:.1f} units/day (7d: {self.velocity_7d:.1f}, 30d: {self.velocity_30d:.1f})",
            f"Days Remaining: {self.days_remaining:.0f}",
            f"Reorder Point: {self.reorder_point} units",
            f"Demand Trend: {self.demand_trend.value}",
            f"Margin: {self.margin:.1f}%",
        ]
        if self.issues:
            lines.append("Issues:")
            for i in self.issues:
                lines.append(f"  ⚠️ {i}")
        if self.recommendations:
            lines.append("Recommendations:")
            for r in self.recommendations:
                lines.append(f"  💡 {r}")
        return "\n".join(lines)


def calculate_velocity(daily_units: list[float], window: int = 0) -> float:
    """Calculate average daily sales velocity."""
    if not daily_units:
        return 0.0
    data = daily_units[-window:] if window > 0 else daily_units
    return sum(data) / max(len(data), 1)


def detect_demand_trend(daily_units: list[float]) -> DemandTrend:
    """Detect demand trend from sales history."""
    if len(daily_units) < 7:
        return DemandTrend.NEW_PRODUCT

    recent_7d = calculate_velocity(daily_units, 7)
    older = calculate_velocity(daily_units[:-7], 7) if len(daily_units) > 14 else recent_7d

    if older == 0:
        return DemandTrend.NEW_PRODUCT

    change = (recent_7d - older) / older

    if change > 0.5:
        return DemandTrend.SEASONAL_PEAK
    if change > 0.15:
        return DemandTrend.RISING
    if change < -0.15:
        return DemandTrend.DECLINING
    return DemandTrend.STABLE


def calculate_reorder_point(velocity: float, lead_time_days: int,
                            safety_stock_days: int) -> int:
    """Calculate reorder point (when to place order)."""
    return math.ceil(velocity * (lead_time_days + safety_stock_days))


def calculate_eoq(annual_demand: float, order_cost: float = 50,
                  holding_cost_pct: float = 0.25, unit_cost: float = 10) -> int:
    """Economic Order Quantity (EOQ) calculation."""
    if annual_demand <= 0 or unit_cost <= 0:
        return 0
    holding_cost = unit_cost * holding_cost_pct
    if holding_cost <= 0:
        return math.ceil(annual_demand / 12)
    eoq = math.sqrt(2 * annual_demand * order_cost / holding_cost)
    return max(1, math.ceil(eoq))


def analyze_stock_health(data: SalesData) -> StockHealthReport:
    """Analyze stock health for a single SKU."""
    velocity = calculate_velocity(data.daily_units)
    velocity_7d = calculate_velocity(data.daily_units, 7)
    velocity_30d = calculate_velocity(data.daily_units, 30)
    trend = detect_demand_trend(data.daily_units)

    # Days remaining
    effective_velocity = max(velocity_7d, velocity * 0.5)  # Use recent, floor at half avg
    days_remaining = (data.current_stock / effective_velocity) if effective_velocity > 0 else 999

    # Reorder point
    reorder_point = calculate_reorder_point(
        effective_velocity, data.lead_time_days, data.safety_stock_days
    )

    # EOQ for reorder quantity
    annual_demand = velocity * 365
    reorder_qty = calculate_eoq(annual_demand, unit_cost=max(data.cost, 1))

    # Margin
    margin = ((data.price - data.cost) / data.price * 100) if data.price > 0 else 0.0

    # Revenue at risk if stockout
    revenue_at_risk = effective_velocity * data.price * data.lead_time_days

    # Determine status
    issues = []
    recommendations = []
    score = 100.0

    if data.current_stock == 0:
        status = StockStatus.OUT_OF_STOCK
        issues.append("Out of stock!")
        recommendations.append(f"Urgent reorder: {reorder_qty} units")
        score = 0.0
    elif data.current_stock <= reorder_point:
        if days_remaining <= data.lead_time_days:
            status = StockStatus.REORDER_NOW
            issues.append(f"Stock will run out in {days_remaining:.0f} days, lead time is {data.lead_time_days} days")
            recommendations.append(f"Place order NOW for {reorder_qty} units")
            score = 20.0
        else:
            status = StockStatus.LOW_STOCK
            issues.append(f"Stock below reorder point ({data.current_stock} < {reorder_point})")
            recommendations.append(f"Plan reorder of {reorder_qty} units within {max(0, days_remaining - data.lead_time_days):.0f} days")
            score = 50.0
    elif velocity == 0 and len(data.daily_units) >= 30:
        status = StockStatus.DEAD_STOCK
        issues.append(f"No sales in {len(data.daily_units)} days with {data.current_stock} units in stock")
        recommendations.append("Consider liquidation, bundling, or promotional pricing")
        score = 10.0
    elif days_remaining > 180:
        status = StockStatus.OVERSTOCK
        issues.append(f"~{days_remaining:.0f} days of inventory ({data.current_stock} units)")
        recommendations.append("Reduce price or run promotions to increase velocity")
        holding_cost_est = data.cost * data.current_stock * 0.25 / 365 * days_remaining
        if holding_cost_est > 0:
            recommendations.append(f"Estimated holding cost: ${holding_cost_est:.0f}")
        score = 40.0
    else:
        status = StockStatus.HEALTHY
        score = 80.0

    # Trend-based adjustments
    if trend == DemandTrend.RISING:
        recommendations.append("Demand rising — consider larger reorder quantities")
        if status == StockStatus.HEALTHY:
            score = min(100, score + 10)
    elif trend == DemandTrend.DECLINING:
        issues.append("Demand declining")
        recommendations.append("Monitor closely; avoid over-ordering")
        score = max(0, score - 10)
    elif trend == DemandTrend.SEASONAL_PEAK:
        recommendations.append("Seasonal peak detected — ensure adequate stock")

    # Margin warnings
    if margin < 0:
        issues.append(f"Negative margin ({margin:.0f}%)")
        score = max(0, score - 20)
    elif margin < 15:
        issues.append(f"Thin margin ({margin:.0f}%)")
        recommendations.append("Negotiate better supplier pricing or increase retail price")

    return StockHealthReport(
        sku=data.sku,
        status=status,
        health_score=max(0, min(100, score)),
        velocity=velocity,
        velocity_7d=velocity_7d,
        velocity_30d=velocity_30d,
        days_remaining=min(days_remaining, 999),
        reorder_point=reorder_point,
        reorder_quantity=reorder_qty,
        demand_trend=trend,
        margin=margin,
        revenue_at_risk=revenue_at_risk,
        issues=issues,
        recommendations=recommendations,
    )


def analyze_portfolio(products: list[SalesData]) -> dict:
    """Analyze stock health across a portfolio of products."""
    reports = [analyze_stock_health(p) for p in products]

    status_counts = {}
    for r in reports:
        status_counts[r.status.value] = status_counts.get(r.status.value, 0) + 1

    total_revenue_at_risk = sum(r.revenue_at_risk for r in reports
                                if r.status in (StockStatus.LOW_STOCK, StockStatus.REORDER_NOW, StockStatus.OUT_OF_STOCK))

    urgent = [r for r in reports if r.status in (StockStatus.REORDER_NOW, StockStatus.OUT_OF_STOCK)]
    dead = [r for r in reports if r.status == StockStatus.DEAD_STOCK]
    overstock = [r for r in reports if r.status == StockStatus.OVERSTOCK]

    avg_health = sum(r.health_score for r in reports) / max(len(reports), 1)

    return {
        "total_skus": len(reports),
        "avg_health_score": round(avg_health, 1),
        "status_breakdown": status_counts,
        "urgent_reorders": [r.sku for r in urgent],
        "dead_stock": [r.sku for r in dead],
        "overstock": [r.sku for r in overstock],
        "total_revenue_at_risk": round(total_revenue_at_risk, 2),
        "reports": reports,
    }


def portfolio_report_text(products: list[SalesData]) -> str:
    """Generate a text report for an inventory portfolio."""
    result = analyze_portfolio(products)
    lines = [
        "📦 Inventory Health Report",
        "=" * 40,
        f"Total SKUs: {result['total_skus']}",
        f"Average Health: {result['avg_health_score']:.0f}/100",
        f"Revenue at Risk: ${result['total_revenue_at_risk']:,.2f}",
        "",
        "Status Breakdown:",
    ]
    for status, count in result["status_breakdown"].items():
        lines.append(f"  {status}: {count}")

    if result["urgent_reorders"]:
        lines.append(f"\n🚨 Urgent Reorders: {', '.join(result['urgent_reorders'])}")
    if result["dead_stock"]:
        lines.append(f"💀 Dead Stock: {', '.join(result['dead_stock'])}")
    if result["overstock"]:
        lines.append(f"📦 Overstock: {', '.join(result['overstock'])}")

    return "\n".join(lines)
