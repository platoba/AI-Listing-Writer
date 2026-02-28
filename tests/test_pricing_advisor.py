"""Tests for pricing_advisor module."""
import pytest
from app.pricing_advisor import (
    charm_price, prestige_price, anchor_price,
    classify_price_tier, suggest_tier_pricing, suggest_bundles,
    analyze_pricing, format_price, quick_price_check,
    get_platform_notes,
    PriceStrategy, PriceTier, MarketPosition,
    CompetitorPrice, PriceSuggestion, BundleSuggestion,
    TierSuggestion, PricingReport,
)


# ── charm_price ──────────────────────────────────────────────

class TestCharmPrice:
    def test_round_number(self):
        assert charm_price(10.00) == 9.99

    def test_already_charm(self):
        # $9.99 → should still return something reasonable
        result = charm_price(9.99)
        assert result < 10.00

    def test_mid_price(self):
        result = charm_price(25.50)
        assert result < 25.50
        assert str(result).endswith("99") or str(result).endswith("9")

    def test_high_price(self):
        result = charm_price(100.00)
        assert result == 99.99

    def test_zero_price(self):
        assert charm_price(0) == 0

    def test_negative_price(self):
        assert charm_price(-5) == -5

    def test_small_price(self):
        result = charm_price(0.50)
        assert result < 0.50


# ── prestige_price ───────────────────────────────────────────

class TestPrestigePrice:
    def test_near_hundred(self):
        assert prestige_price(99.99) == 100

    def test_mid_range(self):
        result = prestige_price(247)
        assert result == 245 or result == 250  # Rounded to nearest 5

    def test_high_price(self):
        result = prestige_price(1234)
        assert result % 50 == 0  # Rounded to nearest 50

    def test_zero(self):
        assert prestige_price(0) == 0

    def test_negative(self):
        assert prestige_price(-10) == -10

    def test_small_price(self):
        result = prestige_price(3.7)
        assert result == round(3.7)

    def test_under_100(self):
        result = prestige_price(47)
        assert result % 5 == 0


# ── anchor_price ─────────────────────────────────────────────

class TestAnchorPrice:
    def test_basic_anchor(self):
        anchor, sale = anchor_price(50)
        assert anchor > sale
        assert sale == 50

    def test_custom_markup(self):
        anchor, sale = anchor_price(100, markup_pct=50)
        assert anchor > 100
        assert sale == 100

    def test_low_price(self):
        anchor, sale = anchor_price(9.99)
        assert anchor > sale

    def test_high_price(self):
        anchor, sale = anchor_price(500)
        assert anchor > sale
        assert anchor % 10 == 0  # Should be rounded

    def test_zero_markup(self):
        anchor, sale = anchor_price(50, markup_pct=0)
        assert anchor >= sale  # May round up slightly


# ── classify_price_tier ──────────────────────────────────────

class TestClassifyPriceTier:
    def test_budget(self):
        assert classify_price_tier(5) == PriceTier.BUDGET

    def test_value(self):
        assert classify_price_tier(20) == PriceTier.VALUE

    def test_mid_range(self):
        assert classify_price_tier(50) == PriceTier.MID_RANGE

    def test_premium(self):
        assert classify_price_tier(200) == PriceTier.PREMIUM

    def test_luxury(self):
        assert classify_price_tier(1000) == PriceTier.LUXURY

    def test_with_category_avg_budget(self):
        # Price is 40% of category average
        assert classify_price_tier(20, category_avg=50) == PriceTier.BUDGET

    def test_with_category_avg_mid(self):
        # Price is at category average
        assert classify_price_tier(50, category_avg=50) == PriceTier.MID_RANGE

    def test_with_category_avg_premium(self):
        # Price is 1.5x category average
        assert classify_price_tier(75, category_avg=50) == PriceTier.PREMIUM

    def test_with_category_avg_luxury(self):
        # Price is 3x category average
        assert classify_price_tier(150, category_avg=50) == PriceTier.LUXURY


# ── suggest_tier_pricing ─────────────────────────────────────

class TestSuggestTierPricing:
    def test_three_tiers(self):
        tiers = suggest_tier_pricing(100)
        assert len(tiers) == 3

    def test_tier_names(self):
        tiers = suggest_tier_pricing(100)
        names = [t.name for t in tiers]
        assert "Basic" in names
        assert "Standard" in names
        assert "Premium" in names

    def test_tier_ordering(self):
        tiers = suggest_tier_pricing(100)
        prices = [t.price for t in tiers]
        assert prices == sorted(prices)

    def test_standard_is_recommended(self):
        tiers = suggest_tier_pricing(100)
        recommended = [t for t in tiers if t.is_recommended]
        assert len(recommended) == 1
        assert recommended[0].name == "Standard"

    def test_standard_is_base_price(self):
        tiers = suggest_tier_pricing(49.99)
        standard = [t for t in tiers if t.name == "Standard"][0]
        assert standard.price == 49.99

    def test_basic_is_cheaper(self):
        tiers = suggest_tier_pricing(100)
        basic = [t for t in tiers if t.name == "Basic"][0]
        assert basic.price < 100

    def test_premium_is_more_expensive(self):
        tiers = suggest_tier_pricing(100)
        premium = [t for t in tiers if t.name == "Premium"][0]
        assert premium.price > 100


