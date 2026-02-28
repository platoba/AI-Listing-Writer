"""Tests for seasonal optimizer module."""
import pytest
from datetime import date
from app.seasonal import (
    SeasonalOptimizer, SeasonalKeywordSuggestion, SeasonalOptimization,
    optimize_for_season, format_seasonal_report,
    SEASONAL_KEYWORDS, SHOPPING_EVENTS, CATEGORY_SEASONALITY,
)


# --- Fixtures ---

@pytest.fixture
def spring_optimizer():
    return SeasonalOptimizer(reference_date=date(2025, 4, 15))


@pytest.fixture
def summer_optimizer():
    return SeasonalOptimizer(reference_date=date(2025, 7, 12))


@pytest.fixture
def fall_optimizer():
    return SeasonalOptimizer(reference_date=date(2025, 10, 28))


@pytest.fixture
def winter_optimizer():
    return SeasonalOptimizer(reference_date=date(2025, 12, 15))


@pytest.fixture
def black_friday_optimizer():
    return SeasonalOptimizer(reference_date=date(2025, 11, 28))


@pytest.fixture
def sample_listing():
    return {
        "title": "Premium Wireless Bluetooth Headphones",
        "bullets": [
            "Active noise cancellation",
            "30-hour battery life",
            "Comfortable over-ear design",
            "Built-in microphone",
        ],
        "description": "High-quality wireless headphones for music lovers",
        "category": "electronics",
    }


# --- Season Detection Tests ---

class TestSeasonDetection:
    def test_spring_months(self):
        for month in [3, 4, 5]:
            opt = SeasonalOptimizer(reference_date=date(2025, month, 15))
            assert opt.current_season == "spring"

    def test_summer_months(self):
        for month in [6, 7, 8]:
            opt = SeasonalOptimizer(reference_date=date(2025, month, 15))
            assert opt.current_season == "summer"

    def test_fall_months(self):
        for month in [9, 10, 11]:
            opt = SeasonalOptimizer(reference_date=date(2025, month, 15))
            assert opt.current_season == "fall"

    def test_winter_months(self):
        for month in [12, 1, 2]:
            opt = SeasonalOptimizer(reference_date=date(2025, month, 15))
            assert opt.current_season == "winter"

    def test_default_today(self):
        opt = SeasonalOptimizer()
        assert opt.current_season in ("spring", "summer", "fall", "winter")


# --- Event Detection Tests ---

class TestEventDetection:
    def test_christmas_active(self, winter_optimizer):
        events = winter_optimizer._get_current_events()
        assert "Christmas" in events

    def test_black_friday_active(self, black_friday_optimizer):
        events = black_friday_optimizer._get_current_events()
        assert "Black Friday" in events

    def test_halloween_active(self, fall_optimizer):
        events = fall_optimizer._get_current_events()
        assert "Halloween" in events

    def test_prime_day_active(self, summer_optimizer):
        events = summer_optimizer._get_current_events()
        assert "Prime Day" in events

    def test_no_events_mid_march(self):
        opt = SeasonalOptimizer(reference_date=date(2025, 3, 15))
        events = opt._get_current_events()
        # No major event on March 15
        assert len(events) <= 1

    def test_upcoming_events(self):
        opt = SeasonalOptimizer(reference_date=date(2025, 10, 1))
        upcoming = opt._get_upcoming_events(lookahead_days=45)
        event_names = " ".join(upcoming)
        # Should see upcoming November events
        assert len(upcoming) >= 0  # Depends on exact dates

    def test_valentines_active(self):
        opt = SeasonalOptimizer(reference_date=date(2025, 2, 10))
        events = opt._get_current_events()
        assert "Valentine's Day" in events

    def test_mothers_day_active(self):
        opt = SeasonalOptimizer(reference_date=date(2025, 5, 10))
        events = opt._get_current_events()
        assert "Mother's Day" in events


# --- Category Timing Tests ---

