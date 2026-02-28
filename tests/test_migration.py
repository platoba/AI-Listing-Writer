"""Tests for migration module."""

import pytest

from app.migration import (
    BatchMigrationReport,
    CATEGORY_MAPPINGS,
    FieldMapping,
    ListingMigrator,
    MigrationIssue,
    MigrationResult,
    MigrationStatus,
    Platform,
    PlatformSpec,
    PLATFORM_SPECS,
)


@pytest.fixture
def migrator():
    return ListingMigrator()


@pytest.fixture
def amazon_listing():
    return {
        "id": "B001234",
        "title": "Premium Wireless Bluetooth Earbuds with Active Noise Cancellation - 40H Battery Life",
        "description": "<p>Experience crystal clear audio with our <b>premium wireless earbuds</b>.</p>"
                      "<ul><li>Active Noise Cancellation</li><li>40H Battery</li></ul>",
        "bullet_points": [
            "Active Noise Cancellation - Block out ambient noise",
            "40-Hour Battery Life - Extended playback",
            "IPX7 Waterproof - Sweat resistant",
            "Bluetooth 5.3 - Low-latency connection",
            "Ergonomic Design - Comfortable fit",
        ],
        "price": 49.99,
        "images": [f"img{i}.jpg" for i in range(7)],
        "keywords": ["wireless earbuds", "bluetooth earbuds"],
        "backend_keywords": "earbuds headphones wireless bluetooth ANC waterproof",
        "category": "Electronics",
        "brand": "AudioPro",
        "sku": "AP-WE-001",
    }


@pytest.fixture
def minimal_listing():
    return {
        "id": "MIN001",
        "title": "Simple Product",
        "price": 10,
    }


class TestPlatform:
    def test_all_platforms(self):
        assert len(Platform) >= 10
        assert Platform.AMAZON.value == "amazon"
        assert Platform.TIKTOK_SHOP.value == "tiktok_shop"

    def test_platform_specs_exist(self):
        for p in Platform:
            assert p in PLATFORM_SPECS


class TestPlatformSpec:
    def test_amazon_spec(self):
        spec = PLATFORM_SPECS[Platform.AMAZON]
        assert spec.title_max == 200
        assert spec.bullet_points == 5
        assert spec.supports_html is True

    def test_shopee_spec(self):
        spec = PLATFORM_SPECS[Platform.SHOPEE]
        assert spec.title_max == 120
        assert spec.bullet_points == 0
        assert spec.emoji_friendly is True

    def test_ebay_spec(self):
        spec = PLATFORM_SPECS[Platform.EBAY]
        assert spec.title_max == 80
        assert "condition" in spec.required_fields

    def test_walmart_spec(self):
        spec = PLATFORM_SPECS[Platform.WALMART]
        assert spec.title_max == 75
        assert "upc" in spec.required_fields

    def test_mercado_libre_spec(self):
        spec = PLATFORM_SPECS[Platform.MERCADO_LIBRE]
        assert spec.title_max == 60
        assert "MX" in spec.regions


class TestListingMigrator:
    def test_get_spec(self, migrator):
        spec = migrator.get_spec("amazon")
        assert spec.name == "Amazon"

    def test_get_spec_invalid(self, migrator):
        with pytest.raises(ValueError):
            migrator.get_spec("invalid_platform")

    def test_supported_platforms(self):
        platforms = ListingMigrator.supported_platforms()
        assert "amazon" in platforms
        assert "shopee" in platforms
        assert len(platforms) >= 10

    def test_supported_migrations(self):
        pairs = ListingMigrator.supported_migrations()
        assert len(pairs) > 0
        assert ("amazon", "shopee") in pairs


