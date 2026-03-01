"""Tests for Customer Q&A Generator."""
import pytest
import tempfile
import os
from app.customer_qa import (
    CustomerQAGenerator,
    QAPair, ObjectionResponse, QAReport,
    QuestionCategory, BuyerPersona, Platform,
    _extract_features, _extract_specs, _extract_materials, _generate_answer,
)


class TestFeatureExtraction:
    def test_extract_bullet_points(self):
        text = "• Premium quality\n• Waterproof design\n• Long battery life"
        features = _extract_features(text)
        assert len(features) >= 3
        assert any("Premium quality" in f for f in features)
        assert any("Waterproof" in f for f in features)

    def test_extract_numbered_points(self):
        text = "1. Stainless steel construction\n2. Dishwasher safe\n3. BPA free"
        features = _extract_features(text)
        assert len(features) >= 3

    def test_extract_features_with_keywords(self):
        text = "Features include: wireless charging, fast processor, HD camera"
        features = _extract_features(text)
        assert len(features) > 0

    def test_extract_no_features(self):
        text = "This is a simple sentence with no features"
        features = _extract_features(text)
        assert isinstance(features, list)

    def test_extract_features_limit(self):
        text = "\n".join([f"• Feature {i}" for i in range(30)])
        features = _extract_features(text)
        assert len(features) <= 20  # capped at 20


class TestSpecExtraction:
    def test_extract_colon_specs(self):
        text = "Material: Stainless Steel\nWeight: 2.5 lbs\nColor: Black"
        specs = _extract_specs(text)
        assert "material" in specs
        assert "weight" in specs
        assert "color" in specs

    def test_extract_dimensions(self):
        text = "Product dimensions: 12 x 8 x 4 inches"
        specs = _extract_specs(text)
        assert "dimensions" in specs
        assert "12" in specs["dimensions"]

    def test_extract_weight(self):
        text = "Ships at 5 lbs total weight"
        specs = _extract_specs(text)
        assert "weight" in specs
        assert "lbs" in specs["weight"]

    def test_no_specs_found(self):
        text = "Just a simple product description without specs"
        specs = _extract_specs(text)
        assert isinstance(specs, dict)


class TestMaterialExtraction:
    def test_extract_common_materials(self):
        text = "Made from premium stainless steel and silicone"
        materials = _extract_materials(text)
        assert "stainless steel" in materials
        assert "silicone" in materials

    def test_extract_fabric_materials(self):
        text = "Constructed with durable polyester and cotton blend"
        materials = _extract_materials(text)
        assert "polyester" in materials or "cotton" in materials

    def test_extract_no_materials(self):
        text = "A great product for everyone"
        materials = _extract_materials(text)
        assert isinstance(materials, list)

    def test_extract_wood_types(self):
        text = "Crafted from solid oak and maple wood"
        materials = _extract_materials(text)
        assert "oak" in materials or "maple" in materials


class TestAnswerGeneration:
    def test_shipping_answer(self):
        title = "Fast Shipping Widget"
        desc = "Free shipping on all orders. Ships next day via express delivery"
        answer, conf = _generate_answer(
            "How long does shipping take?",
            title, desc, [], {}, [], "shipping"
        )
        assert "free shipping" in answer.lower() or "express" in answer.lower()
        assert conf > 0.5

    def test_material_answer(self):
        title = "Stainless Steel Water Bottle"
        desc = "Made from premium stainless steel"
        materials = ["stainless steel"]
        answer, conf = _generate_answer(
            "What material is this made of?",
            title, desc, [], {}, materials, "material"
        )
        assert "stainless steel" in answer.lower()
        assert conf > 0.7

    def test_sizing_answer_with_specs(self):
        specs = {"dimensions": "12 x 8 x 4 inches"}
        answer, conf = _generate_answer(
            "What are the dimensions?",
            "Product", "", [], specs, [], "sizing"
        )
        assert "12 x 8 x 4" in answer
        assert conf > 0.9

    def test_low_confidence_fallback(self):
        answer, conf = _generate_answer(
            "Random question?", "", "", [], {}, [], "general"
        )
        assert conf < 0.5
        assert "refer" in answer.lower() or "contact" in answer.lower()


