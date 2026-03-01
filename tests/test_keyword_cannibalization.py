"""Tests for keyword_cannibalization module."""

import pytest
from app.keyword_cannibalization import (
    KeywordCannibalizationDetector,
    ListingKeywords,
    CannibalizationPair,
    KeywordCluster,
    AllocationSuggestion,
    CannibalizationReport,
    STOP_WORDS,
)


@pytest.fixture
def detector():
    return KeywordCannibalizationDetector()


@pytest.fixture
def loaded_detector():
    d = KeywordCannibalizationDetector()
    d.add_listing(
        "L1",
        "Stainless Steel Water Bottle Insulated 32oz BPA Free",
        description="Double wall vacuum insulated stainless steel water bottle keeps drinks cold 24 hours",
        bullet_points=["BPA free materials", "Leak proof lid", "32oz capacity"],
    )
    d.add_listing(
        "L2",
        "Insulated Water Bottle Stainless Steel 24oz Sport",
        description="Vacuum insulated stainless steel sports water bottle for gym and outdoor",
        bullet_points=["BPA free", "Sport cap included", "24oz size"],
    )
    d.add_listing(
        "L3",
        "Bamboo Cutting Board Kitchen Set Large Premium",
        description="Premium organic bamboo cutting board set for kitchen with juice groove",
        bullet_points=["Eco-friendly bamboo", "Juice groove", "3 piece set"],
    )
    return d


class TestInit:
    def test_default_init(self, detector):
        assert detector.min_keyword_length == 3
        assert len(detector.listings) == 0
        assert detector.ngram_weight == 2.0

    def test_custom_stop_words(self):
        d = KeywordCannibalizationDetector(custom_stop_words={"custom", "words"})
        assert "custom" in d.stop_words
        assert "words" in d.stop_words
        assert "the" in d.stop_words  # default still present

    def test_custom_min_length(self):
        d = KeywordCannibalizationDetector(min_keyword_length=4)
        assert d.min_keyword_length == 4


class TestNormalize:
    def test_basic_normalize(self, detector):
        tokens = detector._normalize("Hello World Python Testing")
        assert "hello" in tokens
        assert "world" in tokens
        assert "python" in tokens

    def test_removes_stop_words(self, detector):
        tokens = detector._normalize("the cat and the dog")
        assert "the" not in tokens
        assert "and" not in tokens
        assert "cat" in tokens
        assert "dog" in tokens

    def test_removes_short_words(self, detector):
        tokens = detector._normalize("go to be or do it")
        # all 2-letter words should be removed (min_length=3)
        assert "go" not in tokens
        assert "to" not in tokens
        assert "be" not in tokens

    def test_removes_punctuation(self, detector):
        tokens = detector._normalize("hello, world! test-case (foo)")
        assert all("," not in t and "!" not in t for t in tokens)


class TestNgrams:
    def test_bigrams(self, detector):
        tokens = ["stainless", "steel", "water", "bottle"]
        bigrams = detector._extract_ngrams(tokens, 2)
        assert "stainless steel" in bigrams
        assert "steel water" in bigrams
        assert "water bottle" in bigrams
        assert len(bigrams) == 3

    def test_trigrams(self, detector):
        tokens = ["stainless", "steel", "water", "bottle"]
        trigrams = detector._extract_ngrams(tokens, 3)
        assert "stainless steel water" in trigrams
        assert len(trigrams) == 2

    def test_empty_tokens(self, detector):
        assert detector._extract_ngrams([], 2) == []

    def test_single_token(self, detector):
        assert detector._extract_ngrams(["hello"], 2) == []


class TestAddListing:
    def test_basic_add(self, detector):
        result = detector.add_listing("L1", "Stainless Steel Water Bottle 32oz")
        assert result.listing_id == "L1"
        assert "stainless" in result.keywords
        assert "steel" in result.keywords
        assert "water" in result.keywords
        assert "bottle" in result.keywords

    def test_stores_listing(self, detector):
        detector.add_listing("L1", "Test Product")
        assert "L1" in detector.listings

    def test_with_description(self, detector):
        result = detector.add_listing(
            "L1", "Water Bottle", description="Insulated vacuum flask"
        )
        assert "insulated" in result.keywords
        assert "vacuum" in result.keywords

    def test_with_bullets(self, detector):
        result = detector.add_listing(
            "L1", "Water Bottle",
            bullet_points=["BPA free", "Leak proof design"],
        )
        assert "leak" in result.keywords
        assert "proof" in result.keywords

    def test_with_backend_keywords(self, detector):
        result = detector.add_listing(
            "L1", "Water Bottle",
            backend_keywords=["thermos", "hydration"],
        )
        assert "thermos" in result.keywords
        assert "hydration" in result.keywords

    def test_primary_keywords(self, detector):
        result = detector.add_listing(
            "L1",
            "Stainless Steel Water Bottle Insulated",
            description="Stainless steel water bottle insulated vacuum",
        )
        assert len(result.primary_keywords) <= 5
        # Title keywords repeated 3x + description should rank high
        assert "stainless" in result.primary_keywords or "steel" in result.primary_keywords

    def test_to_dict(self, detector):
        result = detector.add_listing("L1", "Test Product")
        d = result.to_dict()
        assert "listing_id" in d
        assert "keywords" in d
        assert "primary_keywords" in d


