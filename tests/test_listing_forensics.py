"""Tests for Listing Forensics."""
import pytest
from app.listing_forensics import (
    ListingForensics,
    ForensicIssue, ForensicReport, ListingData,
    TitleDiagnostic, DescriptionDiagnostic, ImageDiagnostic,
    PricingDiagnostic, KeywordDiagnostic, ReviewDiagnostic,
    ConversionDiagnostic,
    Severity, IssueCategory,
    _grade,
)


class TestGrading:
    def test_a_plus_grade(self):
        assert _grade(95) == "A+"
        assert _grade(90) == "A+"

    def test_a_grade(self):
        assert _grade(85) == "A"
        assert _grade(80) == "A"

    def test_b_grade(self):
        assert _grade(75) == "B+"
        assert _grade(65) == "B"

    def test_c_grade(self):
        assert _grade(55) == "C"

    def test_d_grade(self):
        assert _grade(45) == "D"

    def test_f_grade(self):
        assert _grade(30) == "F"
        assert _grade(0) == "F"


class TestTitleDiagnostic:
    def test_title_too_short(self):
        diag = TitleDiagnostic()
        data = ListingData(title="Short", platform="amazon")
        issues = diag.check(data)
        assert len(issues) > 0
        assert any(i.severity == Severity.CRITICAL for i in issues)
        assert any("too short" in i.title.lower() for i in issues)

    def test_title_too_long(self):
        diag = TitleDiagnostic()
        data = ListingData(title="A" * 250, platform="amazon")
        issues = diag.check(data)
        assert any("exceeds maximum" in i.title.lower() for i in issues)

    def test_keyword_stuffing(self):
        diag = TitleDiagnostic()
        data = ListingData(title="Premium Premium Premium Widget Widget Widget")
        issues = diag.check(data)
        assert any("stuffing" in i.title.lower() or "repeated" in i.title.lower() for i in issues)

    def test_all_caps_title(self):
        diag = TitleDiagnostic()
        data = ListingData(title="ALL CAPS PRODUCT TITLE HERE")
        issues = diag.check(data)
        assert any("caps" in i.title.lower() for i in issues)

    def test_missing_primary_keyword(self):
        diag = TitleDiagnostic()
        data = ListingData(
            title="Generic Product Title",
            keywords=["bluetooth", "wireless"]
        )
        issues = diag.check(data)
        assert any("keyword" in i.title.lower() and "missing" in i.description.lower() for i in issues)

    def test_good_title(self):
        diag = TitleDiagnostic()
        data = ListingData(
            title="Premium Wireless Bluetooth Headphones with Noise Cancelling",
            platform="amazon",
            keywords=["wireless", "bluetooth"]
        )
        issues = diag.check(data)
        # Good title may still have minor suggestions
        critical = [i for i in issues if i.severity == Severity.CRITICAL]
        assert len(critical) == 0


class TestDescriptionDiagnostic:
    def test_no_description(self):
        diag = DescriptionDiagnostic()
        data = ListingData(title="Product", description="", bullet_points=[])
        issues = diag.check(data)
        assert len(issues) > 0
        assert any(i.severity == Severity.CRITICAL for i in issues)

    def test_description_too_thin(self):
        diag = DescriptionDiagnostic()
        data = ListingData(description="Short description here")
        issues = diag.check(data)
        assert any("thin" in i.title.lower() or "short" in i.description.lower() for i in issues)

    def test_no_bullet_points_amazon(self):
        diag = DescriptionDiagnostic()
        data = ListingData(
            description="Long description " * 50,
            bullet_points=[],
            platform="amazon"
        )
        issues = diag.check(data)
        assert any("bullet" in i.title.lower() for i in issues)

    def test_too_few_bullets(self):
        diag = DescriptionDiagnostic()
        data = ListingData(
            description="Description",
            bullet_points=["One bullet", "Two bullets"],
            platform="amazon"
        )
        issues = diag.check(data)
        assert any("bullet" in i.title.lower() and ("few" in i.title.lower() or "3" in i.description) for i in issues)

    def test_spam_pattern_detection(self):
        diag = DescriptionDiagnostic()
        data = ListingData(description="AMAZING!!! BEST!!! BUY NOW!!!")
        issues = diag.check(data)
        assert any("spam" in i.title.lower() for i in issues)

    def test_feature_heavy_no_benefits(self):
        diag = DescriptionDiagnostic()
        data = ListingData(description="Made of steel. Has 5 buttons. Weighs 2 pounds. Measures 10 inches.")
        issues = diag.check(data)
        # Should detect lack of benefit-focused language
        assert any("benefit" in i.title.lower() or "feature" in i.description.lower() for i in issues)

    def test_good_description(self):
        diag = DescriptionDiagnostic()
        data = ListingData(
            description="You'll enjoy the premium stainless steel construction, perfect for daily use. " * 10,
            bullet_points=[f"Benefit {i}" for i in range(5)]
        )
        issues = diag.check(data)
        critical = [i for i in issues if i.severity == Severity.CRITICAL]
        assert len(critical) == 0