# ── suggest_bundles ──────────────────────────────────────────

class TestSuggestBundles:
    def test_two_products(self):
        products = [("Widget A", 20), ("Widget B", 30)]
        bundles = suggest_bundles(products)
        assert len(bundles) >= 1

    def test_three_products(self):
        products = [("A", 10), ("B", 20), ("C", 30)]
        bundles = suggest_bundles(products)
        assert len(bundles) >= 2  # Full bundle + pair bundle

    def test_single_product(self):
        bundles = suggest_bundles([("Solo", 50)])
        assert len(bundles) == 0

    def test_empty_products(self):
        bundles = suggest_bundles([])
        assert len(bundles) == 0

    def test_bundle_savings(self):
        products = [("A", 50), ("B", 50)]
        bundles = suggest_bundles(products, discount_pct=20)
        bundle = bundles[0]
        assert bundle.bundle_price < bundle.individual_total
        assert bundle.savings_percent == 20

    def test_bundle_savings_amount(self):
        products = [("A", 50), ("B", 50)]
        bundles = suggest_bundles(products, discount_pct=10)
        bundle = bundles[0]
        assert bundle.savings_amount == pytest.approx(10.0, abs=0.01)


# ── analyze_pricing ──────────────────────────────────────────

class TestAnalyzePricing:
    def test_basic_analysis(self):
        report = analyze_pricing(29.99, "Test Product")
        assert isinstance(report, PricingReport)
        assert report.base_price == 29.99
        assert len(report.suggestions) > 0

    def test_with_product_name(self):
        report = analyze_pricing(49.99, "Wireless Headphones")
        assert report.product_name == "Wireless Headphones"

    def test_with_competitors(self):
        competitors = [
            CompetitorPrice("Brand A", 35.99),
            CompetitorPrice("Brand B", 45.99),
            CompetitorPrice("Brand C", 39.99),
        ]
        report = analyze_pricing(39.99, "Widget", competitors=competitors)
        assert report.market_avg > 0
        assert report.market_min > 0
        assert report.market_max > 0

    def test_market_position_undercut(self):
        competitors = [
            CompetitorPrice("A", 100),
            CompetitorPrice("B", 120),
        ]
        report = analyze_pricing(50, "Cheap Widget", competitors=competitors)
        assert report.market_position == MarketPosition.UNDERCUT

    def test_market_position_competitive(self):
        competitors = [
            CompetitorPrice("A", 48),
            CompetitorPrice("B", 52),
        ]
        report = analyze_pricing(50, "Widget", competitors=competitors)
        assert report.market_position == MarketPosition.COMPETITIVE

    def test_market_position_premium(self):
        competitors = [
            CompetitorPrice("A", 30),
            CompetitorPrice("B", 35),
        ]
        report = analyze_pricing(60, "Premium Widget", competitors=competitors)
        assert report.market_position == MarketPosition.PREMIUM_POSITION

    def test_charm_suggestion_included(self):
        report = analyze_pricing(50.00, "Widget")
        charm_suggestions = [s for s in report.suggestions
                             if s.strategy == PriceStrategy.CHARM]
        assert len(charm_suggestions) > 0

    def test_anchor_suggestion_included(self):
        report = analyze_pricing(50.00, "Widget")
        anchor_suggestions = [s for s in report.suggestions
                              if s.strategy == PriceStrategy.ANCHOR]
        assert len(anchor_suggestions) > 0

    def test_with_related_products(self):
        related = [("Product A", 20), ("Product B", 30)]
        report = analyze_pricing(25, "Widget", related_products=related)
        assert len(report.bundles) > 0

    def test_tier_suggestions(self):
        report = analyze_pricing(99.99, "Widget")
        assert len(report.tiers) == 3

    def test_platform_notes_amazon(self):
        report = analyze_pricing(29.99, "Widget", platform="amazon")
        assert len(report.platform_notes) > 0

    def test_platform_notes_shopee(self):
        report = analyze_pricing(29.99, "Widget", platform="shopee")
        assert len(report.platform_notes) > 0

    def test_psychological_notes(self):
        report = analyze_pricing(50.00, "Widget")
        assert len(report.psychological_notes) > 0

    def test_currency_usd(self):
        report = analyze_pricing(29.99, "Widget", currency="USD")
        assert report.currency == "USD"

    def test_currency_cny(self):
        report = analyze_pricing(199, "商品", currency="CNY")
        assert report.currency == "CNY"

    def test_default_product_name(self):
        report = analyze_pricing(10)
        assert report.product_name == "Unknown Product"

    def test_penetration_suggestion_when_above_market(self):
        competitors = [
            CompetitorPrice("A", 40),
            CompetitorPrice("B", 50),
        ]
        report = analyze_pricing(45, "Widget", competitors=competitors)
        penetration = [s for s in report.suggestions
                       if s.strategy == PriceStrategy.PENETRATION]
        assert len(penetration) > 0


