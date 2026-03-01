"""Tests for Conversion Copy Engine."""
import pytest
from app.conversion_copy import (
    TriggerCategory, TriggerScanner, TriggerMatch,
    PowerWordAnalyzer, PowerWordHit,
    BenefitExtractor, BenefitFeature,
    StructureAnalyzer, CTAGenerator,
    CopyStore, CopyScore, ConversionCopyEngine,
)


# =========================================================================
# TriggerScanner
# =========================================================================

class TestTriggerScanner:
    def setup_method(self):
        self.scanner = TriggerScanner()

    def test_urgency_limited_time(self):
        matches = self.scanner.scan("Limited time offer! Act now!")
        cats = {m.category for m in matches}
        assert TriggerCategory.URGENCY in cats

    def test_urgency_hurry(self):
        matches = self.scanner.scan("Hurry, don't wait!")
        assert any(m.category == TriggerCategory.URGENCY for m in matches)

    def test_scarcity_only_left(self):
        matches = self.scanner.scan("Only 5 left in stock!")
        assert any(m.category == TriggerCategory.SCARCITY for m in matches)

    def test_scarcity_limited_edition(self):
        matches = self.scanner.scan("Limited edition collectible")
        assert any(m.category == TriggerCategory.SCARCITY for m in matches)

    def test_social_proof_customers(self):
        matches = self.scanner.scan("Trusted by 10,000+ customers")
        assert any(m.category == TriggerCategory.SOCIAL_PROOF for m in matches)

    def test_social_proof_best_seller(self):
        matches = self.scanner.scan("Amazon best-seller in electronics")
        assert any(m.category == TriggerCategory.SOCIAL_PROOF for m in matches)

    def test_authority_fda(self):
        matches = self.scanner.scan("FDA-approved formula")
        assert any(m.category == TriggerCategory.AUTHORITY for m in matches)

    def test_authority_patented(self):
        matches = self.scanner.scan("Our patented technology")
        assert any(m.category == TriggerCategory.AUTHORITY for m in matches)

    def test_reciprocity_free_gift(self):
        matches = self.scanner.scan("Free gift with every purchase")
        assert any(m.category == TriggerCategory.RECIPROCITY for m in matches)

    def test_curiosity_secret(self):
        matches = self.scanner.scan("Discover the secret to perfect skin")
        assert any(m.category == TriggerCategory.CURIOSITY for m in matches)

    def test_fear_of_loss_dont_miss(self):
        matches = self.scanner.scan("Don't miss out! Money-back guarantee")
        cats = {m.category for m in matches}
        assert TriggerCategory.FEAR_OF_LOSS in cats

    def test_exclusivity_vip(self):
        matches = self.scanner.scan("VIP members only exclusive deal")
        cats = {m.category for m in matches}
        assert TriggerCategory.EXCLUSIVITY in cats

    def test_no_triggers(self):
        matches = self.scanner.scan("This is a regular product description.")
        assert len(matches) == 0

    def test_multiple_categories(self):
        text = "Limited time! Only 5 left! Trusted by 1000 customers. FDA-approved."
        matches = self.scanner.scan(text)
        cats = {m.category for m in matches}
        assert len(cats) >= 3

    def test_category_counts(self):
        text = "Hurry! Act now! Don't wait! Limited time!"
        counts = self.scanner.category_counts(text)
        assert counts.get("urgency", 0) >= 2

    def test_coverage_full(self):
        text = (
            "Limited time! Only 3 left! 5000 customers! FDA-approved! "
            "Free bonus! Discover secret! Don't miss! VIP exclusive!"
        )
        cov = self.scanner.coverage(text)
        assert cov > 0.5

    def test_coverage_empty(self):
        assert self.scanner.coverage("plain text here") == 0.0

    def test_custom_patterns(self):
        scanner = TriggerScanner(extra_patterns={
            TriggerCategory.URGENCY: [r"\bquick\b"]
        })
        matches = scanner.scan("Quick! Get it now!")
        assert any(m.category == TriggerCategory.URGENCY for m in matches)

    def test_match_position(self):
        matches = self.scanner.scan("Hello hurry up!")
        if matches:
            assert matches[0].position >= 0

    def test_deduplication(self):
        text = "Hurry hurry hurry!"
        matches = self.scanner.scan(text)
        positions = [m.position for m in matches]
        assert len(positions) == len(set(positions))


# =========================================================================
# PowerWordAnalyzer
# =========================================================================