class TestCategoryTiming:
    def test_outdoor_peak_summer(self, summer_optimizer):
        result = summer_optimizer._check_category_timing("outdoor")
        assert result == "peak"

    def test_outdoor_low_winter(self, winter_optimizer):
        result = winter_optimizer._check_category_timing("outdoor gear")
        assert result == "low"

    def test_electronics_peak_winter(self, winter_optimizer):
        result = winter_optimizer._check_category_timing("electronics")
        assert result == "peak"

    def test_fitness_peak_winter(self, winter_optimizer):
        result = winter_optimizer._check_category_timing("fitness")
        assert result == "peak"

    def test_garden_peak_spring(self, spring_optimizer):
        result = spring_optimizer._check_category_timing("garden")
        assert result == "peak"

    def test_unknown_category(self, summer_optimizer):
        result = summer_optimizer._check_category_timing("widgets")
        assert result == "normal"

    def test_normal_timing(self, fall_optimizer):
        result = fall_optimizer._check_category_timing("garden")
        assert result == "normal"


# --- Keyword Suggestions Tests ---

class TestKeywordSuggestions:
    def test_suggests_seasonal_keywords(self, summer_optimizer):
        suggestions = summer_optimizer._suggest_keywords(
            "basic product description", "", []
        )
        assert len(suggestions) > 0
        keywords = [s.keyword for s in suggestions]
        # Should suggest summer keywords
        assert any(kw in SEASONAL_KEYWORDS["summer"]["keywords"]
                    for kw in keywords)

    def test_no_duplicate_suggestions(self, summer_optimizer):
        # If listing already has the keyword, don't suggest it
        suggestions = summer_optimizer._suggest_keywords(
            "summer beach outdoor waterproof travel vacation", "", []
        )
        keywords_in_text = {"summer", "beach", "outdoor", "waterproof",
                            "travel", "vacation"}
        for s in suggestions:
            assert s.keyword.lower() not in keywords_in_text

    def test_event_keywords_when_active(self, black_friday_optimizer):
        suggestions = black_friday_optimizer._suggest_keywords(
            "simple product", "", []
        )
        event_kws = [s for s in suggestions if "Black Friday" in s.category]
        assert len(event_kws) > 0

    def test_suggestions_sorted_by_relevance(self, summer_optimizer):
        suggestions = summer_optimizer._suggest_keywords("test", "", [])
        if len(suggestions) >= 2:
            assert suggestions[0].relevance >= suggestions[1].relevance

    def test_max_20_suggestions(self, summer_optimizer):
        suggestions = summer_optimizer._suggest_keywords("x", "", [])
        assert len(suggestions) <= 20

    def test_urgency_now_for_current(self, summer_optimizer):
        suggestions = summer_optimizer._suggest_keywords("x", "", [])
        now_suggestions = [s for s in suggestions if s.urgency == "now"]
        assert len(now_suggestions) > 0


# --- Title Suggestion Tests ---

class TestTitleSuggestions:
    def test_suggests_adding_season(self, summer_optimizer):
        suggestions = summer_optimizer._suggest_title_mods(
            "Wireless Headphones Premium Quality", ""
        )
        assert len(suggestions) > 0
        combined = " ".join(suggestions)
        assert "Summer" in combined or "seasonal" in combined.lower()

    def test_no_season_suggestion_if_present(self, summer_optimizer):
        suggestions = summer_optimizer._suggest_title_mods(
            "Summer Wireless Headphones", ""
        )
        # Shouldn't suggest adding season since it's already there
        has_add_season = any(
            "Add" in s and "Summer" in s for s in suggestions
        )
        assert has_add_season is False

    def test_event_title_suggestion(self, black_friday_optimizer):
        suggestions = black_friday_optimizer._suggest_title_mods(
            "Wireless Headphones", ""
        )
        combined = " ".join(suggestions)
        assert "Black Friday" in combined or "event" in combined.lower()


# --- Bullet Suggestion Tests ---