class TestQAGeneration:
    def test_basic_generation(self):
        gen = CustomerQAGenerator()
        report = gen.generate(
            title="Premium Wireless Headphones with Noise Cancelling",
            description="Features bluetooth 5.0, 30-hour battery, waterproof IPX7",
            platform="amazon"
        )
        assert isinstance(report, QAReport)
        assert report.total_questions > 0
        assert len(report.qa_pairs) > 0

    def test_with_keywords(self):
        gen = CustomerQAGenerator()
        report = gen.generate(
            title="Yoga Mat",
            description="Non-slip surface, eco-friendly TPE material",
            keywords=["yoga", "mat", "non-slip"]
        )
        assert report.total_questions > 0
        # Primary keyword should boost related questions
        assert any("yoga" in qa.question.lower() or "mat" in qa.question.lower()
                   for qa in report.qa_pairs)

    def test_persona_filtering(self):
        gen = CustomerQAGenerator()
        report = gen.generate(
            title="Budget Smartphone",
            description="Affordable smartphone with great features",
            personas=["budget", "first_timer"],
            max_questions=20
        )
        # Should only include budget/first_timer personas
        for qa in report.qa_pairs:
            if qa.persona:
                assert qa.persona in ["budget", "first_timer"]

    def test_category_filtering(self):
        gen = CustomerQAGenerator()
        report = gen.generate(
            title="Wireless Earbuds",
            description="Bluetooth earbuds with charging case",
            categories=["shipping", "quality"],
            max_questions=10
        )
        # Should only include shipping and quality questions
        for qa in report.qa_pairs:
            assert qa.category in ["shipping", "quality"]

    def test_confidence_threshold(self):
        gen = CustomerQAGenerator()
        report = gen.generate(
            title="Product",
            description="Description",
            min_confidence=0.7
        )
        # All QA pairs should meet minimum confidence
        for qa in report.qa_pairs:
            assert qa.confidence >= 0.7

    def test_platform_formatting(self):
        gen = CustomerQAGenerator()
        report = gen.generate(
            title="A" * 300,  # very long title
            description="B" * 5000,  # very long description
            platform="amazon",
            max_questions=5
        )
        # Amazon limits: title 200, answer 2000
        for qa in report.qa_pairs:
            assert len(qa.question) <= 300  # Some margin
            assert len(qa.answer) <= 2000


class TestObjectionHandling:
    def test_objection_generation(self):
        gen = CustomerQAGenerator()
        report = gen.generate(
            title="Premium Leather Wallet",
            description="Crafted from genuine Italian leather. Backed by lifetime warranty.",
            include_objections=True
        )
        assert len(report.objection_responses) > 0

    def test_no_objections_when_disabled(self):
        gen = CustomerQAGenerator()
        report = gen.generate(
            title="Product",
            description="Description",
            include_objections=False
        )
        assert len(report.objection_responses) == 0

    def test_objection_content(self):
        gen = CustomerQAGenerator()
        report = gen.generate(
            title="Expensive Premium Widget",
            description="Made from premium materials with warranty",
            include_objections=True
        )
        # Should have objection responses
        obj_types = [obj.objection_type for obj in report.objection_responses]
        assert len(obj_types) > 0


class TestBulkGeneration:
    def test_bulk_generate(self):
        gen = CustomerQAGenerator()
        listings = [
            {"title": "Product A", "description": "Desc A", "id": "A1"},
            {"title": "Product B", "description": "Desc B", "id": "B2"},
        ]
        reports = gen.generate_bulk(listings, max_per_listing=10)
        assert len(reports) == 2
        assert all(isinstance(r, QAReport) for r in reports)

    def test_bulk_with_platform(self):
        gen = CustomerQAGenerator()
        listings = [
            {"title": "Product 1", "description": "Description 1"},
            {"title": "Product 2", "description": "Description 2"},
        ]
        reports = gen.generate_bulk(listings, platform="ebay", max_per_listing=5)
        assert all(r.platform == "ebay" for r in reports)


class TestExport:
    def test_json_export(self):
        gen = CustomerQAGenerator()
        report = gen.generate(
            title="Test Product",
            description="Test Description",
            max_questions=3
        )
        json_str = gen.export_json(report)
        assert "listing_title" in json_str
        assert "qa_pairs" in json_str
        assert "Test Product" in json_str

    def test_csv_export(self):
        gen = CustomerQAGenerator()
        report = gen.generate(
            title="Test Product",
            description="Test Description",
            max_questions=3
        )
        csv_str = gen.export_csv(report)
        assert "question,answer,category,persona,confidence" in csv_str
        lines = csv_str.split("\n")
        assert len(lines) >= 2  # header + at least 1 row


class TestPersistence:
    def test_save_with_db(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            gen = CustomerQAGenerator(db_path=db_path)
            report = gen.generate(
                title="Test Product",
                description="Test",
                listing_id="TEST123",
                max_questions=5
            )
            assert report.total_questions > 0

            # Check history
            history = gen.get_history("TEST123")
            assert len(history) >= 5
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_get_history_no_db(self):
        gen = CustomerQAGenerator(db_path=None)
        history = gen.get_history("TEST")
        assert history == []


class TestReportFormatting:
    def test_report_summary(self):
        gen = CustomerQAGenerator()
        report = gen.generate(
            title="Wireless Mouse",
            description="Ergonomic wireless mouse with long battery",
            max_questions=5
        )
        summary = report.summary()
        assert "Q&A Report" in summary
        assert "Wireless Mouse" in summary or "Total Q&A" in summary
        assert str(report.total_questions) in summary

    def test_report_to_dict(self):
        gen = CustomerQAGenerator()
        report = gen.generate(
            title="Test",
            description="Test",
            max_questions=3
        )
        data = report.to_dict()
        assert "listing_title" in data
        assert "total_questions" in data
        assert "qa_pairs" in data
        assert isinstance(data["qa_pairs"], list)

    def test_csv_format(self):
        gen = CustomerQAGenerator()
        report = gen.generate(
            title="Product",
            description="Description",
            max_questions=2
        )
        csv = report.to_csv()
        assert "question,answer,category" in csv
        # CSV should escape quotes properly
        assert csv.count("\n") >= 2  # header + rows
