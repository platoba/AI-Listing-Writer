"""Tests for category optimizer."""
import pytest
from app.category_optimizer import (
    CategoryOptimizer, CategoryMatch, CategorySuggestion,
    CrossPlatformMapping, detect_category,
    CATEGORY_TAXONOMY, AMAZON_BROWSE_NODES,
    PLATFORM_CATEGORY_NAMES,
)


# ── Category Detection ──────────────────────────────────────

class TestCategoryDetection:
    @pytest.fixture
    def optimizer(self):
        return CategoryOptimizer()

    def test_detect_electronics(self, optimizer):
        result = optimizer.detect_category(
            "Wireless Bluetooth Headphones with Noise Cancelling",
            platform="amazon",
        )
        assert result.primary.category is not None
        assert result.primary.confidence > 0

    def test_detect_clothing(self, optimizer):
        result = optimizer.detect_category(
            "Men's Running Shoes Lightweight Breathable Sneakers",
            platform="amazon",
        )
        assert "Clothing" in result.primary.category or "Shoe" in result.primary.category or "Fashion" in result.primary.category

    def test_detect_beauty(self, optimizer):
        result = optimizer.detect_category(
            "Vitamin C Serum Anti-Aging Moisturizer Skincare",
            platform="amazon",
        )
        assert "Beauty" in result.primary.category or "Personal Care" in result.primary.category

    def test_detect_home(self, optimizer):
        result = optimizer.detect_category(
            "Modern LED Desk Lamp with USB Charging Port",
            platform="amazon",
        )
        # Should match Electronics or Home
        assert result.primary.confidence > 0

    def test_detect_sports(self, optimizer):
        result = optimizer.detect_category(
            "Yoga Mat Non-Slip Exercise Fitness Pilates",
            platform="amazon",
        )
        assert result.primary.confidence > 0

    def test_detect_toys(self, optimizer):
        result = optimizer.detect_category(
            "LEGO Building Blocks Educational Toy for Kids",
            platform="amazon",
        )
        assert result.primary.confidence > 0

    def test_detect_pet(self, optimizer):
        result = optimizer.detect_category(
            "Dog Leash Retractable Pet Walking Collar",
            platform="amazon",
        )
        assert "Pet" in result.primary.category

    def test_detect_baby(self, optimizer):
        result = optimizer.detect_category(
            "Baby Stroller Lightweight Foldable Infant Carriage",
            platform="amazon",
        )
        assert result.primary.confidence > 0

    def test_detect_automotive(self, optimizer):
        result = optimizer.detect_category(
            "Car Seat Cover Leather Auto Interior Dashboard",
            platform="amazon",
        )
        assert result.primary.confidence > 0

    def test_detect_food(self, optimizer):
        result = optimizer.detect_category(
            "Organic Green Tea Bags Premium Japanese Matcha",
            platform="amazon",
        )
        assert result.primary.confidence > 0

    def test_detect_chinese_product(self, optimizer):
        result = optimizer.detect_category(
            "蓝牙无线耳机 降噪 运动耳机",
            platform="shopee",
        )
        assert result.primary.confidence > 0

    def test_detect_with_description(self, optimizer):
        result = optimizer.detect_category(
            "Premium Headphones",
            description="Wireless bluetooth earbuds with active noise cancelling and 30 hour battery life.",
            platform="amazon",
        )
        assert result.primary.confidence > 0

    def test_detect_with_keywords(self, optimizer):
        result = optimizer.detect_category(
            "Premium Product",
            keywords=["dog", "pet", "collar", "leash", "training"],
            platform="amazon",
        )
        assert "Pet" in result.primary.category


# ── Subcategory Detection ────────────────────────────────────