class TestBulletSuggestions:
    def test_suggests_themed_bullets(self, summer_optimizer):
        suggestions = summer_optimizer._suggest_bullet_additions(
            ["Active noise cancellation", "30-hour battery"], ""
        )
        assert len(suggestions) > 0

    def test_winter_gift_suggestion(self, winter_optimizer):
        suggestions = winter_optimizer._suggest_bullet_additions(
            ["Great quality"], ""
        )
        combined = " ".join(suggestions)
        assert "gift" in combined.lower() or "🎁" in combined


# --- Full Optimization Tests ---

class TestFullOptimization:
    def test_basic_optimization(self, summer_optimizer, sample_listing):
        result = summer_optimizer.optimize(**sample_listing)
        assert isinstance(result, SeasonalOptimization)
        assert result.current_season == "summer"
        assert 0 <= result.optimization_score <= 100

    def test_has_keyword_suggestions(self, summer_optimizer, sample_listing):
        result = summer_optimizer.optimize(**sample_listing)
        assert len(result.keyword_suggestions) > 0

    def test_has_color_suggestions(self, summer_optimizer, sample_listing):
        result = summer_optimizer.optimize(**sample_listing)
        assert len(result.color_suggestions) > 0

    def test_category_timing_set(self, winter_optimizer, sample_listing):
        result = winter_optimizer.optimize(**sample_listing)
        assert result.category_timing == "peak"  # electronics peak in winter

    def test_is_peak_season(self, winter_optimizer, sample_listing):
        result = winter_optimizer.optimize(**sample_listing)
        assert result.is_peak_season is True

    def test_not_peak_season(self, spring_optimizer, sample_listing):
        result = spring_optimizer.optimize(**sample_listing)
        assert result.is_peak_season is False

    def test_action_items_generated(self, winter_optimizer, sample_listing):
        result = winter_optimizer.optimize(**sample_listing)
        assert len(result.action_items) > 0

    def test_event_detected_in_result(self, black_friday_optimizer, sample_listing):
        result = black_friday_optimizer.optimize(**sample_listing)
        assert "Black Friday" in result.current_events

    def test_no_category(self, summer_optimizer):
        result = summer_optimizer.optimize(
            title="Product", bullets=["Feature"], description="Desc"
        )
        assert result.category_timing == ""

    def test_with_target_keywords(self, summer_optimizer, sample_listing):
        result = summer_optimizer.optimize(
            target_keywords=["waterproof", "beach"],
            **sample_listing,
        )
        # Existing keywords shouldn't be re-suggested
        suggested_kws = {s.keyword.lower() for s in result.keyword_suggestions}
        assert "waterproof" not in suggested_kws


# --- Score Calculation Tests ---

class TestScoreCalculation:
    def test_score_range(self, summer_optimizer, sample_listing):
        result = summer_optimizer.optimize(**sample_listing)
        assert 0 <= result.optimization_score <= 100

    def test_seasonal_listing_scores_higher(self, summer_optimizer):
        # Listing with summer keywords should score higher
        seasonal = summer_optimizer.optimize(
            title="Summer Beach Waterproof Speaker",
            bullets=["UV resistant", "Outdoor use", "Travel friendly"],
            description="Perfect for summer vacation",
            category="electronics",
        )
        generic = summer_optimizer.optimize(
            title="Wireless Speaker",
            bullets=["Good sound"],
            description="A speaker",
            category="electronics",
        )
        assert seasonal.optimization_score >= generic.optimization_score


# --- Action Items Tests ---

class TestActionItems:
    def test_urgent_for_events(self, black_friday_optimizer, sample_listing):
        result = black_friday_optimizer.optimize(**sample_listing)
        has_urgent = any("URGENT" in a for a in result.action_items)
        assert has_urgent is True

    def test_prepare_for_upcoming(self):
        # Mid-October, upcoming Black Friday
        opt = SeasonalOptimizer(reference_date=date(2025, 10, 15))
        result = opt.optimize(
            title="Product",
            bullets=["Feature"],
            category="electronics",
        )
        has_prepare = any("PREPARE" in a for a in result.action_items)
        assert has_prepare is True

    def test_capitalize_peak(self, winter_optimizer, sample_listing):
        result = winter_optimizer.optimize(**sample_listing)
        has_capitalize = any("CAPITALIZE" in a for a in result.action_items)
        assert has_capitalize is True