# ── PricingReport ────────────────────────────────────────────

class TestPricingReport:
    def test_summary_not_empty(self):
        report = analyze_pricing(49.99, "Test Widget", platform="amazon")
        summary = report.summary()
        assert len(summary) > 50
        assert "Pricing Report" in summary

    def test_summary_contains_price(self):
        report = analyze_pricing(49.99, "Widget")
        summary = report.summary()
        assert "49.99" in summary

    def test_summary_with_competitors(self):
        competitors = [CompetitorPrice("A", 40)]
        report = analyze_pricing(50, "W", competitors=competitors)
        summary = report.summary()
        assert "Market" in summary


# ── format_price ─────────────────────────────────────────────

class TestFormatPrice:
    def test_usd(self):
        assert format_price(29.99) == "$29.99"

    def test_eur(self):
        result = format_price(29.99, "EUR")
        assert "€" in result

    def test_gbp(self):
        result = format_price(29.99, "GBP")
        assert "£" in result

    def test_jpy_no_decimals(self):
        result = format_price(2999, "JPY")
        assert "¥" in result
        assert "." not in result

    def test_cny(self):
        result = format_price(199.99, "CNY")
        assert "¥" in result

    def test_large_number(self):
        result = format_price(1234567.89, "USD")
        assert "," in result  # Should have thousands separator

    def test_unknown_currency(self):
        result = format_price(99.99, "XYZ")
        assert "XYZ" in result
        assert "99.99" in result

    def test_european_format(self):
        result = format_price(1234.56, "EUR", locale="de")
        assert "€" in result


# ── quick_price_check ────────────────────────────────────────

class TestQuickPriceCheck:
    def test_charm_pricing(self):
        tips = quick_price_check(9.99)
        assert any("charm" in t.lower() or ".99" in t for t in tips)

    def test_round_pricing(self):
        tips = quick_price_check(50.00)
        assert len(tips) > 0

    def test_threshold_pricing(self):
        tips = quick_price_check(99.00)
        assert any("threshold" in t.lower() or "barrier" in t.lower() for t in tips)

    def test_zero_price(self):
        tips = quick_price_check(0)
        assert any("invalid" in t.lower() for t in tips)

    def test_negative_price(self):
        tips = quick_price_check(-5)
        assert any("invalid" in t.lower() for t in tips)

    def test_odd_cents(self):
        tips = quick_price_check(19.37)
        assert any(".99" in t or "odd" in t.lower() for t in tips)


# ── get_platform_notes ───────────────────────────────────────

class TestGetPlatformNotes:
    def test_amazon(self):
        notes = get_platform_notes("amazon")
        assert len(notes) >= 3

    def test_shopee(self):
        notes = get_platform_notes("shopee")
        assert len(notes) >= 3

    def test_aliexpress(self):
        notes = get_platform_notes("aliexpress")
        assert len(notes) >= 3

    def test_ebay(self):
        notes = get_platform_notes("ebay")
        assert len(notes) >= 3

    def test_etsy(self):
        notes = get_platform_notes("etsy")
        assert len(notes) >= 3

    def test_temu(self):
        notes = get_platform_notes("temu")
        assert len(notes) >= 3

    def test_walmart(self):
        notes = get_platform_notes("walmart")
        assert len(notes) >= 3

    def test_unknown_platform(self):
        notes = get_platform_notes("nonexistent_platform")
        assert len(notes) >= 1  # Should return default note

    def test_case_insensitive(self):
        notes_lower = get_platform_notes("amazon")
        notes_upper = get_platform_notes("Amazon")
        # Platform key lookup should work case-insensitively
        # (the function lowercases input)
        assert len(notes_lower) == len(notes_upper)


# ── Data Classes ─────────────────────────────────────────────

class TestDataClasses:
    def test_competitor_price(self):
        cp = CompetitorPrice("Brand X", 49.99, "USD", "http://example.com")
        assert cp.name == "Brand X"
        assert cp.price == 49.99

    def test_price_suggestion(self):
        ps = PriceSuggestion(
            strategy=PriceStrategy.CHARM,
            suggested_price=9.99,
            original_price=10.00,
            rationale="Test",
            confidence=0.8,
        )
        assert ps.suggested_price < ps.original_price

    def test_bundle_suggestion_savings(self):
        bs = BundleSuggestion(
            items=["A", "B"],
            individual_total=100,
            bundle_price=85,
            savings_percent=15,
            rationale="Test",
        )
        assert bs.savings_amount == 15

    def test_tier_suggestion(self):
        ts = TierSuggestion(
            name="Standard",
            price=49.99,
            features=["Feature A"],
            target="Everyone",
            is_recommended=True,
        )
        assert ts.is_recommended is True