class TestPowerWordAnalyzer:
    def setup_method(self):
        self.analyzer = PowerWordAnalyzer()

    def test_detect_free(self):
        hits = self.analyzer.analyze("Get your free sample today!")
        words = [h.word for h in hits]
        assert "free" in words

    def test_detect_multiple(self):
        hits = self.analyzer.analyze("Exclusive new proven results guaranteed")
        assert len(hits) >= 4

    def test_score_high_words(self):
        hits = self.analyzer.analyze("Free proven guaranteed results")
        for h in hits:
            if h.word in ("free", "proven", "guaranteed"):
                assert h.score >= 0.9

    def test_filler_detection(self):
        ratio = self.analyzer.filler_ratio("This is very very quite really good nice product")
        assert ratio > 0.0

    def test_density(self):
        density = self.analyzer.density("Free exclusive new proven amazing product")
        assert density > 0.3

    def test_weighted_score(self):
        score = self.analyzer.weighted_score("Free exclusive proven guaranteed")
        assert score > 0

    def test_empty_text(self):
        assert self.analyzer.analyze("") == []
        assert self.analyzer.density("") == 0.0
        assert self.analyzer.filler_ratio("") == 0.0

    def test_no_power_words(self):
        hits = self.analyzer.analyze("The cat sat on the mat")
        assert len(hits) == 0

    def test_custom_words(self):
        custom = PowerWordAnalyzer(custom_words={"superduper": 0.99})
        hits = custom.analyze("This is superduper!")
        assert any(h.word == "superduper" for h in hits)

    def test_count_tracking(self):
        hits = self.analyzer.analyze("Free free free samples")
        free_hit = next((h for h in hits if h.word == "free"), None)
        assert free_hit is not None
        assert free_hit.count == 3

    def test_positions_tracked(self):
        hits = self.analyzer.analyze("Free is great and free again")
        free_hit = next((h for h in hits if h.word == "free"), None)
        assert free_hit is not None
        assert len(free_hit.positions) == 2


# =========================================================================
# BenefitExtractor
# =========================================================================

class TestBenefitExtractor:
    def setup_method(self):
        self.extractor = BenefitExtractor()

    def test_classify_benefit(self):
        result = self.extractor.classify("You'll enjoy effortless cooking every night")
        assert result.is_benefit is True

    def test_classify_feature(self):
        result = self.extractor.classify("Made of stainless steel with 5L capacity")
        assert result.is_benefit is False

    def test_extract_mixed(self):
        text = (
            "Made of premium stainless steel. "
            "You'll enjoy cooking for years to come. "
            "Features a 5L capacity tank. "
            "Save hours every week with easy cleanup."
        )
        results = self.extractor.extract(text)
        benefits = [r for r in results if r.is_benefit]
        features = [r for r in results if not r.is_benefit]
        assert len(benefits) >= 1
        assert len(features) >= 1

    def test_ratio(self):
        text = "You'll love it. Save time. Made of steel. 5cm dimensions."
        ratio = self.extractor.ratio(text)
        assert ratio["total"] > 0
        assert ratio["benefits"] >= 0
        assert ratio["features"] >= 0

    def test_suggest_rewrites(self):
        text = "Made of aluminum alloy. Weighs 200g. Dimensions 10x5x3cm."
        suggestions = self.extractor.suggest_benefit_rewrites(text)
        assert len(suggestions) >= 1
        assert "tip" in suggestions[0]

    def test_empty_text(self):
        results = self.extractor.extract("")
        assert results == []

    def test_short_sentences_filtered(self):
        results = self.extractor.extract("Hi. Ok. Yes.")
        assert len(results) == 0  # too short

    def test_confidence(self):
        result = self.extractor.classify("You'll experience amazing results instantly")
        assert result.confidence > 0.0


# =========================================================================
# StructureAnalyzer
# =========================================================================

class TestStructureAnalyzer:
    def setup_method(self):
        self.analyzer = StructureAnalyzer()

    def test_bullet_detection(self):
        text = "- Feature one\n- Feature two\n- Feature three"
        info = self.analyzer.analyze(text)
        assert info["bullet_count"] == 3

    def test_cta_detection(self):
        text = "Buy now and save! Order today. Visit our store."
        info = self.analyzer.analyze(text)
        assert info["cta_count"] >= 2

    def test_question_detection(self):
        text = "Tired of messy cables? Want a cleaner desk?"
        info = self.analyzer.analyze(text)
        assert info["question_count"] == 2

    def test_word_count(self):
        text = "one two three four five"
        info = self.analyzer.analyze(text)
        assert info["word_count"] == 5

    def test_score_good_structure(self):
        text = (
            "• Premium quality material\n"
            "• Easy to install\n"
            "• Lifetime warranty\n\n"
            "Ready to upgrade your space?\n\n"
            "Buy now and transform your home!"
        )
        score = self.analyzer.score(text)
        assert score > 10

    def test_score_poor_structure(self):
        text = "a product thing it does stuff"
        score = self.analyzer.score(text)
        assert score < 15

    def test_has_flags(self):
        text = "• Bullet\nQuestion?\nBuy now!"
        info = self.analyzer.analyze(text)
        assert info["has_bullets"] is True
        assert info["has_cta"] is True
        assert info["has_questions"] is True


# =========================================================================
# CTAGenerator
# =========================================================================