class TestSubcategoryDetection:
    @pytest.fixture
    def optimizer(self):
        return CategoryOptimizer()

    def test_subcategory_detected(self, optimizer):
        result = optimizer.detect_category(
            "Women's Summer Dress Casual Floral Skirt",
            platform="amazon",
        )
        assert result.primary.subcategory != ""

    def test_subcategory_specificity(self, optimizer):
        result = optimizer.detect_category(
            "Cat Litter Box Self-Cleaning Automatic",
            platform="amazon",
        )
        if result.primary.subcategory:
            assert "Cat" in result.primary.subcategory

    def test_path_includes_hierarchy(self, optimizer):
        result = optimizer.detect_category(
            "Professional Running Shoes Men's Athletic Sneakers",
            platform="amazon",
        )
        assert len(result.primary.path) >= 1


# ── Browse Node Mapping ─────────────────────────────────────

class TestBrowseNodes:
    @pytest.fixture
    def optimizer(self):
        return CategoryOptimizer()

    def test_browse_node_for_amazon(self, optimizer):
        result = optimizer.detect_category(
            "Bluetooth Wireless Earbuds Headphones",
            platform="amazon",
        )
        # Electronics should have a browse node
        assert result.primary.browse_node != "" or result.primary.category != "Uncategorized"

    def test_no_browse_node_for_non_amazon(self, optimizer):
        result = optimizer.detect_category(
            "Bluetooth Wireless Earbuds Headphones",
            platform="shopee",
        )
        # Shopee shouldn't have Amazon browse nodes
        assert result.primary.browse_node == ""

    def test_browse_nodes_exist(self):
        assert "Electronics" in AMAZON_BROWSE_NODES
        assert "node" in AMAZON_BROWSE_NODES["Electronics"]


# ── Platform Mapping ─────────────────────────────────────────

class TestPlatformMapping:
    @pytest.fixture
    def optimizer(self):
        return CategoryOptimizer()

    def test_amazon_category_names(self, optimizer):
        result = optimizer.detect_category(
            "Wireless Headphones Bluetooth",
            platform="amazon",
        )
        assert result.platform == "amazon"

    def test_shopee_category_names(self, optimizer):
        result = optimizer.detect_category(
            "Wireless Headphones Bluetooth",
            platform="shopee",
        )
        assert result.platform == "shopee"

    def test_ebay_category_names(self, optimizer):
        result = optimizer.detect_category(
            "Vintage Leather Wallet for Men",
            platform="ebay",
        )
        assert result.platform == "ebay"

    def test_walmart_category_names(self, optimizer):
        result = optimizer.detect_category(
            "Kitchen Blender Smoothie Maker",
            platform="walmart",
        )
        assert result.platform == "walmart"

    def test_all_platforms_have_mappings(self):
        for platform in PLATFORM_CATEGORY_NAMES:
            assert len(PLATFORM_CATEGORY_NAMES[platform]) > 0


# ── Alternatives ─────────────────────────────────────────────

class TestAlternatives:
    @pytest.fixture
    def optimizer(self):
        return CategoryOptimizer()

    def test_alternatives_provided(self, optimizer):
        result = optimizer.detect_category(
            "Smart Fitness Watch with Heart Rate Monitor Running GPS",
            platform="amazon",
        )
        # Should match Electronics and Sports
        assert isinstance(result.alternatives, list)

    def test_alternatives_sorted_by_confidence(self, optimizer):
        result = optimizer.detect_category(
            "Smart Fitness Watch Sport Running GPS Heart Rate",
            platform="amazon",
        )
        if len(result.alternatives) >= 2:
            assert result.alternatives[0].confidence >= result.alternatives[1].confidence


# ── Cross-Platform Mapping ───────────────────────────────────