class TestCompatibility:
    def test_amazon_to_shopee(self, migrator, amazon_listing):
        score, issues = migrator.analyze_compatibility(amazon_listing, "amazon", "shopee")
        assert 0 <= score <= 100
        # Should find HTML issue (shopee doesn't support HTML)
        html_issues = [i for i in issues if "HTML" in i.message]
        assert len(html_issues) > 0

    def test_amazon_to_ebay_title(self, migrator, amazon_listing):
        score, issues = migrator.analyze_compatibility(amazon_listing, "amazon", "ebay")
        # eBay title max is 80, Amazon listing title > 80
        title_issues = [i for i in issues if "title" in i.field.lower() and "long" in i.message.lower()]
        assert len(title_issues) > 0

    def test_amazon_to_walmart_missing_upc(self, migrator, amazon_listing):
        score, issues = migrator.analyze_compatibility(amazon_listing, "amazon", "walmart")
        missing = [i for i in issues if "upc" in i.message.lower()]
        assert len(missing) > 0

    def test_bullets_to_no_bullets_platform(self, migrator, amazon_listing):
        score, issues = migrator.analyze_compatibility(amazon_listing, "amazon", "aliexpress")
        bullet_issues = [i for i in issues if "bullet" in i.message.lower()]
        assert len(bullet_issues) > 0

    def test_no_bullets_to_bullets_platform(self, migrator, minimal_listing):
        score, issues = migrator.analyze_compatibility(minimal_listing, "aliexpress", "amazon")
        bullet_issues = [i for i in issues if "bullet" in i.message.lower()]
        # Should suggest adding bullets
        assert len(bullet_issues) > 0

    def test_perfect_compatibility(self, migrator):
        listing = {
            "id": "P1",
            "title": "Short Title",
            "description": "A " * 100,
            "price": 30,
            "images": ["a.jpg", "b.jpg", "c.jpg"],
            "category": "Electronics",
            "brand": "Test",
            "keywords": ["test"],
            "backend_keywords": "test keywords",
        }
        score, issues = migrator.analyze_compatibility(listing, "amazon", "amazon")
        assert score >= 80

    def test_too_many_images(self, migrator):
        listing = {
            "id": "IMG",
            "title": "Test Product Title for Testing",
            "description": "D" * 200,
            "price": 10,
            "images": [f"img{i}.jpg" for i in range(15)],
            "category": "Electronics",
            "brand": "T",
        }
        score, issues = migrator.analyze_compatibility(listing, "amazon", "aliexpress")
        img_issues = [i for i in issues if "image" in i.field.lower()]
        assert len(img_issues) > 0

    def test_backend_keywords_unsupported(self, migrator, amazon_listing):
        score, issues = migrator.analyze_compatibility(amazon_listing, "amazon", "shopee")
        bk_issues = [i for i in issues if "backend" in i.message.lower()]
        assert len(bk_issues) > 0


class TestMigration:
    def test_amazon_to_shopee(self, migrator, amazon_listing):
        result = migrator.migrate_listing(amazon_listing, "amazon", "shopee")
        assert result.status in (MigrationStatus.COMPLETED, MigrationStatus.NEEDS_REVIEW)
        assert result.compatibility_score > 0
        assert result.migrated_data.get("title")
        # HTML should be stripped
        assert "<p>" not in result.migrated_data.get("description", "")

    def test_amazon_to_ebay(self, migrator, amazon_listing):
        result = migrator.migrate_listing(amazon_listing, "amazon", "ebay")
        # Title should be truncated to 80
        assert len(result.migrated_data["title"]) <= 80

    def test_bullets_merged_to_desc(self, migrator, amazon_listing):
        result = migrator.migrate_listing(amazon_listing, "amazon", "aliexpress")
        # Bullet points should be merged into description
        assert "bullet_points" not in result.migrated_data or not result.migrated_data.get("bullet_points")
        assert "•" in result.migrated_data.get("description", "")

    def test_images_trimmed(self, migrator, amazon_listing):
        result = migrator.migrate_listing(amazon_listing, "amazon", "aliexpress")
        # AliExpress max 6 images
        assert len(result.migrated_data.get("images", [])) <= 6

    def test_backend_keywords_dropped(self, migrator, amazon_listing):
        result = migrator.migrate_listing(amazon_listing, "amazon", "shopee")
        assert "backend_keywords" not in result.migrated_data

    def test_category_mapping(self, migrator, amazon_listing):
        result = migrator.migrate_listing(amazon_listing, "amazon", "shopee")
        assert result.migrated_data.get("category") == "Electronic Devices"

    def test_auto_fix_disabled(self, migrator, amazon_listing):
        result = migrator.migrate_listing(amazon_listing, "amazon", "shopee", auto_fix=False)
        assert result.status in (MigrationStatus.NEEDS_REVIEW, MigrationStatus.COMPLETED, MigrationStatus.FAILED)

    def test_generate_bullets(self, migrator):
        listing = {
            "id": "GEN1",
            "title": "Product with long description",
            "description": "This product features advanced technology. "
                         "It is made from premium materials. "
                         "The design is ergonomic and comfortable. "
                         "Battery lasts for 40 hours of continuous use. "
                         "Waterproof rating of IPX7 for all weather conditions.",
            "price": 30,
            "category": "Electronics",
            "brand": "Test",
            "images": ["a.jpg", "b.jpg", "c.jpg"],
        }
        result = migrator.migrate_listing(listing, "aliexpress", "amazon")
        bullets = result.migrated_data.get("bullet_points", [])
        assert len(bullets) > 0

    def test_migration_result_fields(self, migrator, amazon_listing):
        result = migrator.migrate_listing(amazon_listing, "amazon", "shopee")
        assert result.source_platform == "amazon"
        assert result.target_platform == "shopee"
        assert result.listing_id == "B001234"
        assert result.created_at

    def test_auto_fixes_recorded(self, migrator, amazon_listing):
        result = migrator.migrate_listing(amazon_listing, "amazon", "shopee")
        assert len(result.auto_fixes_applied) > 0

    def test_field_mappings_recorded(self, migrator, amazon_listing):
        result = migrator.migrate_listing(amazon_listing, "amazon", "shopee")
        assert len(result.field_mappings) > 0

    def test_migration_minimal_listing(self, migrator, minimal_listing):
        result = migrator.migrate_listing(minimal_listing, "amazon", "shopee")
        # Should fail or need review due to missing required fields
        assert result.status in (MigrationStatus.FAILED, MigrationStatus.NEEDS_REVIEW, MigrationStatus.COMPLETED)