class TestImageDiagnostic:
    def test_no_images(self):
        diag = ImageDiagnostic()
        data = ListingData(images=0)
        issues = diag.check(data)
        assert any(i.severity == Severity.CRITICAL for i in issues)

    def test_too_few_images(self):
        diag = ImageDiagnostic()
        data = ListingData(images=2, platform="amazon")
        issues = diag.check(data)
        assert any(i.severity == Severity.HIGH for i in issues)

    def test_below_ideal_images(self):
        diag = ImageDiagnostic()
        data = ListingData(images=5, platform="amazon")
        issues = diag.check(data)
        # 5 images is okay but below ideal (7+)
        assert any(i.severity == Severity.LOW for i in issues)

    def test_good_image_count(self):
        diag = ImageDiagnostic()
        data = ListingData(images=8, platform="amazon")
        issues = diag.check(data)
        # Should have no or minimal issues
        assert len([i for i in issues if i.severity != Severity.LOW]) == 0


class TestPricingDiagnostic:
    def test_no_price(self):
        diag = PricingDiagnostic()
        data = ListingData(price=0)
        issues = diag.check(data)
        assert any(i.severity == Severity.CRITICAL for i in issues)

    def test_price_too_low(self):
        diag = PricingDiagnostic()
        data = ListingData(price=5.0, competitor_price_low=15.0)
        issues = diag.check(data)
        assert any("low" in i.title.lower() for i in issues)

    def test_price_too_high(self):
        diag = PricingDiagnostic()
        data = ListingData(price=100.0, competitor_price_high=50.0)
        issues = diag.check(data)
        assert any("above market" in i.title.lower() or "high" in i.description.lower() for i in issues)

    def test_not_charm_pricing(self):
        diag = PricingDiagnostic()
        data = ListingData(price=20.00)
        issues = diag.check(data)
        assert any("charm" in i.title.lower() or ".99" in i.description for i in issues)

    def test_excessive_discount(self):
        diag = PricingDiagnostic()
        data = ListingData(price=10.0, original_price=100.0)
        issues = diag.check(data)
        assert any("excessive" in i.title.lower() or "discount" in i.title.lower() for i in issues)

    def test_good_charm_pricing(self):
        diag = PricingDiagnostic()
        data = ListingData(price=19.99, competitor_price_low=18.0, competitor_price_high=25.0)
        issues = diag.check(data)
        # Should have minimal issues
        critical = [i for i in issues if i.severity in (Severity.CRITICAL, Severity.HIGH)]
        assert len(critical) == 0


