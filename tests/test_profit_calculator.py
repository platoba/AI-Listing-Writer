"""Tests for profit_calculator module – existing ProfitCalculator + ProfitBreakdown API."""

import pytest
from app.profit_calculator import (
    ProfitCalculator,
    ProfitBreakdown,
    MultiPlatformComparison,
    Platform,
    Currency,
    PLATFORM_FEES,
    EXCHANGE_RATES,
    IMPORT_DUTIES,
    SHIPPING_RATES,
    quick_profit_check,
)


@pytest.fixture
def calc():
    return ProfitCalculator()


class TestInit:
    def test_default_init(self, calc):
        assert calc.platform_fees == PLATFORM_FEES
        assert calc.exchange_rates == EXCHANGE_RATES

    def test_has_all_platforms(self):
        for p in [Platform.AMAZON_US, Platform.EBAY, Platform.SHOPIFY, Platform.WALMART, Platform.ETSY]:
            assert p in PLATFORM_FEES


class TestCalculateProfit:
    def test_basic_amazon(self, calc):
        bd = calc.calculate_profit(
            selling_price=29.99, cost_of_goods=8.00, platform=Platform.AMAZON_US
        )
        assert bd.selling_price == 29.99
        assert bd.cost_of_goods == 8.00
        assert bd.platform_fees > 0
        assert bd.net_profit > 0
        assert bd.profit_margin_pct > 0

    def test_ebay(self, calc):
        bd = calc.calculate_profit(
            selling_price=29.99, cost_of_goods=8.00, platform=Platform.EBAY
        )
        assert bd.net_profit > 0

    def test_shopify_no_referral(self, calc):
        bd = calc.calculate_profit(
            selling_price=29.99, cost_of_goods=8.00, platform=Platform.SHOPIFY
        )
        # Shopify has 0% referral rate
        assert bd.platform_fees < 5  # Should be much lower than Amazon

    def test_walmart(self, calc):
        bd = calc.calculate_profit(
            selling_price=29.99, cost_of_goods=8.00, platform=Platform.WALMART
        )
        assert bd.net_profit > 0

    def test_etsy_low_commission(self, calc):
        bd = calc.calculate_profit(
            selling_price=29.99, cost_of_goods=8.00, platform=Platform.ETSY
        )
        assert bd.net_profit > 0

    def test_negative_profit(self, calc):
        bd = calc.calculate_profit(
            selling_price=5.00, cost_of_goods=15.00, platform=Platform.AMAZON_US
        )
        assert bd.net_profit < 0
        assert bd.profit_margin_pct < 0

    def test_with_shipping(self, calc):
        bd = calc.calculate_profit(
            selling_price=30.00, cost_of_goods=8.00, shipping_cost=5.00
        )
        assert bd.shipping_cost == 5.00

    def test_with_import_duty(self, calc):
        bd = calc.calculate_profit(
            selling_price=30.00, cost_of_goods=8.00, import_duty_rate=0.10
        )
        assert bd.import_duty == 0.80  # 8.00 * 0.10

    def test_with_other_costs(self, calc):
        bd = calc.calculate_profit(
            selling_price=30.00, cost_of_goods=8.00, other_costs=2.50
        )
        assert bd.other_costs == 2.50

    def test_currency_conversion(self, calc):
        bd = calc.calculate_profit(
            selling_price=25.00, cost_of_goods=5.00,
            currency=Currency.GBP
        )
        # GBP → USD conversion
        assert bd.selling_price > 25.00  # GBP is worth more than USD

    def test_break_even_positive(self, calc):
        bd = calc.calculate_profit(selling_price=50.00, cost_of_goods=10.00)
        assert bd.break_even_units >= 1

    def test_break_even_negative_profit(self, calc):
        bd = calc.calculate_profit(selling_price=5.00, cost_of_goods=20.00)
        assert bd.break_even_units == 9999

    def test_zero_selling_price(self, calc):
        bd = calc.calculate_profit(selling_price=0.0, cost_of_goods=5.00)
        assert bd.profit_margin_pct == 0

    def test_shipping_method_economy(self, calc):
        bd = calc.calculate_profit(
            selling_price=30.00, cost_of_goods=8.00,
            shipping_method="economy", product_weight_kg=1.0
        )
        assert bd.shipping_cost == SHIPPING_RATES["economy"]

    def test_shipping_method_express(self, calc):
        bd = calc.calculate_profit(
            selling_price=30.00, cost_of_goods=8.00,
            shipping_method="express", product_weight_kg=1.0
        )
        assert bd.shipping_cost == SHIPPING_RATES["express"]

    def test_monthly_volume_affects_sub_cost(self, calc):
        bd_low = calc.calculate_profit(
            selling_price=30.00, cost_of_goods=8.00, monthly_sales_volume=10
        )
        bd_high = calc.calculate_profit(
            selling_price=30.00, cost_of_goods=8.00, monthly_sales_volume=1000
        )
        # Higher volume = lower per-unit subscription cost = better profit
        assert bd_high.net_profit > bd_low.net_profit

    def test_tiktok_shop(self, calc):
        bd = calc.calculate_profit(
            selling_price=29.99, cost_of_goods=8.00, platform=Platform.TIKTOK_SHOP
        )
        assert bd.net_profit > 0
        # TikTok has 5% commission — lower than Amazon 15%
        assert bd.platform_fees < 5

    def test_roi_calculation(self, calc):
        bd = calc.calculate_profit(selling_price=50.00, cost_of_goods=10.00)
        assert bd.roi_pct > 0

    def test_gross_profit(self, calc):
        bd = calc.calculate_profit(selling_price=30.00, cost_of_goods=10.00)
        assert bd.gross_profit == 20.00


