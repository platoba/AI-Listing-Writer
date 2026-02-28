"""Tests for stock_health inventory analyzer."""
import pytest
from app.stock_health import (
    SalesData, StockStatus, DemandTrend, StockHealthReport,
    calculate_velocity, detect_demand_trend,
    calculate_reorder_point, calculate_eoq,
    analyze_stock_health, analyze_portfolio, portfolio_report_text,
)


# ── Velocity Tests ──

class TestVelocity:
    def test_basic_velocity(self):
        assert calculate_velocity([10, 20, 30]) == 20.0

    def test_windowed_velocity(self):
        data = [1, 1, 1, 10, 10, 10]
        assert calculate_velocity(data, 3) == 10.0

    def test_empty(self):
        assert calculate_velocity([]) == 0.0

    def test_single_day(self):
        assert calculate_velocity([5]) == 5.0


# ── Demand Trend Tests ──

class TestDemandTrend:
    def test_new_product(self):
        assert detect_demand_trend([5, 5, 5]) == DemandTrend.NEW_PRODUCT

    def test_stable(self):
        data = [10] * 30
        assert detect_demand_trend(data) == DemandTrend.STABLE

    def test_rising(self):
        data = [5] * 14 + [10] * 7
        trend = detect_demand_trend(data)
        assert trend in (DemandTrend.RISING, DemandTrend.SEASONAL_PEAK)

    def test_declining(self):
        data = [20] * 14 + [5] * 7
        assert detect_demand_trend(data) == DemandTrend.DECLINING

    def test_seasonal_peak(self):
        data = [5] * 14 + [30] * 7
        assert detect_demand_trend(data) == DemandTrend.SEASONAL_PEAK


# ── Reorder Point Tests ──

class TestReorderPoint:
    def test_basic_calculation(self):
        rp = calculate_reorder_point(10.0, 14, 7)
        assert rp == 210  # 10 * (14 + 7)

    def test_zero_velocity(self):
        assert calculate_reorder_point(0, 14, 7) == 0

    def test_fractional(self):
        rp = calculate_reorder_point(3.5, 10, 5)
        assert rp == 53  # ceil(3.5 * 15)


# ── EOQ Tests ──

class TestEOQ:
    def test_basic_eoq(self):
        eoq = calculate_eoq(1000, order_cost=50, holding_cost_pct=0.25, unit_cost=10)
        assert eoq > 0
        assert eoq < 1000

    def test_zero_demand(self):
        assert calculate_eoq(0) == 0

    def test_high_demand(self):
        eoq = calculate_eoq(100000)
        assert eoq > 0


# ── Stock Health Analysis ──

class TestAnalyzeStockHealth:
    def test_healthy_stock(self):
        data = SalesData(
            sku="SKU001",
            daily_units=[10] * 30,
            price=29.99,
            cost=10.0,
            current_stock=500,
            lead_time_days=14,
        )
        report = analyze_stock_health(data)
        assert report.status == StockStatus.HEALTHY
        assert report.health_score >= 70
        assert report.velocity == 10.0
        assert report.margin > 0

    def test_out_of_stock(self):
        data = SalesData(
            sku="SKU002",
            daily_units=[5] * 30,
            price=19.99,
            cost=8.0,
            current_stock=0,
        )
        report = analyze_stock_health(data)
        assert report.status == StockStatus.OUT_OF_STOCK
        assert report.health_score == 0
        assert any("Out of stock" in i for i in report.issues)

    def test_low_stock_reorder(self):
        data = SalesData(
            sku="SKU003",
            daily_units=[20] * 30,
            price=49.99,
            cost=15.0,
            current_stock=50,  # Only 2.5 days at velocity 20
            lead_time_days=14,
        )
        report = analyze_stock_health(data)
        assert report.status in (StockStatus.LOW_STOCK, StockStatus.REORDER_NOW)

    def test_dead_stock(self):
        data = SalesData(
            sku="SKU004",
            daily_units=[0] * 60,
            price=9.99,
            cost=5.0,
            current_stock=1000,
        )
        report = analyze_stock_health(data)
        assert report.status == StockStatus.DEAD_STOCK
        assert any("liquidation" in r.lower() for r in report.recommendations)

    def test_overstock(self):
        data = SalesData(
            sku="SKU005",
            daily_units=[1] * 30,
            price=9.99,
            cost=3.0,
            current_stock=5000,  # ~5000 days worth
        )
        report = analyze_stock_health(data)
        assert report.status == StockStatus.OVERSTOCK

    def test_negative_margin_warning(self):
        data = SalesData(
            sku="SKU006",
            daily_units=[10] * 30,
            price=5.0,
            cost=8.0,
            current_stock=100,
        )
        report = analyze_stock_health(data)
        assert report.margin < 0
        assert any("margin" in i.lower() for i in report.issues)

    def test_thin_margin_warning(self):
        data = SalesData(
            sku="SKU007",
            daily_units=[10] * 30,
            price=10.0,
            cost=9.0,
            current_stock=300,
        )
        report = analyze_stock_health(data)
        assert any("margin" in i.lower() for i in report.issues)

    def test_summary_output(self):
        data = SalesData(
            sku="TEST",
            daily_units=[5] * 30,
            price=20.0,
            cost=8.0,
            current_stock=200,
        )
        report = analyze_stock_health(data)
        summary = report.summary()
        assert "TEST" in summary
        assert "Health Score" in summary

    def test_rising_demand(self):
        data = SalesData(
            sku="SKU008",
            daily_units=[5] * 14 + [15] * 7,
            price=30.0,
            cost=10.0,
            current_stock=300,
        )
        report = analyze_stock_health(data)
        assert report.demand_trend in (DemandTrend.RISING, DemandTrend.SEASONAL_PEAK)

    def test_revenue_at_risk(self):
        data = SalesData(
            sku="SKU009",
            daily_units=[10] * 30,
            price=50.0,
            cost=20.0,
            current_stock=30,
            lead_time_days=14,
        )
        report = analyze_stock_health(data)
        assert report.revenue_at_risk > 0


# ── Portfolio Analysis ──

class TestPortfolioAnalysis:
    @pytest.fixture
    def portfolio(self):
        return [
            SalesData(sku="A", daily_units=[10]*30, price=20, cost=8, current_stock=300),
            SalesData(sku="B", daily_units=[0]*30, price=15, cost=5, current_stock=500),
            SalesData(sku="C", daily_units=[20]*30, price=30, cost=10, current_stock=0),
        ]

    def test_portfolio_summary(self, portfolio):
        result = analyze_portfolio(portfolio)
        assert result["total_skus"] == 3
        assert "C" in result["urgent_reorders"]
        assert "B" in result["dead_stock"]
        assert result["avg_health_score"] >= 0

    def test_portfolio_report(self, portfolio):
        report = portfolio_report_text(portfolio)
        assert "Inventory Health Report" in report
        assert "Total SKUs: 3" in report

    def test_empty_portfolio(self):
        result = analyze_portfolio([])
        assert result["total_skus"] == 0

    def test_all_healthy(self):
        products = [
            SalesData(sku=f"H{i}", daily_units=[10]*30, price=25, cost=8, current_stock=300)
            for i in range(5)
        ]
        result = analyze_portfolio(products)
        assert result["avg_health_score"] >= 70
        assert len(result["urgent_reorders"]) == 0