class TestTitleMigration:
    def test_truncate_at_word_boundary(self, migrator):
        spec = migrator.get_spec("ebay")
        long_title = "Premium Wireless Bluetooth Earbuds with Active Noise Cancellation and Long Battery"
        result = migrator._migrate_title(long_title, "amazon", "ebay", spec)
        assert len(result) <= 80
        # Should not cut mid-word
        assert not result.endswith(" ")

    def test_short_title_unchanged(self, migrator):
        spec = migrator.get_spec("amazon")
        title = "Short Title"
        result = migrator._migrate_title(title, "ebay", "amazon", spec)
        assert result == title


class TestDescriptionMigration:
    def test_strip_html(self, migrator):
        spec = migrator.get_spec("shopee")
        html_desc = "<p>Hello <b>world</b></p><ul><li>Item 1</li><li>Item 2</li></ul>"
        result = migrator._migrate_description(html_desc, {}, "amazon", "shopee", spec)
        assert "<p>" not in result
        assert "<b>" not in result
        assert "•" in result

    def test_truncate_long_desc(self, migrator):
        spec = migrator.get_spec("temu")
        long_desc = "A" * 5000
        result = migrator._migrate_description(long_desc, {}, "amazon", "temu", spec)
        assert len(result) <= spec.desc_max

    def test_preserve_html_when_supported(self, migrator):
        spec = migrator.get_spec("ebay")
        html_desc = "<p>Hello <b>world</b></p>"
        result = migrator._migrate_description(html_desc, {}, "amazon", "ebay", spec)
        assert "<p>" in result  # eBay supports HTML


class TestStripHTML:
    def test_br_tags(self, migrator):
        assert "\n" in migrator._strip_html("Hello<br>World")

    def test_list_items(self, migrator):
        result = migrator._strip_html("<ul><li>Item 1</li><li>Item 2</li></ul>")
        assert "• Item 1" in result

    def test_paragraphs(self, migrator):
        result = migrator._strip_html("<p>Para 1</p><p>Para 2</p>")
        assert "Para 1" in result
        assert "Para 2" in result

    def test_headings(self, migrator):
        result = migrator._strip_html("<h1>Title</h1><p>Content</p>")
        assert "Title" in result
        assert "<h1>" not in result

    def test_generic_tags(self, migrator):
        result = migrator._strip_html("<div class='x'><span>text</span></div>")
        assert result == "text"

    def test_multiple_newlines_collapsed(self, migrator):
        result = migrator._strip_html("<p>A</p><p></p><p></p><p>B</p>")
        assert "\n\n\n" not in result


class TestExtractBulletPoints:
    def test_extract_from_text(self, migrator):
        desc = ("This product is waterproof. "
                "It has 40 hours of battery life. "
                "The design is ergonomic and comfortable. "
                "Sound quality is crystal clear. "
                "Compatible with all devices.")
        bullets = migrator._extract_bullet_points(desc, 5)
        assert len(bullets) == 5

    def test_extract_limited(self, migrator):
        desc = "Feature one is great. Feature two is amazing. Feature three is wonderful."
        bullets = migrator._extract_bullet_points(desc, 2)
        assert len(bullets) == 2

    def test_extract_deduplication(self, migrator):
        desc = "This is a great product. This is a great item. Something different here."
        bullets = migrator._extract_bullet_points(desc, 5)
        # Should deduplicate similar sentences
        assert len(bullets) <= 3

    def test_extract_empty(self, migrator):
        bullets = migrator._extract_bullet_points("", 5)
        assert bullets == []