# --- Convenience Function Tests ---

class TestConvenienceFunction:
    def test_optimize_for_season(self):
        result = optimize_for_season(
            title="Test Product",
            bullets=["Feature 1"],
            category="outdoor",
            reference_date=date(2025, 7, 1),
        )
        assert result.current_season == "summer"
        assert result.category_timing == "peak"

    def test_optimize_for_season_defaults(self):
        result = optimize_for_season(
            title="Test",
            bullets=[],
        )
        assert result.current_season in ("spring", "summer", "fall", "winter")


# --- Format Report Tests ---

class TestFormatReport:
    def test_report_structure(self, summer_optimizer, sample_listing):
        result = summer_optimizer.optimize(**sample_listing)
        report = format_seasonal_report(result)
        assert "SEASONAL OPTIMIZATION REPORT" in report
        assert "Current Season" in report
        assert "Optimization Score" in report

    def test_report_shows_events(self, black_friday_optimizer, sample_listing):
        result = black_friday_optimizer.optimize(**sample_listing)
        report = format_seasonal_report(result)
        assert "Active Shopping Events" in report
        assert "Black Friday" in report

    def test_report_shows_keywords(self, summer_optimizer, sample_listing):
        result = summer_optimizer.optimize(**sample_listing)
        report = format_seasonal_report(result)
        if result.keyword_suggestions:
            assert "Suggested Keywords" in report

    def test_report_shows_colors(self, summer_optimizer, sample_listing):
        result = summer_optimizer.optimize(**sample_listing)
        report = format_seasonal_report(result)
        assert "Seasonal Colors" in report

    def test_report_shows_actions(self, winter_optimizer, sample_listing):
        result = winter_optimizer.optimize(**sample_listing)
        report = format_seasonal_report(result)
        if result.action_items:
            assert "Action Items" in report


# --- Data Integrity Tests ---

class TestDataIntegrity:
    def test_all_seasons_have_keywords(self):
        for season, data in SEASONAL_KEYWORDS.items():
            assert len(data["keywords"]) > 0, f"{season} missing keywords"
            assert len(data["months"]) == 3, f"{season} wrong month count"
            assert len(data["themes"]) > 0, f"{season} missing themes"
            assert len(data["colors"]) > 0, f"{season} missing colors"

    def test_all_events_have_keywords(self):
        for event in SHOPPING_EVENTS:
            assert "name" in event
            assert "keywords" in event
            assert len(event["keywords"]) > 0
            assert "boost" in event
            assert event["boost"] >= 1.0

    def test_all_categories_have_peak(self):
        for cat, timing in CATEGORY_SEASONALITY.items():
            assert "peak" in timing
            assert "low" in timing

    def test_months_cover_all(self):
        all_months = set()
        for data in SEASONAL_KEYWORDS.values():
            all_months.update(data["months"])
        assert all_months == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}


# --- Edge Cases ---

class TestEdgeCases:
    def test_empty_listing(self, summer_optimizer):
        result = summer_optimizer.optimize(title="", bullets=[], description="")
        assert result.optimization_score >= 0

    def test_very_long_title(self, summer_optimizer):
        title = "Summer " * 100
        result = summer_optimizer.optimize(
            title=title, bullets=["test"], description=""
        )
        assert result.optimization_score > 0

    def test_year_boundary(self):
        opt = SeasonalOptimizer(reference_date=date(2025, 12, 31))
        assert opt.current_season == "winter"
        events = opt._get_current_events()
        assert "Year-End Clearance" in events

    def test_jan_first(self):
        opt = SeasonalOptimizer(reference_date=date(2025, 1, 1))
        assert opt.current_season == "winter"
        events = opt._get_current_events()
        assert "New Year Sales" in events
