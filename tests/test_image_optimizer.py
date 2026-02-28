"""Tests for image_optimizer module."""
import pytest
from app.image_optimizer import (
    ImageInfo, ImageIssue, AltTextSuggestion, ImageOptimization,
    ImageOptimizer, analyze_listing_images, format_image_report,
    IMAGE_TYPES, PLATFORM_REQUIREMENTS,
)


# --- Fixtures ---

@pytest.fixture
def good_images():
    """Well-optimized image set for Amazon."""
    return [
        ImageInfo(url="https://example.com/main.jpg", filename="main.jpg",
                  alt_text="Premium Bluetooth Headphones - Main Product Image",
                  width=2000, height=2000, size_kb=400, position=1),
        ImageInfo(url="https://example.com/lifestyle.jpg", filename="lifestyle-use.jpg",
                  alt_text="Headphones worn during running - Lifestyle shot",
                  width=2000, height=2000, size_kb=350, position=2),
        ImageInfo(url="https://example.com/detail.jpg", filename="detail-closeup.jpg",
                  alt_text="Close-up of ear cushion material",
                  width=2000, height=2000, size_kb=300, position=3),
        ImageInfo(url="https://example.com/info.jpg", filename="infographic-specs.jpg",
                  alt_text="Product dimensions and specifications",
                  width=2000, height=2000, size_kb=500, position=4),
        ImageInfo(url="https://example.com/scale.jpg", filename="scale-reference.jpg",
                  alt_text="Size comparison with hand",
                  width=2000, height=2000, size_kb=280, position=5),
        ImageInfo(url="https://example.com/package.jpg", filename="package-contents.jpg",
                  alt_text="What's included in the box",
                  width=2000, height=2000, size_kb=320, position=6),
        ImageInfo(url="https://example.com/back.jpg", filename="back-view.jpg",
                  alt_text="Rear view showing controls",
                  width=2000, height=2000, size_kb=290, position=7),
    ]


@pytest.fixture
def poor_images():
    """Poorly optimized image set."""
    return [
        ImageInfo(url="https://example.com/1.jpg", filename="IMG_001.jpg",
                  alt_text="", width=400, height=400, size_kb=50, position=1),
        ImageInfo(url="https://example.com/2.jpg", filename="IMG_002.jpg",
                  alt_text="", width=300, height=800, size_kb=30, position=2),
    ]


@pytest.fixture
def amazon_optimizer():
    return ImageOptimizer("amazon")


@pytest.fixture
def shopify_optimizer():
    return ImageOptimizer("shopify")


@pytest.fixture
def etsy_optimizer():
    return ImageOptimizer("etsy")


# --- ImageInfo Tests ---

class TestImageInfo:
    def test_default_values(self):
        img = ImageInfo()
        assert img.url == ""
        assert img.filename == ""
        assert img.alt_text == ""
        assert img.width is None
        assert img.position == 0
        assert img.detected_type == "unknown"

    def test_custom_values(self):
        img = ImageInfo(
            url="https://example.com/img.jpg",
            filename="img.jpg",
            alt_text="Test",
            width=1000,
            height=1000,
            size_kb=200,
            position=1,
        )
        assert img.width == 1000
        assert img.position == 1


# --- ImageOptimization Tests ---

class TestImageOptimization:
    def test_error_count(self):
        opt = ImageOptimization(
            issues=[
                ImageIssue(severity="error", image_position=1,
                           message="test", fix_suggestion="fix"),
                ImageIssue(severity="warning", image_position=2,
                           message="test", fix_suggestion="fix"),
                ImageIssue(severity="error", image_position=3,
                           message="test", fix_suggestion="fix"),
            ]
        )
        assert opt.error_count == 2
        assert opt.warning_count == 1

    def test_empty_issues(self):
        opt = ImageOptimization()
        assert opt.error_count == 0
        assert opt.warning_count == 0


# --- Image Classification Tests ---