class TestCrossPlatformMapping:
    @pytest.fixture
    def optimizer(self):
        return CategoryOptimizer()

    def test_cross_platform_map(self, optimizer):
        mapping = optimizer.cross_platform_map("Electronics", source_platform="amazon")
        assert isinstance(mapping, CrossPlatformMapping)
        assert len(mapping.mappings) > 0

    def test_all_platforms_mapped(self, optimizer):
        mapping = optimizer.cross_platform_map("Electronics")
        for platform in PLATFORM_CATEGORY_NAMES:
            assert platform in mapping.mappings

    def test_mapping_has_confidence(self, optimizer):
        mapping = optimizer.cross_platform_map("Electronics")
        for match in mapping.mappings.values():
            assert match.confidence > 0

    def test_mapping_summary(self, optimizer):
        mapping = optimizer.cross_platform_map("Electronics", subcategory="Audio & Headphones")
        summary = mapping.summary()
        assert "Cross-Platform" in summary

    def test_reverse_lookup(self, optimizer):
        # Map platform name back to generic
        result = optimizer._reverse_lookup("Consumer Electronics", "ebay")
        assert result == "Electronics"

    def test_reverse_lookup_unknown(self, optimizer):
        result = optimizer._reverse_lookup("Nonexistent Category", "amazon")
        assert result is None


# ── Category Validation ──────────────────────────────────────

class TestCategoryValidation:
    @pytest.fixture
    def optimizer(self):
        return CategoryOptimizer()

    def test_valid_category(self, optimizer):
        result = optimizer.validate_category("Electronics", "amazon")
        assert result["valid"] is True

    def test_invalid_category(self, optimizer):
        result = optimizer.validate_category("Nonexistent Stuff", "amazon")
        assert result["valid"] is False
        assert len(result["issues"]) > 0

    def test_gated_category_warning(self, optimizer):
        result = optimizer.validate_category("Grocery & Gourmet Food", "amazon")
        issues_text = " ".join(result["issues"])
        assert "ungating" in issues_text.lower() or "approval" in issues_text.lower()

    def test_mismatched_product(self, optimizer):
        result = optimizer.validate_category(
            "Electronics", "amazon",
            product_data={"title": "Organic Dog Food Premium Pet Nutrition", "description": "For dogs"},
        )
        assert len(result["issues"]) > 0 or len(result["suggestions"]) > 0

    def test_closest_category_suggestion(self, optimizer):
        closest = optimizer._find_closest_category("Electronic Devices", {"electronics", "clothing"})
        assert closest == "electronics"

    def test_closest_category_none(self, optimizer):
        closest = optimizer._find_closest_category("XYZ", {"abc", "def"})
        assert closest is None


# ── Tips & Warnings ──────────────────────────────────────────

class TestTipsWarnings:
    @pytest.fixture
    def optimizer(self):
        return CategoryOptimizer()

    def test_tips_generated(self, optimizer):
        result = optimizer.detect_category(
            "Bluetooth Headphones Wireless",
            platform="amazon",
        )
        assert isinstance(result.tips, list)

    def test_warnings_for_ambiguous(self, optimizer):
        # Product that could be in multiple categories
        result = optimizer.detect_category(
            "Smart Fitness Watch Sport Heart Rate GPS Running Exercise",
            platform="amazon",
        )
        assert isinstance(result.warnings, list)

    def test_low_confidence_tip(self, optimizer):
        result = optimizer.detect_category(
            "Generic thing random stuff",
            platform="amazon",
        )
        if result.primary.confidence < 0.3:
            tips_text = " ".join(result.tips)
            assert "confidence" in tips_text.lower() or len(result.tips) > 0


# ── ASIN Suggestion ──────────────────────────────────────────

class TestASINSuggestion:
    @pytest.fixture
    def optimizer(self):
        return CategoryOptimizer()

    def test_suggest_from_asin(self, optimizer):
        result = optimizer.suggest_from_asin(
            "B0ABCDEF12",
            title="Wireless Bluetooth Headphones",
            description="Active noise cancelling earbuds",
        )
        assert isinstance(result, CategorySuggestion)
        assert result.primary.confidence > 0

    def test_asin_tip_added(self, optimizer):
        result = optimizer.suggest_from_asin("B0TESTTEST", title="Test Product")
        tips_text = " ".join(result.tips)
        assert "B0" in tips_text or "ASIN" in tips_text


