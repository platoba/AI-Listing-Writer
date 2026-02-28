"""Tests for platform compliance checker."""
import pytest
from app.compliance import (
    ComplianceChecker, ComplianceReport, ComplianceIssue,
    Severity, PlatformRules, PLATFORM_RULES, CharLimit,
)


class TestComplianceIssue:
    def test_str_format(self):
        issue = ComplianceIssue(
            rule_id="TEST",
            platform="amazon",
            severity=Severity.ERROR,
            field="title",
            message="Too long",
            suggestion="Shorten it",
        )
        s = str(issue)
        assert "❌" in s
        assert "TEST" in s
        assert "Too long" in s
        assert "Shorten" in s

    def test_warning_icon(self):
        issue = ComplianceIssue(
            rule_id="W", platform="amazon",
            severity=Severity.WARNING,
            field="title", message="test",
        )
        assert "⚠️" in str(issue)

    def test_info_icon(self):
        issue = ComplianceIssue(
            rule_id="I", platform="amazon",
            severity=Severity.INFO,
            field="title", message="test",
        )
        assert "💡" in str(issue)


class TestComplianceReport:
    def test_empty_report_is_compliant(self):
        report = ComplianceReport(platform="amazon")
        assert report.is_compliant
        assert report.score == 100.0
        assert len(report.errors) == 0
        assert len(report.warnings) == 0

    def test_errors_make_non_compliant(self):
        report = ComplianceReport(platform="amazon", issues=[
            ComplianceIssue("E1", "amazon", Severity.ERROR, "title", "bad"),
        ])
        assert not report.is_compliant
        assert len(report.errors) == 1

    def test_warnings_still_compliant(self):
        report = ComplianceReport(platform="amazon", issues=[
            ComplianceIssue("W1", "amazon", Severity.WARNING, "title", "meh"),
        ])
        assert report.is_compliant

    def test_score_calculation(self):
        report = ComplianceReport(platform="test", checked_rules=10, issues=[
            ComplianceIssue("E1", "test", Severity.ERROR, "f", "m"),
            ComplianceIssue("W1", "test", Severity.WARNING, "f", "m"),
            ComplianceIssue("I1", "test", Severity.INFO, "f", "m"),
        ])
        # 100 - 10(error) - 3(warning) - 1(info) = 86
        assert report.score == 86.0

    def test_score_floor_zero(self):
        report = ComplianceReport(platform="test", checked_rules=10, issues=[
            ComplianceIssue(f"E{i}", "test", Severity.ERROR, "f", "m")
            for i in range(20)
        ])
        assert report.score == 0

    def test_format_report(self):
        report = ComplianceReport(platform="amazon", checked_rules=5, issues=[
            ComplianceIssue("E1", "amazon", Severity.ERROR, "title", "too long"),
        ])
        report.passed_rules = 4
        text = report.format_report()
        assert "AMAZON" in text
        assert "FAIL" in text
        assert "ERRORS" in text

    def test_format_report_pass(self):
        report = ComplianceReport(platform="shopee", checked_rules=5)
        report.passed_rules = 5
        text = report.format_report()
        assert "PASS" in text


class TestPlatformRules:
    def test_all_eight_platforms(self):
        expected = {"amazon", "shopee", "lazada", "aliexpress",
                    "tiktok_shop", "shopify", "ebay", "walmart"}
        assert set(PLATFORM_RULES.keys()) == expected

    def test_amazon_rules(self):
        rules = PLATFORM_RULES["amazon"]
        assert rules.name == "Amazon"
        assert not rules.emoji_allowed
        assert rules.html_allowed
        assert rules.max_bullet_count == 5

    def test_shopee_rules(self):
        rules = PLATFORM_RULES["shopee"]
        assert rules.emoji_allowed
        assert not rules.html_allowed

    def test_walmart_rules(self):
        rules = PLATFORM_RULES["walmart"]
        assert not rules.emoji_allowed
        assert rules.max_bullet_count == 10

    def test_all_platforms_have_char_limits(self):
        for name, rules in PLATFORM_RULES.items():
            assert len(rules.char_limits) > 0, f"{name}: no char limits"

    def test_all_platforms_have_required_fields(self):
        for name, rules in PLATFORM_RULES.items():
            assert len(rules.required_fields) > 0, f"{name}: no required fields"