class TestImageClassification:
    def test_classify_main(self, amazon_optimizer):
        img = ImageInfo(filename="main-product.jpg", position=1)
        assert amazon_optimizer._classify_image(img) == "main"

    def test_classify_lifestyle(self, amazon_optimizer):
        img = ImageInfo(filename="lifestyle-shot.jpg", position=2)
        assert amazon_optimizer._classify_image(img) == "lifestyle"

    def test_classify_detail(self, amazon_optimizer):
        img = ImageInfo(filename="detail-closeup.jpg", position=3)
        assert amazon_optimizer._classify_image(img) == "detail"

    def test_classify_infographic(self, amazon_optimizer):
        img = ImageInfo(filename="infographic-specs.jpg", position=4)
        assert amazon_optimizer._classify_image(img) == "infographic"

    def test_classify_packaging(self, amazon_optimizer):
        img = ImageInfo(filename="package-contents.jpg", position=5)
        assert amazon_optimizer._classify_image(img) == "packaging"

    def test_classify_scale(self, amazon_optimizer):
        img = ImageInfo(filename="scale-hand.jpg", position=3)
        assert amazon_optimizer._classify_image(img) == "scale"

    def test_classify_by_alt_text(self, amazon_optimizer):
        img = ImageInfo(filename="img1.jpg",
                        alt_text="lifestyle shot in action", position=2)
        assert amazon_optimizer._classify_image(img) == "lifestyle"

    def test_classify_fallback_position(self, amazon_optimizer):
        img = ImageInfo(filename="xyz.jpg", position=1)
        assert amazon_optimizer._classify_image(img) == "main"

    def test_classify_unknown(self, amazon_optimizer):
        img = ImageInfo(filename="xyz.jpg", position=10)
        assert amazon_optimizer._classify_image(img) == "unknown"


# --- Count Scoring Tests ---

class TestCountScoring:
    def test_ideal_count(self, amazon_optimizer):
        score = amazon_optimizer._score_count(7)
        assert score == 100.0

    def test_above_ideal(self, amazon_optimizer):
        score = amazon_optimizer._score_count(9)
        assert score == 100.0

    def test_minimum_count(self, amazon_optimizer):
        score = amazon_optimizer._score_count(5)
        assert score == 60.0

    def test_below_minimum(self, amazon_optimizer):
        score = amazon_optimizer._score_count(2)
        assert 0 < score < 60

    def test_zero_count(self, amazon_optimizer):
        score = amazon_optimizer._score_count(0)
        assert score == 0.0

    def test_one_image(self, amazon_optimizer):
        score = amazon_optimizer._score_count(1)
        assert 0 < score < 30


# --- Diversity Scoring Tests ---

class TestDiversityScoring:
    def test_good_diversity(self, amazon_optimizer, good_images):
        result = ImageOptimization()
        for img in good_images:
            img.detected_type = amazon_optimizer._classify_image(img)
            result.detected_types[img.detected_type] = \
                result.detected_types.get(img.detected_type, 0) + 1
        score = amazon_optimizer._score_diversity(good_images, result)
        assert score > 70

    def test_missing_required_type(self, amazon_optimizer):
        images = [
            ImageInfo(filename="detail.jpg", position=2, detected_type="detail"),
        ]
        result = ImageOptimization()
        result.detected_types = {"detail": 1}
        score = amazon_optimizer._score_diversity(images, result)
        assert score < 100
        assert "main" in result.missing_types

    def test_all_same_type(self, amazon_optimizer):
        images = [
            ImageInfo(filename=f"img{i}.jpg", position=i, detected_type="main")
            for i in range(5)
        ]
        result = ImageOptimization()
        result.detected_types = {"main": 5}
        score = amazon_optimizer._score_diversity(images, result)
        assert score < 100


# --- Quality Scoring Tests ---

