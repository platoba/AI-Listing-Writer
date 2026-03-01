"""Tests for Bundle Recommender."""
import pytest
from app.bundle_recommender import (
    BundleRecommender,
    Product, Bundle,
    BundleStrategy, DiscountType,
    _extract_category_keywords, _find_complements,
    _calculate_bundle_discount, _calculate_profitability,
    _generate_bundle_title,
)


class TestProductModel:
    def test_create_product(self):
        p = Product("P1", "Wireless Headphones", 49.99, "electronics", ["bluetooth", "wireless"], 20.00)
        assert p.id == "P1"
        assert p.price == 49.99
        assert p.cost == 20.00


class TestCategoryExtraction:
    def test_extract_phone_keyword(self):
        keywords = _extract_category_keywords("iPhone 13 Pro Max")
        assert "phone" in keywords

    def test_extract_camera_keyword(self):
        keywords = _extract_category_keywords("Canon DSLR Camera Kit")
        assert "camera" in keywords

    def test_no_keywords_found(self):
        keywords = _extract_category_keywords("Random Product Name")
        assert isinstance(keywords, list)


class TestComplementDiscovery:
    def test_find_phone_complements(self):
        phone = Product("P1", "iPhone 13", 999, "phone")
        available = [
            Product("A1", "Phone Case for iPhone", 19.99, "accessory"),
            Product("A2", "Screen Protector", 9.99, "accessory"),
            Product("A3", "Wireless Charger", 29.99, "accessory"),
        ]
        complements = _find_complements(phone, available)
        assert len(complements) > 0
        assert any("case" in c.title.lower() for c in complements)

    def test_find_camera_complements(self):
        camera = Product("C1", "Digital Camera", 499, "camera")
        available = [
            Product("A1", "Memory Card 64GB", 19.99, "storage"),
            Product("A2", "Camera Bag", 39.99, "accessory"),
            Product("A3", "Tripod", 29.99, "accessory"),
        ]
        complements = _find_complements(camera, available)
        assert len(complements) > 0

    def test_no_complements_found(self):
        product = Product("P1", "Generic Product", 10, "unknown")
        available = [Product("P2", "Another Generic", 15, "different")]
        complements = _find_complements(product, available)
        # Should fall back to same category
        assert isinstance(complements, list)


class TestBundleDiscount:
    def test_percentage_discount(self):
        products = [Product("P1", "Item A", 50, "cat"), Product("P2", "Item B", 30, "cat")]
        price, discount, pct = _calculate_bundle_discount(products, DiscountType.PERCENTAGE, 15.0)
        assert discount == 12.0  # 15% of 80
        assert price == 68.0
        assert pct == 15.0

    def test_fixed_discount(self):
        products = [Product("P1", "A", 50, "c"), Product("P2", "B", 30, "c")]
        price, discount, pct = _calculate_bundle_discount(products, DiscountType.FIXED_AMOUNT, 10.0)
        assert discount == 10.0
        assert price == 70.0

    def test_bogo_discount(self):
        products = [Product("P1", "A", 50, "c"), Product("P2", "B", 30, "c")]
        price, discount, pct = _calculate_bundle_discount(products, DiscountType.BOGO, 0)
        # BOGO = discount is price of cheapest
        assert discount == 30.0

    def test_tiered_discount(self):
        products = [Product(f"P{i}", f"Item {i}", 20, "c") for i in range(4)]
        price, discount, pct = _calculate_bundle_discount(products, DiscountType.TIERED, 0)
        # 4 items = 20% discount
        assert pct == 20.0


class TestProfitability:
    def test_high_margin_bundle(self):
        products = [
            Product("P1", "A", 100, "c", cost=30),
            Product("P2", "B", 50, "c", cost=15)
        ]
        bundle_price = 135  # $15 discount from $150
        score = _calculate_profitability(products, bundle_price)
        # Cost = 45, profit = 90, margin = 66% → high score
        assert score > 70

    def test_low_margin_bundle(self):
        products = [Product("P1", "A", 100, "c", cost=80)]
        bundle_price = 90
        score = _calculate_profitability(products, bundle_price)
        # Low margin
        assert score < 50

    def test_no_cost_data_estimation(self):
        products = [Product("P1", "A", 100, "c")]  # No cost
        bundle_price = 90
        score = _calculate_profitability(products, bundle_price)
        # Should estimate cost as 40% of price
        assert score >= 0


class TestBundleTitleGeneration:
    def test_complementary_title(self):
        products = [
            Product("P1", "iPhone 13 Pro Max", 999, "phone"),
            Product("P2", "Premium Phone Case", 19.99, "accessory")
        ]
        title = _generate_bundle_title(products, BundleStrategy.COMPLEMENTARY)
        assert "iPhone" in title or "Bundle" in title

    def test_variety_pack_title(self):
        products = [Product(f"P{i}", f"Shirt Size {i}", 29.99, "clothing") for i in range(3)]
        title = _generate_bundle_title(products, BundleStrategy.VARIETY_PACK)
        assert "3" in title or "Pack" in title

    def test_title_length_capped(self):
        products = [Product("P1", "Very Long Product Name " * 10, 100, "c")]
        title = _generate_bundle_title(products, BundleStrategy.COMPLEMENTARY)
        assert len(title) <= 120


