"""Tests for Localization Engine."""
import pytest
from app.localization import (
    LocalizationEngine,
    LocaleConfig, LocalizationResult, UnitConversion, LocalizationIssue,
    localize_listing,
    LOCALES, MARKETPLACE_LOCALES,
    convert_unit, fahrenheit_to_celsius, celsius_to_fahrenheit,
)


class TestLocaleData:
    def test_us_locale_exists(self):
        assert "en-US" in LOCALES
        us = LOCALES["en-US"]
        assert us.currency == "USD"
        assert us.measurement == "imperial"

    def test_de_locale_exists(self):
        de = LOCALES.get("de-DE")
        assert de is not None
        assert de.currency == "EUR"
        assert de.measurement == "metric"

    def test_marketplace_mapping(self):
        assert "amazon.com" in MARKETPLACE_LOCALES
        assert MARKETPLACE_LOCALES["amazon.com"] == "en-US"
        assert MARKETPLACE_LOCALES["amazon.de"] == "de-DE"


class TestUnitConversion:
    def test_inches_to_cm(self):
        result = convert_unit(10, "in_to_cm")
        assert abs(result - 25.4) < 0.1

    def test_pounds_to_kg(self):
        result = convert_unit(10, "lb_to_kg")
        assert abs(result - 4.54) < 0.1

    def test_fahrenheit_to_celsius_function(self):
        result = fahrenheit_to_celsius(32)
        assert abs(result - 0) < 0.1
        result = fahrenheit_to_celsius(212)
        assert abs(result - 100) < 0.1

    def test_celsius_to_fahrenheit_function(self):
        result = celsius_to_fahrenheit(0)
        assert abs(result - 32) < 0.1
        result = celsius_to_fahrenheit(100)
        assert abs(result - 212) < 0.1

    def test_invalid_conversion_key(self):
        result = convert_unit(10, "invalid_key")
        assert result == 10  # Should return original


class TestLocalizationEngine:
    def test_get_locale(self):
        engine = LocalizationEngine()
        us = engine.get_locale("en-US")
        assert us is not None
        assert us.country == "United States"

    def test_get_marketplace_locale(self):
        engine = LocalizationEngine()
        locale = engine.get_marketplace_locale("amazon.de")
        assert locale is not None
        assert locale.code == "de-DE"

    def test_unknown_locale(self):
        engine = LocalizationEngine()
        locale = engine.get_locale("xx-XX")
        assert locale is None

    def test_unknown_marketplace(self):
        engine = LocalizationEngine()
        locale = engine.get_marketplace_locale("unknown.com")
        assert locale is None


class TestBasicLocalization:
    def test_imperial_to_metric_conversion(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "Product dimensions: 10 inches x 5 inches. Weight: 2 lbs.",
            source_locale="en-US",
            target_locale="de-DE"
        )
        assert "(cm)" in result.localized_text or "(kg)" in result.localized_text
        assert len(result.unit_conversions) > 0

    def test_metric_to_imperial_conversion(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "Dimensions: 25 cm x 15 cm. Weight: 1 kg.",
            source_locale="de-DE",
            target_locale="en-US"
        )
        assert "(in)" in result.localized_text or "(lb)" in result.localized_text
        assert len(result.unit_conversions) > 0

    def test_same_measurement_system(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "25 cm",
            source_locale="de-DE",
            target_locale="fr-FR"  # Both metric
        )
        # Should not convert units
        assert len(result.unit_conversions) == 0

    def test_temperature_conversion_f_to_c(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "Operating temperature: 72°F",
            source_locale="en-US",
            target_locale="de-DE"
        )
        assert "°C" in result.localized_text
        assert len(result.unit_conversions) > 0

    def test_temperature_conversion_c_to_f(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "Temperature: 20°C",
            source_locale="de-DE",
            target_locale="en-US"
        )
        assert "°F" in result.localized_text