class TestQualityScoring:
    def test_good_quality(self, amazon_optimizer, good_images):
        result = ImageOptimization()
        score = amazon_optimizer._score_quality(good_images, result)
        assert score == 100.0
        assert result.error_count == 0

    def test_low_resolution(self, amazon_optimizer):
        images = [
            ImageInfo(width=400, height=400, position=1),
        ]
        result = ImageOptimization()
        score = amazon_optimizer._score_quality(images, result)
        assert score < 100
        assert result.error_count > 0

    def test_below_ideal_resolution(self, amazon_optimizer):
        images = [
            ImageInfo(width=1200, height=1200, position=1),
        ]
        result = ImageOptimization()
        score = amazon_optimizer._score_quality(images, result)
        assert score < 100
        assert result.warning_count > 0

    def test_extreme_aspect_ratio(self, amazon_optimizer):
        images = [
            ImageInfo(width=2000, height=500, position=1),
        ]
        result = ImageOptimization()
        score = amazon_optimizer._score_quality(images, result)
        assert score < 100

    def test_oversized_file(self, amazon_optimizer):
        images = [
            ImageInfo(size_kb=15000, position=1),  # 15MB > 10MB limit
        ]
        result = ImageOptimization()
        score = amazon_optimizer._score_quality(images, result)
        assert score < 100
        assert result.error_count > 0

    def test_bad_format(self, amazon_optimizer):
        images = [
            ImageInfo(filename="image.bmp", position=1),
        ]
        result = ImageOptimization()
        score = amazon_optimizer._score_quality(images, result)
        assert score < 100

    def test_no_dimensions(self, amazon_optimizer):
        images = [ImageInfo(position=1)]
        result = ImageOptimization()
        score = amazon_optimizer._score_quality(images, result)
        assert score == 100.0  # Can't check what we don't have


# --- Alt Text Tests ---

class TestAltTextScoring:
    def test_good_alt_texts(self, amazon_optimizer, good_images):
        result = ImageOptimization()
        score = amazon_optimizer._score_alt_texts(
            good_images, "Product", "Category", result
        )
        assert score > 80

    def test_missing_alt_texts(self, amazon_optimizer, poor_images):
        result = ImageOptimization()
        score = amazon_optimizer._score_alt_texts(
            poor_images, "Product", "Category", result
        )
        assert score < 80
        assert len(result.alt_text_suggestions) > 0

    def test_short_alt_text(self, amazon_optimizer):
        images = [
            ImageInfo(alt_text="img", position=1),
        ]
        result = ImageOptimization()
        score = amazon_optimizer._score_alt_texts(
            images, "Product", "Category", result
        )
        assert score < 100
        assert len(result.alt_text_suggestions) > 0

    def test_long_alt_text(self, amazon_optimizer):
        images = [
            ImageInfo(alt_text="a" * 150, position=1),
        ]
        result = ImageOptimization()
        score = amazon_optimizer._score_alt_texts(
            images, "Product", "Category", result
        )
        assert score < 100

    def test_generate_alt_text(self, amazon_optimizer):
        img = ImageInfo(detected_type="main", position=1)
        alt = amazon_optimizer._generate_alt_text(img, "Cool Product", "Electronics")
        assert "Cool Product" in alt
        assert len(alt) <= 125

    def test_generate_alt_text_no_title(self, amazon_optimizer):
        img = ImageInfo(detected_type="lifestyle", position=2)
        alt = amazon_optimizer._generate_alt_text(img, "", "")
        assert "Product in real-world use" in alt


# --- Grade Tests ---

class TestGrading:
    def test_grade_a_plus(self, amazon_optimizer):
        assert amazon_optimizer._to_grade(95) == "A+"

    def test_grade_a(self, amazon_optimizer):
        assert amazon_optimizer._to_grade(85) == "A"

    def test_grade_b(self, amazon_optimizer):
        assert amazon_optimizer._to_grade(75) == "B"

    def test_grade_c(self, amazon_optimizer):
        assert amazon_optimizer._to_grade(65) == "C"

    def test_grade_d(self, amazon_optimizer):
        assert amazon_optimizer._to_grade(55) == "D"

    def test_grade_f(self, amazon_optimizer):
        assert amazon_optimizer._to_grade(40) == "F"