class TestDetectPairs:
    def test_similar_listings_detected(self, loaded_detector):
        pairs = loaded_detector.detect_pairs(min_overlap=10)
        # L1 and L2 should be detected (both water bottles)
        bottle_pairs = [
            p for p in pairs
            if (p.listing_a_id in ["L1", "L2"] and p.listing_b_id in ["L1", "L2"])
        ]
        assert len(bottle_pairs) >= 1
        assert bottle_pairs[0].overlap_score > 10

    def test_dissimilar_not_paired(self, loaded_detector):
        pairs = loaded_detector.detect_pairs(min_overlap=50)
        # L1/L2 (water bottles) vs L3 (cutting board) should NOT be high overlap
        cross_pairs = [
            p for p in pairs
            if "L3" in [p.listing_a_id, p.listing_b_id]
        ]
        assert len(cross_pairs) == 0

    def test_severity_assigned(self, loaded_detector):
        pairs = loaded_detector.detect_pairs(min_overlap=5)
        for p in pairs:
            assert p.severity in ["low", "medium", "high", "critical"]

    def test_recommendations_present(self, loaded_detector):
        pairs = loaded_detector.detect_pairs(min_overlap=5)
        for p in pairs:
            assert len(p.recommendation) > 0

    def test_sorted_by_score(self, loaded_detector):
        pairs = loaded_detector.detect_pairs(min_overlap=5)
        scores = [p.overlap_score for p in pairs]
        assert scores == sorted(scores, reverse=True)

    def test_empty_detector(self, detector):
        pairs = detector.detect_pairs()
        assert pairs == []

    def test_single_listing(self, detector):
        detector.add_listing("L1", "Test Product")
        pairs = detector.detect_pairs()
        assert pairs == []


class TestKeywordClusters:
    def test_finds_shared_keywords(self, loaded_detector):
        clusters = loaded_detector.keyword_clusters(min_listings=2)
        # "water", "bottle", "stainless", "steel", "insulated" shared by L1 & L2
        shared_kws = {c.keyword for c in clusters}
        assert "water" in shared_kws or "bottle" in shared_kws or "stainless" in shared_kws

    def test_cluster_has_listing_ids(self, loaded_detector):
        clusters = loaded_detector.keyword_clusters(min_listings=2)
        for c in clusters:
            assert len(c.listing_ids) >= 2
            assert c.is_cannibalized is True

    def test_sorted_by_frequency(self, loaded_detector):
        clusters = loaded_detector.keyword_clusters(min_listings=2)
        freqs = [c.total_frequency for c in clusters]
        assert freqs == sorted(freqs, reverse=True)

    def test_no_clusters_for_unique_listings(self, detector):
        detector.add_listing("L1", "Apple iPhone Case")
        detector.add_listing("L2", "Bamboo Cutting Board")
        clusters = detector.keyword_clusters(min_listings=2)
        # Should have few or no shared unigrams
        shared_meaningful = [c for c in clusters if c.keyword not in STOP_WORDS]
        # May still share some short words, but not many
        assert len(shared_meaningful) < 5


class TestSuggestAllocation:
    def test_suggestions_generated(self, loaded_detector):
        suggestions = loaded_detector.suggest_allocation()
        assert len(suggestions) > 0

    def test_suggestion_has_assigned_listing(self, loaded_detector):
        suggestions = loaded_detector.suggest_allocation()
        for s in suggestions:
            assert s.assigned_listing_id in ["L1", "L2", "L3"]
            assert len(s.keyword) > 0

    def test_competing_listings_listed(self, loaded_detector):
        suggestions = loaded_detector.suggest_allocation()
        for s in suggestions:
            assert s.assigned_listing_id not in s.competing_listings

    def test_to_dict(self, loaded_detector):
        suggestions = loaded_detector.suggest_allocation()
        if suggestions:
            d = suggestions[0].to_dict()
            assert "keyword" in d
            assert "assigned_listing_id" in d


class TestFullReport:
    def test_report_generated(self, loaded_detector):
        report = loaded_detector.full_report()
        assert report.total_listings == 3
        assert report.total_keywords_analyzed > 0
        assert report.risk_level in ["low", "medium", "high", "critical"]

    def test_report_summary(self, loaded_detector):
        report = loaded_detector.full_report()
        assert "listings" in report.summary.lower()
        assert "keywords" in report.summary.lower()

    def test_report_to_dict(self, loaded_detector):
        report = loaded_detector.full_report()
        d = report.to_dict()
        assert "total_listings" in d
        assert "cannibalization_pairs" in d
        assert "overall_score" in d

    def test_empty_report(self, detector):
        report = detector.full_report()
        assert report.total_listings == 0
        assert report.overall_score == 0

    def test_high_cannibalization_score(self):
        d = KeywordCannibalizationDetector()
        # Add very similar listings
        for i in range(5):
            d.add_listing(
                f"L{i}",
                f"Stainless Steel Water Bottle Insulated {i}",
                description="Double wall vacuum insulated stainless steel water bottle",
            )
        report = d.full_report(min_overlap=5)
        assert report.overall_score > 20
        assert report.cannibalized_keywords > 0


class TestCompareTwo:
    def test_compare_existing(self, loaded_detector):
        pair = loaded_detector.compare_two("L1", "L2")
        assert pair is not None
        assert pair.overlap_score > 0
        assert len(pair.shared_keywords) > 0

    def test_compare_nonexistent(self, loaded_detector):
        result = loaded_detector.compare_two("L1", "NONEXISTENT")
        assert result is None

    def test_compare_dissimilar(self, loaded_detector):
        pair = loaded_detector.compare_two("L1", "L3")
        assert pair is not None
        # Water bottle vs cutting board — low overlap
        assert pair.overlap_score < 30

    def test_compare_self_nonexistent(self, detector):
        result = detector.compare_two("X", "Y")
        assert result is None


class TestStopWords:
    def test_stop_words_set(self):
        assert "the" in STOP_WORDS
        assert "and" in STOP_WORDS
        assert "for" in STOP_WORDS

    def test_marketplace_stop_words(self):
        assert "pack" in STOP_WORDS
        assert "pcs" in STOP_WORDS
        assert "piece" in STOP_WORDS