class TestComparePlatforms:
    def test_basic_comparison(self, calc):
        comp = calc.compare_platforms("Widget", 29.99, 8.00)
        assert comp.product_name == "Widget"
        assert len(comp.platforms) >= 3
        assert comp.best_platform != ""
        assert comp.best_profit > comp.worst_profit

    def test_custom_platforms(self, calc):
        comp = calc.compare_platforms(
            "Gadget", 29.99, 8.00,
            platforms=[Platform.AMAZON_US, Platform.SHOPIFY]
        )
        assert len(comp.platforms) == 2

    def test_best_worst_assigned(self, calc):
        comp = calc.compare_platforms("Test", 25.00, 5.00)
        assert comp.best_platform in [p.value for p in Platform]
        assert comp.worst_platform in [p.value for p in Platform]

    def test_all_have_breakdown(self, calc):
        comp = calc.compare_platforms("Test", 30.00, 10.00)
        for _, bd in comp.platforms.items():
            assert isinstance(bd, ProfitBreakdown)
            assert hasattr(bd, "net_profit")


class TestFormatting:
    def test_format_breakdown(self, calc):
        bd = calc.calculate_profit(selling_price=29.99, cost_of_goods=8.00)
        text = calc.format_breakdown(bd)
        assert "Profit Breakdown" in text
        assert "$29.99" in text
        assert "Net Profit" in text

    def test_format_low_margin_warning(self, calc):
        bd = calc.calculate_profit(selling_price=12.00, cost_of_goods=8.00)
        text = calc.format_breakdown(bd)
        if bd.profit_margin_pct < 15:
            assert "⚠️" in text

    def test_format_healthy_margin(self, calc):
        bd = calc.calculate_profit(selling_price=100.00, cost_of_goods=10.00)
        text = calc.format_breakdown(bd)
        if bd.profit_margin_pct > 40:
            assert "✅" in text

    def test_format_comparison(self, calc):
        comp = calc.compare_platforms("Widget", 29.99, 8.00)
        text = calc.format_comparison(comp)
        assert "Comparison" in text
        assert "Best Platform" in text
        assert "Worst Platform" in text
        assert "⭐" in text


class TestCurrencyConversion:
    def test_usd_to_usd(self, calc):
        result = calc.convert_currency(100.0, Currency.USD, Currency.USD)
        assert result == 100.0

    def test_gbp_to_usd(self, calc):
        result = calc.convert_currency(100.0, Currency.GBP, Currency.USD)
        assert result > 100.0  # GBP > USD

    def test_cny_to_usd(self, calc):
        result = calc.convert_currency(100.0, Currency.CNY, Currency.USD)
        assert result < 100.0  # CNY < USD

    def test_usd_to_eur(self, calc):
        result = calc.convert_currency(100.0, Currency.USD, Currency.EUR)
        assert result > 0


class TestImportDuty:
    def test_us_duty(self, calc):
        duty = calc.calculate_import_duty(100.0, "us")
        assert duty == 5.00  # 5%

    def test_cn_duty(self, calc):
        duty = calc.calculate_import_duty(100.0, "cn")
        assert duty == 10.00  # 10%

    def test_unknown_country_default(self, calc):
        duty = calc.calculate_import_duty(100.0, "xx")
        assert duty == 5.00  # default 5%

    def test_case_insensitive(self, calc):
        duty = calc.calculate_import_duty(100.0, "US")
        assert duty == 5.00


class TestQuickProfitCheck:
    def test_viable_product(self):
        result = quick_profit_check(29.99, 8.00)
        assert "net_profit" in result
        assert "margin_pct" in result
        assert "viable" in result

    def test_non_viable_product(self):
        result = quick_profit_check(10.00, 15.00)
        assert result["viable"] is False

    def test_custom_platform(self):
        result = quick_profit_check(29.99, 8.00, platform="shopify")
        assert result["net_profit"] > 0


class TestEnums:
    def test_platform_values(self):
        assert Platform.AMAZON_US.value == "amazon_us"
        assert Platform.TIKTOK_SHOP.value == "tiktok_shop"

    def test_currency_values(self):
        assert Currency.USD.value == "usd"
        assert Currency.CNY.value == "cny"

    def test_all_platforms_have_fees(self):
        for p in [Platform.AMAZON_US, Platform.EBAY, Platform.SHOPIFY]:
            assert p in PLATFORM_FEES


class TestConstants:
    def test_shipping_rates(self):
        assert SHIPPING_RATES["economy"] < SHIPPING_RATES["standard"]
        assert SHIPPING_RATES["standard"] < SHIPPING_RATES["express"]

    def test_exchange_rates_positive(self):
        for _, rate in EXCHANGE_RATES.items():
            assert rate > 0

    def test_import_duties_valid(self):
        for _, rate in IMPORT_DUTIES.items():
            assert 0 <= rate <= 1.0