class TestUnitConversionTracking:
    def test_conversion_details_recorded(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "10 inches",
            source_locale="en-US",
            target_locale="de-DE"
        )
        assert len(result.unit_conversions) > 0
        conv = result.unit_conversions[0]
        assert conv.original_value == 10.0
        assert conv.from_unit == "in"
        assert conv.to_unit == "cm"

    def test_multiple_conversions(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "Dimensions: 12 inches x 8 inches. Weight: 5 lbs.",
            source_locale="en-US",
            target_locale="de-DE"
        )
        # Should have conversions for both dimensions and weight
        assert len(result.unit_conversions) >= 3


class TestCulturalRules:
    def test_cultural_rules_for_japan(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "Product description",
            source_locale="en-US",
            target_locale="ja-JP",
            product_category="electronics"
        )
        # Should include cultural rules for Japan
        assert len(result.cultural_rules) > 0
        # Should include voltage rule for electronics
        assert any("voltage" in r.rule.lower() or "100v" in r.rule.lower() 
                   for r in result.cultural_rules)

    def test_cultural_rules_for_germany(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "Description",
            source_locale="en-US",
            target_locale="de-DE"
        )
        assert len(result.cultural_rules) > 0

    def test_required_vs_recommended_rules(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "Text",
            source_locale="en-US",
            target_locale="ja-JP",
            product_category="electronics"
        )
        # Should have both required and recommended rules
        required = [r for r in result.cultural_rules if r.severity == "required"]
        recommended = [r for r in result.cultural_rules if r.severity == "recommended"]
        assert len(required) + len(recommended) > 0


class TestComplianceChecks:
    def test_voltage_mismatch_warning(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "Power: 120V",
            source_locale="en-US",
            target_locale="de-DE",
            product_category="electronics"
        )
        # Should warn about voltage difference
        voltage_issues = [i for i in result.issues if "voltage" in i.message.lower()]
        assert len(voltage_issues) > 0

    def test_no_voltage_info_error(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "Electronic device",
            source_locale="en-US",
            target_locale="de-DE",
            product_category="electronics"
        )
        # Should error on missing voltage for electronics
        errors = [i for i in result.issues if i.severity == "error"]
        assert len(errors) > 0

    def test_currency_symbol_detection(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "Price: $49.99",
            source_locale="en-US",
            target_locale="de-DE"
        )
        # Should note currency symbol mismatch
        currency_issues = [i for i in result.issues if "currency" in i.category.lower()]
        assert len(currency_issues) > 0

    def test_rtl_language_warning(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "English text only",
            source_locale="en-US",
            target_locale="ar-SA"
        )
        # Should warn about RTL formatting
        rtl_issues = [i for i in result.issues if "rtl" in i.message.lower() or "direction" in i.category.lower()]
        assert len(rtl_issues) > 0


class TestQualityScoring:
    def test_perfect_localization_high_score(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "Simple product description",
            source_locale="en-US",
            target_locale="en-GB"
        )
        # US to UK should have minimal issues
        assert result.quality_score >= 80

    def test_problematic_localization_low_score(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "120V electronic device $49.99",
            source_locale="en-US",
            target_locale="de-DE",
            product_category="electronics"
        )
        # Multiple issues should lower score
        assert result.quality_score < 100

    def test_quality_deduction_for_errors(self):
        engine = LocalizationEngine()
        # Create result with known error
        result = engine.localize(
            "Electronic product",
            source_locale="en-US",
            target_locale="de-DE",
            product_category="electronics"
        )
        # Errors should significantly reduce quality
        if any(i.severity == "error" for i in result.issues):
            assert result.quality_score < 90


class TestPriceFormatting:
    def test_us_price_format(self):
        engine = LocalizationEngine()
        formatted = engine.format_price(49.99, "en-US")
        assert "$" in formatted
        assert "49.99" in formatted or "49,99" in formatted

    def test_german_price_format(self):
        engine = LocalizationEngine()
        formatted = engine.format_price(49.99, "de-DE")
        assert "€" in formatted

    def test_japanese_price_no_decimals(self):
        engine = LocalizationEngine()
        formatted = engine.format_price(4999, "ja-JP")
        assert "¥" in formatted
        assert "." not in formatted  # No decimal for JPY

    def test_unknown_locale_fallback(self):
        engine = LocalizationEngine()
        formatted = engine.format_price(49.99, "xx-XX")
        assert "$" in formatted  # Should fall back to USD