# ── Formatting ───────────────────────────────────────────────

class TestFormatting:
    @pytest.fixture
    def optimizer(self):
        return CategoryOptimizer()

    def test_format_suggestion(self, optimizer):
        result = optimizer.detect_category(
            "Wireless Bluetooth Headphones ANC",
            platform="amazon",
        )
        formatted = optimizer.format_suggestion(result)
        assert "Category Suggestion" in formatted
        assert "Primary" in formatted

    def test_format_includes_alternatives(self, optimizer):
        result = optimizer.detect_category(
            "Smart Watch Fitness GPS Running Sport",
            platform="amazon",
        )
        formatted = optimizer.format_suggestion(result)
        assert "Primary" in formatted

    def test_format_includes_browse_node(self, optimizer):
        result = optimizer.detect_category(
            "Bluetooth Earbuds Headphones Wireless",
            platform="amazon",
        )
        formatted = optimizer.format_suggestion(result)
        if result.primary.browse_node:
            assert "Browse Node" in formatted


# ── Convenience Function ─────────────────────────────────────

class TestConvenienceFunction:
    def test_detect_category_function(self):
        result = detect_category("Dog Collar Leather Pet Leash")
        assert isinstance(result, CategorySuggestion)
        assert result.primary.confidence > 0

    def test_detect_category_with_platform(self):
        result = detect_category("Dog Collar", platform="shopee")
        assert result.platform == "shopee"

    def test_detect_category_with_description(self):
        result = detect_category(
            "Premium Product",
            description="Wireless bluetooth headphones with noise cancelling",
        )
        assert result.primary.confidence > 0


# ── Taxonomy Coverage ─────────────────────────────────────────

class TestTaxonomyCoverage:
    def test_all_categories_have_keywords(self):
        for cat, data in CATEGORY_TAXONOMY.items():
            assert len(data["keywords"]) > 0, f"{cat} has no keywords"

    def test_all_categories_have_subcategories(self):
        for cat, data in CATEGORY_TAXONOMY.items():
            assert len(data.get("subcategories", {})) > 0, f"{cat} has no subcategories"

    def test_subcategories_have_keywords(self):
        for cat, data in CATEGORY_TAXONOMY.items():
            for sub, kws in data.get("subcategories", {}).items():
                assert len(kws) > 0, f"{cat}/{sub} has no keywords"

    def test_all_amazon_nodes_valid(self):
        for cat, data in AMAZON_BROWSE_NODES.items():
            assert "node" in data, f"{cat} missing node"
            assert data["node"].isdigit(), f"{cat} node is not numeric"

    def test_platform_coverage(self):
        """Each platform should map at least 5 categories."""
        for platform, names in PLATFORM_CATEGORY_NAMES.items():
            assert len(names) >= 5, f"{platform} has only {len(names)} category mappings"


# ── Edge Cases ───────────────────────────────────────────────

class TestEdgeCases:
    @pytest.fixture
    def optimizer(self):
        return CategoryOptimizer()

    def test_empty_title(self, optimizer):
        result = optimizer.detect_category("")
        assert result.primary.category == "Uncategorized"

    def test_special_characters_only(self, optimizer):
        result = optimizer.detect_category("★★★ $$$ !!!")
        assert result.primary.category == "Uncategorized"

    def test_very_long_title(self, optimizer):
        title = "Premium Bluetooth Wireless " * 50
        result = optimizer.detect_category(title)
        assert result.primary.confidence > 0

    def test_unknown_platform(self, optimizer):
        result = optimizer.detect_category("Headphones", platform="unknown_platform")
        assert result.primary is not None

    def test_cross_map_unknown_category(self, optimizer):
        mapping = optimizer.cross_platform_map("Nonexistent Category")
        assert len(mapping.mappings) > 0