# --- Full Analysis Tests ---

class TestFullAnalysis:
    def test_good_listing(self, amazon_optimizer, good_images):
        result = amazon_optimizer.analyze(good_images, "Product Title", "Electronics")
        assert result.total_images == 7
        assert result.overall_score > 70
        assert result.grade in ("A+", "A", "B")

    def test_poor_listing(self, amazon_optimizer, poor_images):
        result = amazon_optimizer.analyze(poor_images, "Product", "Category")
        assert result.total_images == 2
        assert result.overall_score < 60
        assert result.grade in ("D", "F")

    def test_empty_images(self, amazon_optimizer):
        result = amazon_optimizer.analyze([], "Product", "Category")
        assert result.total_images == 0
        assert result.overall_score == 0.0
        assert result.grade == "F"
        assert result.error_count > 0

    def test_recommendations_generated(self, amazon_optimizer, poor_images):
        result = amazon_optimizer.analyze(poor_images, "Product", "Category")
        assert len(result.recommendations) > 0

    def test_missing_lifestyle_recommendation(self, amazon_optimizer):
        images = [
            ImageInfo(filename="main.jpg", position=1, width=2000, height=2000,
                      alt_text="Main product"),
        ]
        result = amazon_optimizer.analyze(images, "Product", "Category")
        rec_text = " ".join(result.recommendations)
        assert "lifestyle" in rec_text.lower()

    def test_missing_infographic_recommendation(self, amazon_optimizer):
        images = [
            ImageInfo(filename="main.jpg", position=1, width=2000, height=2000,
                      alt_text="Main product"),
            ImageInfo(filename="lifestyle.jpg", position=2, width=2000, height=2000,
                      alt_text="Lifestyle shot"),
        ]
        result = amazon_optimizer.analyze(images, "Product", "Category")
        rec_text = " ".join(result.recommendations)
        assert "infographic" in rec_text.lower()


# --- Platform-Specific Tests ---

class TestPlatformSpecific:
    def test_amazon_requirements(self):
        req = PLATFORM_REQUIREMENTS["amazon"]
        assert req["min_images"] == 5
        assert req["ideal_images"] == 7
        assert req["max_images"] == 9

    def test_shopify_requirements(self):
        req = PLATFORM_REQUIREMENTS["shopify"]
        assert req["min_images"] == 3
        assert req["max_images"] == 250

    def test_etsy_requirements(self):
        req = PLATFORM_REQUIREMENTS["etsy"]
        assert req["min_images"] == 5
        assert req["ideal_resolution"] == (3000, 3000)

    def test_shopify_optimizer(self, shopify_optimizer, good_images):
        result = shopify_optimizer.analyze(good_images)
        assert result.platform == "shopify"

    def test_etsy_optimizer(self, etsy_optimizer, good_images):
        result = etsy_optimizer.analyze(good_images)
        assert result.platform == "etsy"

    def test_unknown_platform_defaults(self):
        opt = ImageOptimizer("unknown_platform")
        assert opt.requirements == PLATFORM_REQUIREMENTS["amazon"]

    def test_aliexpress_max_images(self):
        req = PLATFORM_REQUIREMENTS["aliexpress"]
        assert req["max_images"] == 6


# --- Convenience Function Tests ---

class TestConvenienceFunction:
    def test_analyze_from_dicts(self):
        images = [
            {"url": "https://example.com/1.jpg", "filename": "main.jpg",
             "alt_text": "Product", "width": 2000, "height": 2000,
             "size_kb": 300, "position": 1},
            {"url": "https://example.com/2.jpg", "filename": "detail-closeup.jpg",
             "alt_text": "Detail", "width": 2000, "height": 2000,
             "size_kb": 250, "position": 2},
        ]
        result = analyze_listing_images(images, "amazon", "Product", "Category")
        assert result.total_images == 2

    def test_analyze_empty_dicts(self):
        result = analyze_listing_images([], "amazon")
        assert result.total_images == 0
        assert result.grade == "F"

    def test_analyze_minimal_dict(self):
        result = analyze_listing_images([{"url": "test.jpg"}])
        assert result.total_images == 1

    def test_analyze_with_platform(self):
        result = analyze_listing_images(
            [{"url": "test.jpg"}], platform="etsy"
        )
        assert result.platform == "etsy"