class TestKeywordDiagnostic:
    def test_no_keywords_provided(self):
        diag = KeywordDiagnostic()
        data = ListingData(title="Product", description="Description")
        issues = diag.check(data)
        assert any("no target keywords" in i.title.lower() for i in issues)

    def test_missing_keywords_in_listing(self):
        diag = KeywordDiagnostic()
        data = ListingData(
            title="Generic Product",
            description="Basic description",
            keywords=["bluetooth", "wireless", "premium"]
        )
        issues = diag.check(data)
        assert any("missing" in i.title.lower() for i in issues)

    def test_no_keywords_in_title(self):
        diag = KeywordDiagnostic()
        data = ListingData(
            title="Random Product Name",
            description="Features bluetooth wireless technology",
            keywords=["bluetooth", "wireless"]
        )
        issues = diag.check(data)
        assert any("title" in i.description.lower() and "keyword" in i.title.lower() for i in issues)

    def test_good_keyword_coverage(self):
        diag = KeywordDiagnostic()
        data = ListingData(
            title="Bluetooth Wireless Headphones",
            description="Premium bluetooth wireless audio device with noise cancelling",
            keywords=["bluetooth", "wireless", "headphones"]
        )
        issues = diag.check(data)
        # Should have minimal issues
        high_severity = [i for i in issues if i.severity == Severity.HIGH]
        assert len(high_severity) == 0


class TestReviewDiagnostic:
    def test_zero_reviews(self):
        diag = ReviewDiagnostic()
        data = ListingData(reviews=0, rating=0.0)
        issues = diag.check(data)
        assert any(i.severity == Severity.HIGH for i in issues)

    def test_very_few_reviews(self):
        diag = ReviewDiagnostic()
        data = ListingData(reviews=5, rating=4.2)
        issues = diag.check(data)
        assert any("few" in i.title.lower() or "review" in i.title.lower() for i in issues)

    def test_low_rating_critical(self):
        diag = ReviewDiagnostic()
        data = ListingData(reviews=50, rating=3.0)
        issues = diag.check(data)
        assert any(i.severity == Severity.CRITICAL for i in issues)

    def test_below_average_rating(self):
        diag = ReviewDiagnostic()
        data = ListingData(reviews=100, rating=3.8)
        issues = diag.check(data)
        assert any(i.severity == Severity.HIGH for i in issues)

    def test_good_reviews(self):
        diag = ReviewDiagnostic()
        data = ListingData(reviews=150, rating=4.5)
        issues = diag.check(data)
        # Should have no high severity issues
        high = [i for i in issues if i.severity in (Severity.CRITICAL, Severity.HIGH)]
        assert len(high) == 0


class TestConversionDiagnostic:
    def test_very_low_conversion(self):
        diag = ConversionDiagnostic()
        data = ListingData(daily_views=100, daily_orders=0)
        issues = diag.check(data)
        assert any(i.severity == Severity.CRITICAL for i in issues)

    def test_below_average_conversion(self):
        diag = ConversionDiagnostic()
        data = ListingData(daily_views=100, daily_orders=3)  # 3% conversion
        issues = diag.check(data)
        assert any("conversion" in i.title.lower() for i in issues)

    def test_zero_traffic(self):
        diag = ConversionDiagnostic()
        data = ListingData(daily_views=0, daily_orders=0)
        issues = diag.check(data)
        assert any("zero traffic" in i.title.lower() or "visibility" in i.title.lower() for i in issues)

    def test_low_traffic(self):
        diag = ConversionDiagnostic()
        data = ListingData(daily_views=5, daily_orders=1)
        issues = diag.check(data)
        assert any("low traffic" in i.title.lower() or "visibility" in i.category.value for i in issues)