class TestBatchLocalization:
    def test_batch_multiple_locales(self):
        engine = LocalizationEngine()
        result = engine.batch_localize(
            "Product: 10 inches, 2 lbs",
            source_locale="en-US",
            target_locales=["de-DE", "fr-FR", "ja-JP"]
        )
        assert len(result) == 3
        assert "de-DE" in result
        assert "fr-FR" in result
        assert "ja-JP" in result

    def test_batch_report_formatting(self):
        engine = LocalizationEngine()
        results = engine.batch_localize(
            "10 inches",
            source_locale="en-US",
            target_locales=["de-DE", "fr-FR"]
        )
        report = engine.format_batch_report(results)
        assert "Batch Localization Report" in report
        assert "de-DE" in report
        assert "fr-FR" in report
        assert "Quality" in report


class TestSummaryReporting:
    def test_summary_includes_conversions(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "10 inches, 5 lbs",
            source_locale="en-US",
            target_locale="de-DE"
        )
        summary = result.summary()
        assert "Localization Report" in summary
        assert "Unit Conversions" in summary

    def test_summary_includes_cultural_rules(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "Product",
            source_locale="en-US",
            target_locale="ja-JP",
            product_category="electronics"
        )
        summary = result.summary()
        if result.cultural_rules:
            assert "Cultural Rules" in summary

    def test_summary_includes_issues(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "120V device",
            source_locale="en-US",
            target_locale="de-DE",
            product_category="electronics"
        )
        summary = result.summary()
        if result.issues:
            assert "Issues" in summary


class TestConvenienceFunction:
    def test_localize_listing_quick(self):
        result = localize_listing(
            "10 inches",
            source="en-US",
            target="de-DE"
        )
        assert isinstance(result, LocalizationResult)
        assert "(cm)" in result.localized_text


class TestEdgeCases:
    def test_empty_text_localization(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "",
            source_locale="en-US",
            target_locale="de-DE"
        )
        assert result.localized_text == ""

    def test_text_without_units(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "Just plain text",
            source_locale="en-US",
            target_locale="de-DE"
        )
        assert result.localized_text == "Just plain text"
        assert len(result.unit_conversions) == 0

    def test_mixed_units(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "10 inches and 5 cm",
            source_locale="en-US",
            target_locale="de-DE"
        )
        # Should handle mixed units
        assert len(result.unit_conversions) > 0

    def test_invalid_locale_codes(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "text",
            source_locale="invalid",
            target_locale="also-invalid"
        )
        # Should have error in issues
        assert len(result.issues) > 0
        assert any("unknown locale" in i.message.lower() for i in result.issues)

    def test_very_large_numbers(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "9999999 inches",
            source_locale="en-US",
            target_locale="de-DE"
        )
        assert len(result.unit_conversions) > 0

    def test_decimal_measurements(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "10.5 inches",
            source_locale="en-US",
            target_locale="de-DE"
        )
        assert len(result.unit_conversions) > 0
        conv = result.unit_conversions[0]
        assert conv.original_value == 10.5

    def test_special_characters_in_text(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "Product™ 10 inches ® Special",
            source_locale="en-US",
            target_locale="de-DE"
        )
        assert "™" in result.localized_text
        assert "®" in result.localized_text

    def test_multiple_same_unit(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "10 inches by 20 inches by 30 inches",
            source_locale="en-US",
            target_locale="de-DE"
        )
        # Should convert all three
        assert len(result.unit_conversions) == 3

    def test_fractional_units(self):
        engine = LocalizationEngine()
        result = engine.localize(
            "1/2 inch",
            source_locale="en-US",
            target_locale="de-DE"
        )
        # May or may not parse fractions, should not crash
        assert result.localized_text != ""

    def test_abbreviation_variations(self):
        engine = LocalizationEngine()
        variations = ["10in", "10 in", "10 inches", '10"']
        for var in variations:
            result = engine.localize(var, "en-US", "de-DE")
            # Should handle different abbreviations
            assert result.localized_text != ""