class TestCTAGenerator:
    def setup_method(self):
        self.gen = CTAGenerator()

    def test_buy_ctas(self):
        ctas = self.gen.generate(style="buy", product="Widget Pro", benefit="save 50% today")
        assert len(ctas) > 0
        assert any("save 50% today" in c or "Cart" in c for c in ctas)

    def test_try_ctas(self):
        ctas = self.gen.generate(style="try", product="SkinCare Pro")
        assert len(ctas) > 0

    def test_learn_ctas(self):
        ctas = self.gen.generate(style="learn", product="SmartWatch X")
        assert len(ctas) > 0

    def test_platform_ctas(self):
        assert len(self.gen.best_for_platform("amazon")) >= 2
        assert len(self.gen.best_for_platform("shopee")) >= 2
        assert len(self.gen.best_for_platform("unknown")) >= 2


# =========================================================================
# CopyStore
# =========================================================================

class TestCopyStore:
    def setup_method(self):
        self.store = CopyStore(":memory:")

    def test_save_and_history(self):
        score = CopyScore(total=75.0, grade="B+")
        self.store.save("LST-001", "amazon", score)
        history = self.store.history("LST-001")
        assert len(history) == 1
        assert history[0]["total_score"] == 75.0

    def test_multiple_entries(self):
        for i in range(5):
            score = CopyScore(total=50.0 + i * 10, grade="C")
            self.store.save("LST-002", "shopee", score)
        history = self.store.history("LST-002")
        assert len(history) == 5

    def test_best_scores(self):
        self.store.save("A", "amazon", CopyScore(total=90, grade="A+"))
        self.store.save("B", "amazon", CopyScore(total=60, grade="B"))
        best = self.store.best_scores()
        assert best[0]["listing_id"] == "A"

    def test_avg_by_platform(self):
        self.store.save("X", "amazon", CopyScore(total=80, grade="A"))
        self.store.save("Y", "amazon", CopyScore(total=60, grade="B"))
        avgs = self.store.avg_score_by_platform()
        assert "amazon" in avgs
        assert avgs["amazon"] == 70.0

    def test_improvement_trend(self):
        self.store.save("Z", "ebay", CopyScore(total=40, grade="D"))
        self.store.save("Z", "ebay", CopyScore(total=70, grade="B+"))
        trend = self.store.improvement_trend("Z")
        assert len(trend) == 2
        assert trend[0]["total_score"] < trend[1]["total_score"]


# =========================================================================
# ConversionCopyEngine (Integration)
# =========================================================================

class TestConversionCopyEngine:
    def setup_method(self):
        self.engine = ConversionCopyEngine()

    def test_analyze_basic(self):
        text = "Buy this great product now. Free shipping!"
        score = self.engine.analyze(text)
        assert 0 <= score.total <= 100
        assert score.grade in ("A+", "A", "B+", "B", "C", "D", "F")

    def test_analyze_rich_copy(self):
        text = (
            "🔥 LIMITED TIME OFFER — Only 50 left in stock!\n\n"
            "Trusted by 10,000+ happy customers. FDA-approved formula.\n\n"
            "• You'll enjoy instant results — proven to work in 7 days\n"
            "• Save 2 hours every day with our exclusive technology\n"
            "• Free bonus gift with every order!\n"
            "• 100% money-back guarantee — nothing to lose\n\n"
            "Ready to transform your life?\n\n"
            "Buy now and discover the difference!"
        )
        score = self.engine.analyze(text)
        assert score.total > 40
        assert len(score.triggers_found) > 0
        assert len(score.power_words_found) > 0

    def test_analyze_poor_copy(self):
        text = "Product. Good quality. Nice."
        score = self.engine.analyze(text)
        assert score.total < 50

    def test_suggestions_generated(self):
        text = "This is a basic product with aluminum body."
        score = self.engine.analyze(text)
        assert len(score.suggestions) > 0

    def test_compare(self):
        texts = [
            "Amazing free exclusive product! Buy now!",
            "A product.",
        ]
        scores = self.engine.compare(texts)
        assert len(scores) == 2
        assert scores[0].total > scores[1].total

    def test_report(self):
        score = self.engine.analyze("Free proven exclusive product. Buy now! 5000+ customers love it.")
        report = self.engine.report(score)
        assert "CONVERSION COPY ANALYSIS" in report
        assert "Triggers" in report or "Power Words" in report or "Score" in report

    def test_persist_with_id(self):
        text = "Buy our exclusive product now!"
        score = self.engine.analyze(text, listing_id="TEST-001", platform="amazon")
        history = self.engine.store.history("TEST-001")
        assert len(history) == 1

    def test_to_dict(self):
        score = self.engine.analyze("Free product with guaranteed results!")
        d = score.to_dict()
        assert "total" in d
        assert "grade" in d
        assert "triggers_found" in d
        assert "suggestions" in d

    def test_empty_text(self):
        score = self.engine.analyze("")
        assert score.total >= 0
        assert score.grade in ("A+", "A", "B+", "B", "C", "D", "F")

    def test_trigger_match_to_dict(self):
        match = TriggerMatch(
            category=TriggerCategory.URGENCY,
            pattern=r"\bhurry\b",
            text_matched="hurry",
            position=5,
        )
        d = match.to_dict()
        assert d["category"] == "urgency"
        assert d["position"] == 5