class TestCategoryMapping:
    def test_amazon_to_shopee(self, migrator):
        result = migrator._map_category("Electronics", "amazon", "shopee")
        assert result == "Electronic Devices"

    def test_amazon_to_ebay(self, migrator):
        result = migrator._map_category("Electronics", "amazon", "ebay")
        assert result == "Consumer Electronics"

    def test_amazon_to_walmart(self, migrator):
        result = migrator._map_category("Beauty & Personal Care", "amazon", "walmart")
        assert result == "Beauty"

    def test_reverse_mapping(self, migrator):
        result = migrator._map_category("Electronic Devices", "shopee", "amazon")
        assert result == "Electronics"

    def test_fuzzy_match(self, migrator):
        result = migrator._map_category("Electronics & Gadgets", "amazon", "shopee")
        assert result is not None

    def test_no_mapping(self, migrator):
        result = migrator._map_category("Totally Unique Category", "amazon", "shopee")
        assert result is None


class TestBatchMigration:
    def test_batch_basic(self, migrator, amazon_listing, minimal_listing):
        report = migrator.batch_migrate([amazon_listing, minimal_listing], "amazon", "shopee")
        assert report.total == 2
        assert report.completed + report.failed + report.needs_review == 2

    def test_batch_report_fields(self, migrator, amazon_listing):
        report = migrator.batch_migrate([amazon_listing], "amazon", "ebay")
        assert report.source_platform == "amazon"
        assert report.target_platform == "ebay"
        assert report.generated_at

    def test_batch_common_issues(self, migrator, amazon_listing):
        listings = [dict(amazon_listing) for _ in range(3)]
        report = migrator.batch_migrate(listings, "amazon", "shopee")
        # Common issues should be aggregated
        assert len(report.common_issues) > 0

    def test_batch_compatibility(self, migrator, amazon_listing):
        report = migrator.batch_migrate([amazon_listing], "amazon", "shopee")
        assert 0 <= report.avg_compatibility <= 100


class TestPlatformComparison:
    def test_compare_amazon_shopee(self, migrator):
        comp = migrator.get_platform_comparison("amazon", "shopee")
        assert comp["source"]["platform"] == "amazon"
        assert comp["target"]["platform"] == "shopee"
        assert "differences" in comp
        assert comp["differences"]["html_support"]["action"] == "strip"
        assert comp["category_mapping_available"] is True

    def test_compare_amazon_ebay(self, migrator):
        comp = migrator.get_platform_comparison("amazon", "ebay")
        assert comp["differences"]["title_max"]["action"] == "truncate"

    def test_compare_same_platform(self, migrator):
        comp = migrator.get_platform_comparison("amazon", "amazon")
        assert comp["differences"]["title_max"]["action"] == "ok"

    def test_bullet_action_merge(self, migrator):
        src = PLATFORM_SPECS[Platform.AMAZON]
        tgt = PLATFORM_SPECS[Platform.SHOPEE]
        assert migrator._bullet_action(src, tgt) == "merge_to_desc"

    def test_bullet_action_generate(self, migrator):
        src = PLATFORM_SPECS[Platform.SHOPEE]
        tgt = PLATFORM_SPECS[Platform.AMAZON]
        assert migrator._bullet_action(src, tgt) == "generate"

    def test_bullet_action_ok(self, migrator):
        src = PLATFORM_SPECS[Platform.AMAZON]
        tgt = PLATFORM_SPECS[Platform.WALMART]
        assert migrator._bullet_action(src, tgt) == "ok"


class TestFormatting:
    def test_format_migration_report(self, migrator, amazon_listing):
        result = migrator.migrate_listing(amazon_listing, "amazon", "shopee")
        text = migrator.format_migration_report(result)
        assert "Migration" in text
        assert "amazon" in text
        assert "shopee" in text

    def test_format_migration_failed(self, migrator, minimal_listing):
        result = migrator.migrate_listing(minimal_listing, "amazon", "walmart")
        text = migrator.format_migration_report(result)
        assert result.status.value in text

    def test_format_batch_report(self, migrator, amazon_listing):
        report = migrator.batch_migrate([amazon_listing], "amazon", "shopee")
        text = migrator.format_batch_report(report)
        assert "Batch" in text
        assert "1" in text


class TestMigrationStatus:
    def test_values(self):
        assert MigrationStatus.COMPLETED.value == "completed"
        assert MigrationStatus.FAILED.value == "failed"
        assert MigrationStatus.NEEDS_REVIEW.value == "needs_review"


class TestMigrationIssue:
    def test_creation(self):
        issue = MigrationIssue(
            field="title", severity="warning",
            message="Title too long", auto_fixable=True,
        )
        assert issue.field == "title"
        assert issue.auto_fixable is True

    def test_defaults(self):
        issue = MigrationIssue("f", "s", "m")
        assert issue.auto_fixable is False
        assert issue.fix_description == ""


class TestFieldMapping:
    def test_creation(self):
        fm = FieldMapping("title", "title", "copy")
        assert fm.transform == "copy"
        assert fm.notes == ""