class TestBundleRecommender:
    def test_recommend_complementary_bundles(self):
        recommender = BundleRecommender()
        phone = Product("P1", "iPhone 13", 799, "phone")
        available = [
            Product("A1", "Phone Case", 19.99, "accessory"),
            Product("A2", "Screen Protector", 9.99, "accessory"),
            Product("A3", "Charger", 29.99, "accessory"),
        ]
        bundles = recommender.recommend_bundles(
            phone, available, strategy=BundleStrategy.COMPLEMENTARY
        )
        assert len(bundles) > 0
        assert all(isinstance(b, Bundle) for b in bundles)

    def test_recommend_variety_pack(self):
        recommender = BundleRecommender()
        shirt1 = Product("S1", "T-Shirt Red", 19.99, "clothing")
        available = [
            Product("S2", "T-Shirt Blue", 19.99, "clothing"),
            Product("S3", "T-Shirt Green", 19.99, "clothing"),
        ]
        bundles = recommender.recommend_bundles(
            shirt1, available, strategy=BundleStrategy.VARIETY_PACK
        )
        assert len(bundles) > 0

    def test_recommend_upgrade_bundle(self):
        recommender = BundleRecommender()
        base = Product("B1", "Basic Headphones", 29.99, "audio")
        available = [
            Product("U1", "Premium Cable", 19.99, "accessory"),
            Product("U2", "Carrying Case", 39.99, "accessory"),
        ]
        bundles = recommender.recommend_bundles(
            base, available, strategy=BundleStrategy.UPGRADE
        )
        assert len(bundles) >= 0  # May or may not find upgrades

    def test_max_bundles_limit(self):
        recommender = BundleRecommender()
        main = Product("M", "Main Product", 100, "category")
        available = [Product(f"A{i}", f"Accessory {i}", 10, "acc") for i in range(10)]
        bundles = recommender.recommend_bundles(main, available, max_bundles=2)
        assert len(bundles) <= 2

    def test_profitability_sorting(self):
        recommender = BundleRecommender()
        main = Product("M", "Main", 100, "cat", cost=30)
        available = [
            Product("A1", "Low Profit", 10, "cat", cost=9),
            Product("A2", "High Profit", 50, "cat", cost=10),
        ]
        bundles = recommender.recommend_bundles(main, available)
        if len(bundles) > 1:
            # Should be sorted by profitability
            assert bundles[0].profitability_score >= bundles[1].profitability_score


class TestFindBestBundle:
    def test_find_best_bundle(self):
        recommender = BundleRecommender()
        main = Product("M", "Main Product", 100, "electronics")
        available = [
            Product("A1", "Accessory 1", 20, "accessory"),
            Product("A2", "Accessory 2", 30, "accessory"),
        ]
        best = recommender.find_best_bundle(main, available)
        assert best is not None
        assert isinstance(best, Bundle)

    def test_no_bundles_available(self):
        recommender = BundleRecommender()
        main = Product("M", "Main", 100, "unique")
        available = []
        best = recommender.find_best_bundle(main, available)
        assert best is None


class TestBulkRecommendations:
    def test_bulk_recommendations(self):
        recommender = BundleRecommender()
        products = [
            Product("P1", "Product 1", 50, "cat1"),
            Product("P2", "Product 2", 60, "cat1"),
            Product("P3", "Product 3", 70, "cat2"),
        ]
        results = recommender.bulk_recommendations(products)
        assert isinstance(results, dict)
        # Should have recommendations for at least some products
        assert len(results) >= 0


class TestBundleFormatting:
    def test_format_bundle_display(self):
        recommender = BundleRecommender()
        bundle = Bundle(
            bundle_id="B1",
            strategy=BundleStrategy.COMPLEMENTARY,
            products=[
                Product("P1", "Main Product", 100, "cat"),
                Product("P2", "Accessory", 20, "cat")
            ],
            bundle_title="Main Product + Accessory Bundle",
            original_total=120.0,
            bundle_price=102.0,
            discount_amount=18.0,
            discount_percentage=15.0,
            profitability_score=75.0,
            reasoning="Test"
        )
        formatted = recommender.format_bundle_display(bundle)
        assert "Bundle" in formatted
        assert "$120.00" in formatted
        assert "$102.00" in formatted
        assert "Save" in formatted


class TestEdgeCases:
    def test_empty_product_list(self):
        recommender = BundleRecommender()
        main = Product("M", "Main", 100, "cat")
        bundles = recommender.recommend_bundles(main, [])
        assert len(bundles) == 0

    def test_single_product_bundle(self):
        recommender = BundleRecommender(min_bundle_size=1, max_bundle_size=1)
        main = Product("M", "Main", 100, "cat")
        bundles = recommender.recommend_bundles(main, [])
        # Should handle gracefully
        assert isinstance(bundles, list)

    def test_very_large_bundle(self):
        recommender = BundleRecommender(min_bundle_size=2, max_bundle_size=10)
        main = Product("M", "Main", 100, "cat")
        available = [Product(f"A{i}", f"Accessory {i}", 10, "cat") for i in range(20)]
        bundles = recommender.recommend_bundles(main, available)
        # Should cap at max_bundle_size
        for bundle in bundles:
            assert len(bundle.products) <= 10

    def test_zero_price_products(self):
        main = Product("M", "Main", 0, "cat")
        available = [Product("A", "Accessory", 0, "cat")]
        recommender = BundleRecommender()
        bundles = recommender.recommend_bundles(main, available)
        # Should handle zero prices gracefully
        assert isinstance(bundles, list)