class TestListingForensics:
    def test_basic_diagnose(self):
        forensics = ListingForensics()
        data = ListingData(
            title="Premium Wireless Bluetooth Headphones",
            description="Great headphones with noise cancelling",
            bullet_points=["Feature 1", "Feature 2", "Feature 3"],
            images=5,
            price=49.99,
            reviews=50,
            rating=4.3,
            keywords=["wireless", "bluetooth"]
        )
        report = forensics.diagnose(data, "TEST123")
        assert isinstance(report, ForensicReport)
        assert report.health_score >= 0
        assert report.health_score <= 100
        assert report.grade in ["A+", "A", "B+", "B", "C", "D", "F"]

    def test_critical_issues_lower_score(self):
        forensics = ListingForensics()
        data = ListingData(
            title="Bad",  # Too short
            description="",  # Empty
            images=0,  # No images
            price=0,  # No price
        )
        report = forensics.diagnose(data)
        assert report.health_score < 50
        assert report.critical_count > 0

    def test_top_priorities_sorting(self):
        forensics = ListingForensics()
        data = ListingData(
            title="Short",
            description="",
            images=0,
            price=0
        )
        report = forensics.diagnose(data)
        assert len(report.top_priorities) <= 5
        # Should be sorted by impact
        if len(report.top_priorities) > 1:
            assert report.top_priorities[0].impact_score >= report.top_priorities[1].impact_score

    def test_issue_categorization(self):
        forensics = ListingForensics()
        data = ListingData(
            title="Product",
            description="Desc",
            images=2,
            price=10.0,
            reviews=0
        )
        report = forensics.diagnose(data)
        # Count by category
        categories = {issue.category for issue in report.issues}
        assert len(categories) > 0

    def test_batch_diagnose(self):
        forensics = ListingForensics()
        listings = [
            ("ID1", ListingData(title="Product 1", price=10.0, images=5)),
            ("ID2", ListingData(title="Product 2", price=20.0, images=3)),
        ]
        reports = forensics.batch_diagnose(listings)
        assert len(reports) == 2
        assert all(isinstance(r, ForensicReport) for r in reports)

    def test_compare_reports(self):
        forensics = ListingForensics()
        r1 = forensics.diagnose(ListingData(title="Good Product " * 10, price=19.99, images=7, reviews=100, rating=4.5), "GOOD")
        r2 = forensics.diagnose(ListingData(title="Bad", price=0, images=0), "BAD")

        comparison = forensics.compare([r1, r2])
        assert "best" in comparison
        assert "worst" in comparison
        assert comparison["best"] == "GOOD"
        assert comparison["worst"] == "BAD"

    def test_report_text_formatting(self):
        forensics = ListingForensics()
        data = ListingData(
            title="Test Product",
            description="Test",
            images=3,
            price=25.00
        )
        report = forensics.diagnose(data, "TEST")
        text = forensics.report_text(report)
        assert "LISTING FORENSICS REPORT" in text
        assert "TEST" in text
        assert "Health Score" in text

    def test_estimated_uplift(self):
        forensics = ListingForensics()
        # Bad listing should have high uplift potential
        bad_data = ListingData(title="Bad", description="", images=0, price=0)
        bad_report = forensics.diagnose(bad_data)
        assert bad_report.estimated_uplift_pct > 0

        # Good listing should have low uplift
        good_data = ListingData(
            title="Premium Wireless Headphones with Noise Cancelling Technology",
            description="Comprehensive description " * 20,
            bullet_points=[f"Feature {i}" for i in range(5)],
            images=8,
            price=49.99,
            reviews=200,
            rating=4.6,
            keywords=["wireless", "headphones"],
            daily_views=500,
            daily_orders=50
        )
        good_report = forensics.diagnose(good_data)
        assert good_report.estimated_uplift_pct < bad_report.estimated_uplift_pct


class TestForensicStore:
    def test_save_and_retrieve(self):
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            forensics = ListingForensics(db_path=db_path)
            data = ListingData(title="Test", price=10.0)
            report = forensics.diagnose(data, "PROD1")

            history = forensics.store.history("PROD1")
            assert len(history) > 0
            assert history[0]["listing_id"] == "PROD1"
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_worst_listings(self):
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            forensics = ListingForensics(db_path=db_path)
            forensics.diagnose(ListingData(title="Good " * 15, price=19.99, images=7), "GOOD1")
            forensics.diagnose(ListingData(title="Bad", price=0, images=0), "BAD1")

            worst = forensics.store.worst_listings(limit=5)
            assert len(worst) > 0
            assert worst[0]["listing_id"] == "BAD1"  # Should be worst
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