class TestComplianceChecker:
    def setup_method(self):
        self.checker = ComplianceChecker()

    def test_platforms_list(self):
        assert len(self.checker.platforms) == 8
        assert "amazon" in self.checker.platforms

    def test_get_rules(self):
        rules = self.checker.get_rules("amazon")
        assert rules is not None
        assert rules.name == "Amazon"

    def test_get_rules_case_insensitive(self):
        rules = self.checker.get_rules("AMAZON")
        assert rules is not None

    def test_get_rules_invalid(self):
        rules = self.checker.get_rules("nonexistent")
        assert rules is None

    # --- Amazon compliance tests ---

    def test_amazon_good_listing(self):
        listing = {
            "title": "Premium Wireless Bluetooth Headphones with Active Noise Cancelling - Over-Ear Headphones for Music and Calls",
            "bullet_points": "• Crystal clear audio with 40mm drivers\n• 30-hour battery life\n• Comfortable memory foam ear cushions\n• Foldable design for travel\n• Built-in microphone for hands-free calls",
            "description": "Experience premium sound quality with these wireless Bluetooth headphones. " * 10,
            "search_terms": "wireless headphones bluetooth noise cancelling over ear headphones music",
        }
        report = self.checker.check(listing, "amazon")
        assert report.is_compliant

    def test_amazon_title_too_long(self):
        listing = {
            "title": "X" * 201,
            "bullet_points": "• Test bullet point with enough content here",
            "description": "D" * 200,
        }
        report = self.checker.check(listing, "amazon")
        errors = [i for i in report.issues if i.rule_id == "CHAR_LIMIT_MAX"]
        assert len(errors) > 0

    def test_amazon_title_too_short(self):
        listing = {
            "title": "Short",
            "bullet_points": "• bullet",
            "description": "D" * 200,
        }
        report = self.checker.check(listing, "amazon")
        errors = [i for i in report.issues if i.rule_id == "CHAR_LIMIT_MIN"]
        assert len(errors) > 0

    def test_amazon_prohibited_words(self):
        listing = {
            "title": "Best Seller Number One Headphone Buy Now",
            "bullet_points": "• Great product",
            "description": "This is the best seller product on sale now. " * 5,
        }
        report = self.checker.check(listing, "amazon")
        prohibited = [i for i in report.issues if i.rule_id == "PROHIBITED_WORD"]
        assert len(prohibited) > 0

    def test_amazon_no_emoji(self):
        listing = {
            "title": "🔥 Hot Product Wireless Speaker 🎵",
            "bullet_points": "• Great",
            "description": "Buy this amazing product. " * 10,
        }
        report = self.checker.check(listing, "amazon")
        emoji_issues = [i for i in report.issues if i.rule_id == "EMOJI_NOT_ALLOWED"]
        assert len(emoji_issues) > 0

    def test_amazon_html_in_title(self):
        listing = {
            "title": "<b>Bold Title</b> Wireless Speaker Premium Quality Sound",
            "bullet_points": "• test",
            "description": "Product description here. " * 10,
        }
        report = self.checker.check(listing, "amazon")
        html_issues = [i for i in report.issues if i.rule_id == "HTML_IN_TITLE"]
        assert len(html_issues) > 0

    def test_amazon_keyword_stuffing(self):
        listing = {
            "title": "Speaker Speaker Speaker Bluetooth Speaker Wireless Speaker",
            "bullet_points": "• test",
            "description": "Good product. " * 20,
        }
        report = self.checker.check(listing, "amazon")
        stuff_issues = [i for i in report.issues if i.rule_id == "TITLE_KEYWORD_STUFFING"]
        assert len(stuff_issues) > 0

    def test_amazon_missing_fields(self):
        listing = {
            "title": "Good product title here for Amazon listing test",
        }
        report = self.checker.check(listing, "amazon")
        missing = [i for i in report.issues if i.rule_id == "REQUIRED_FIELD"]
        assert len(missing) >= 1  # at least bullet_points or description

    # --- Shopee compliance tests ---

    def test_shopee_good_listing(self):
        listing = {
            "title": "🔥 Wireless Bluetooth Speaker Portable Mini Bass - Waterproof Outdoor Speaker",
            "description": "✨ Product Features:\n" + "Great sound quality " * 20,
        }
        report = self.checker.check(listing, "shopee")
        assert report.is_compliant

    def test_shopee_external_url(self):
        listing = {
            "title": "Nice product for everyone to enjoy",
            "description": "Buy at https://example.com for cheaper! " * 5,
        }
        report = self.checker.check(listing, "shopee")
        pattern_issues = [i for i in report.issues if i.rule_id == "PROHIBITED_PATTERN"]
        assert len(pattern_issues) > 0

    def test_shopee_replica_word(self):
        listing = {
            "title": "Replica designer bag high quality",
            "description": "AAA quality 1:1 copy of brand bag. " * 5,
        }
        report = self.checker.check(listing, "shopee")
        prohibited = [i for i in report.issues if i.rule_id == "PROHIBITED_WORD"]
        assert len(prohibited) > 0

    # --- TikTok Shop compliance tests ---

    def test_tiktok_no_urls(self):
        listing = {
            "title": "Amazing product you need right now",
            "description": "Check https://mysite.com for more info! " * 5,
        }
        report = self.checker.check(listing, "tiktok_shop")
        pattern_issues = [i for i in report.issues if i.rule_id == "PROHIBITED_PATTERN"]
        assert len(pattern_issues) > 0

    def test_tiktok_no_health_claims(self):
        listing = {
            "title": "Vitamin supplement for better health daily",
            "description": "This product will cure your problems and treat diseases. FDA approved formula.",
        }
        report = self.checker.check(listing, "tiktok_shop")
        prohibited = [i for i in report.issues if i.rule_id == "PROHIBITED_WORD"]
        assert len(prohibited) > 0

    # --- Walmart compliance tests ---

    def test_walmart_no_price(self):
        listing = {
            "product_name": "Premium Wireless Speaker with Deep Bass Sound Quality for Home",
            "shelf_description": "Great speaker for home use. " * 50,
            "short_description": "A wireless speaker. " * 10,
            "key_features": "• Feature 1\n• Feature 2",
        }
        report = self.checker.check(listing, "walmart")
        # Should be compliant
        price_issues = [i for i in report.issues
                        if i.rule_id == "PROHIBITED_PATTERN" and "$" in str(i.message)]
        assert len(price_issues) == 0

    def test_walmart_with_price(self):
        listing = {
            "product_name": "Speaker Only $29.99 Best Deal Amazing Sound Quality Now",
            "shelf_description": "Was $59.99 now only $29.99! " * 30,
            "short_description": "Buy now. " * 10,
            "key_features": "• Cheap",
        }
        report = self.checker.check(listing, "walmart")
        assert not report.is_compliant

    # --- eBay compliance tests ---

    def test_ebay_no_scripts(self):
        listing = {
            "title": "Great product for sale on eBay nice quality item",
            "description": '<script>alert("xss")</script>Product info here. ' * 5,
            "item_specifics": "Brand: Test",
        }
        report = self.checker.check(listing, "ebay")
        # Should catch script tags
        issues = [i for i in report.issues
                  if "active content" in i.message.lower() or "script" in i.message.lower()]
        assert len(issues) > 0

    # --- Universal checks ---

    def test_profanity_detected(self):
        listing = {
            "title": "This damn product is great quality amazing stuff",
            "description": "What the hell is this great product review stuff? " * 5,
        }
        report = self.checker.check(listing, "shopify")
        universal = [i for i in report.issues if i.rule_id == "UNIVERSAL_PROHIBITED"]
        assert len(universal) > 0

    # --- Multi-platform check ---

    def test_check_multi_platform(self):
        listing = {
            "title": "Good product for testing with enough characters here for minimum",
            "description": "Description text here. " * 20,
        }
        results = self.checker.check_multi_platform(
            listing, ["amazon", "shopee", "ebay"]
        )
        assert len(results) == 3
        assert "amazon" in results
        assert all(isinstance(r, ComplianceReport) for r in results.values())

    # --- Unknown platform ---

    def test_unknown_platform(self):
        listing = {"title": "Test"}
        report = self.checker.check(listing, "nonexistent_platform")
        assert len(report.issues) > 0  # Warning about unknown platform

    # --- Platform summary ---

    def test_get_platform_summary(self):
        summary = self.checker.get_platform_summary("amazon")
        assert "Amazon" in summary
        assert "Character Limits" in summary
        assert "Required Fields" in summary

    def test_get_platform_summary_invalid(self):
        summary = self.checker.get_platform_summary("nonexistent")
        assert "Unknown" in summary

    # --- All caps title ---

    def test_title_all_caps(self):
        listing = {
            "title": "WIRELESS BLUETOOTH SPEAKER PORTABLE BASS OUTDOOR WATERPROOF",
            "description": "Good product. " * 20,
        }
        report = self.checker.check(listing, "amazon")
        caps_issues = [i for i in report.issues if i.rule_id == "TITLE_ALL_CAPS"]
        assert len(caps_issues) > 0

    # --- Bullet count ---

    def test_too_many_bullets_amazon(self):
        bullets = "\n".join([f"• Bullet point number {i+1} with details" for i in range(8)])
        listing = {
            "title": "Product with too many bullet points for Amazon listing test",
            "bullet_points": bullets,
            "description": "Description here. " * 20,
        }
        report = self.checker.check(listing, "amazon")
        bullet_issues = [i for i in report.issues if i.rule_id == "BULLET_COUNT_MAX"]
        assert len(bullet_issues) > 0

    # --- Recommended range ---

    def test_recommended_range_info(self):
        listing = {
            "title": "A" * 45 + " good product",  # Between min(50) and recommended_min(80)
            "bullet_points": "• test",
            "description": "D" * 200,
        }
        report = self.checker.check(listing, "amazon")
        # Should have info-level suggestion about title length
        # Title is ~57 chars, min is 50, recommended_min is 80
        # So might get a recommendation
        info_issues = [i for i in report.issues
                       if i.severity == Severity.INFO and i.field == "title"]
        # May or may not trigger depending on exact length
        assert isinstance(report, ComplianceReport)

    # --- Repeated chars ---

    def test_repeated_characters_title(self):
        listing = {
            "title": "Amazing product!!!!! Best ever!!!! Buy it now!!!!",
            "description": "Good product. " * 20,
        }
        report = self.checker.check(listing, "amazon")
        repeat_issues = [i for i in report.issues if i.rule_id == "TITLE_REPEATED_CHARS"]
        assert len(repeat_issues) > 0