# --- Format Report Tests ---

class TestFormatReport:
    def test_report_structure(self, amazon_optimizer, good_images):
        result = amazon_optimizer.analyze(good_images, "Product", "Category")
        report = format_image_report(result)
        assert "IMAGE OPTIMIZATION REPORT" in report
        assert "Platform" in report
        assert "Score Breakdown" in report

    def test_report_shows_types(self, amazon_optimizer, good_images):
        result = amazon_optimizer.analyze(good_images)
        report = format_image_report(result)
        assert "Image Types Detected" in report

    def test_report_shows_issues(self, amazon_optimizer, poor_images):
        result = amazon_optimizer.analyze(poor_images, "Product", "Category")
        report = format_image_report(result)
        assert "Issues" in report

    def test_report_shows_alt_suggestions(self, amazon_optimizer, poor_images):
        result = amazon_optimizer.analyze(poor_images, "Product", "Category")
        report = format_image_report(result)
        assert "Alt Text Suggestions" in report

    def test_report_shows_recommendations(self, amazon_optimizer, poor_images):
        result = amazon_optimizer.analyze(poor_images, "Product", "Category")
        report = format_image_report(result)
        assert "Recommendations" in report

    def test_empty_report(self):
        result = ImageOptimization()
        report = format_image_report(result)
        assert "IMAGE OPTIMIZATION REPORT" in report


# --- Data Integrity Tests ---

class TestDataIntegrity:
    def test_all_image_types_have_description(self):
        for name, data in IMAGE_TYPES.items():
            assert "description" in data, f"{name} missing description"
            assert "indicators" in data, f"{name} missing indicators"
            assert len(data["indicators"]) > 0, f"{name} has empty indicators"

    def test_all_platforms_have_required_fields(self):
        required = ["min_images", "ideal_images", "max_images",
                     "min_resolution", "formats", "max_size_mb"]
        for platform, req in PLATFORM_REQUIREMENTS.items():
            for field in required:
                assert field in req, f"{platform} missing {field}"

    def test_platform_min_less_than_ideal(self):
        for platform, req in PLATFORM_REQUIREMENTS.items():
            assert req["min_images"] <= req["ideal_images"], \
                f"{platform}: min > ideal"
            assert req["ideal_images"] <= req["max_images"], \
                f"{platform}: ideal > max"


# --- Edge Cases ---

class TestEdgeCases:
    def test_single_image(self, amazon_optimizer):
        images = [ImageInfo(filename="main.jpg", position=1, width=2000,
                            height=2000, alt_text="Product")]
        result = amazon_optimizer.analyze(images)
        assert result.total_images == 1
        assert 0 <= result.overall_score <= 100

    def test_maximum_images(self, amazon_optimizer):
        images = [
            ImageInfo(filename=f"img{i}.jpg", position=i,
                      width=2000, height=2000, alt_text=f"Image {i}")
            for i in range(1, 10)
        ]
        result = amazon_optimizer.analyze(images)
        assert result.count_score == 100.0

    def test_zero_dimensions(self, amazon_optimizer):
        images = [ImageInfo(width=0, height=0, position=1)]
        result = amazon_optimizer.analyze(images)
        # Should not crash
        assert result.total_images == 1

    def test_very_large_image(self, amazon_optimizer):
        images = [ImageInfo(width=10000, height=10000, size_kb=50000,
                            position=1)]
        result = amazon_optimizer.analyze(images)
        assert result.total_images == 1
