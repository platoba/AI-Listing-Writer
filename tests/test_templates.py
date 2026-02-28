"""Tests for category template engine."""
import pytest
from app.templates import (
    Category, TemplateEngine, CategoryTemplate,
    PowerWords, CATEGORY_TEMPLATES,
)


class TestCategory:
    def test_all_categories_defined(self):
        """All Category enum values have templates."""
        for cat in Category:
            assert cat in CATEGORY_TEMPLATES, f"Missing template for {cat}"

    def test_category_values(self):
        assert Category.ELECTRONICS.value == "electronics"
        assert Category.FASHION.value == "fashion"
        assert Category.BABY.value == "baby"
        assert Category.HEALTH.value == "health"

    def test_twelve_categories(self):
        assert len(Category) == 12


class TestPowerWords:
    def test_power_words_not_empty(self):
        """Every category has power words in all 5 types."""
        for cat, tmpl in CATEGORY_TEMPLATES.items():
            pw = tmpl.power_words
            assert len(pw.urgency) > 0, f"{cat}: no urgency words"
            assert len(pw.trust) > 0, f"{cat}: no trust words"
            assert len(pw.value) > 0, f"{cat}: no value words"
            assert len(pw.emotion) > 0, f"{cat}: no emotion words"
            assert len(pw.technical) > 0, f"{cat}: no technical words"

    def test_no_duplicate_words_within_type(self):
        for cat, tmpl in CATEGORY_TEMPLATES.items():
            pw = tmpl.power_words
            for attr in ["urgency", "trust", "value", "emotion", "technical"]:
                words = getattr(pw, attr)
                assert len(words) == len(set(words)), \
                    f"{cat}.{attr} has duplicates"

    def test_electronics_has_tech_specs(self):
        pw = CATEGORY_TEMPLATES[Category.ELECTRONICS].power_words
        tech = " ".join(pw.technical).lower()
        assert "usb" in tech or "bluetooth" in tech or "wifi" in tech

    def test_beauty_has_ingredients(self):
        pw = CATEGORY_TEMPLATES[Category.BEAUTY].power_words
        tech = " ".join(pw.technical).lower()
        assert "retinol" in tech or "hyaluronic" in tech


class TestCategoryTemplate:
    def test_all_templates_have_required_fields(self):
        for cat, tmpl in CATEGORY_TEMPLATES.items():
            assert tmpl.name, f"{cat}: missing name"
            assert tmpl.description, f"{cat}: missing description"
            assert len(tmpl.title_patterns) >= 2, f"{cat}: need ≥2 title patterns"
            assert len(tmpl.bullet_patterns) >= 3, f"{cat}: need ≥3 bullet patterns"
            assert len(tmpl.description_structure) >= 4, f"{cat}: need ≥4 desc sections"
            assert len(tmpl.seo_keywords_hints) >= 3, f"{cat}: need ≥3 SEO hints"
            assert len(tmpl.avoid_words) >= 1, f"{cat}: need ≥1 avoid word"
            assert len(tmpl.emoji_palette) >= 5, f"{cat}: need ≥5 emojis"
            assert len(tmpl.typical_features) >= 4, f"{cat}: need ≥4 features"
            assert len(tmpl.target_audiences) >= 3, f"{cat}: need ≥3 audiences"

    def test_emoji_palette_are_actual_emojis(self):
        for cat, tmpl in CATEGORY_TEMPLATES.items():
            for emoji in tmpl.emoji_palette:
                # Emojis are above ASCII range
                assert any(ord(c) > 127 for c in emoji), \
                    f"{cat}: '{emoji}' is not an emoji"


class TestTemplateEngine:
    def setup_method(self):
        self.engine = TemplateEngine()

    def test_categories_list(self):
        cats = self.engine.categories
        assert len(cats) == 12
        assert "electronics" in cats
        assert "fashion" in cats
        assert "baby" in cats

    def test_get_template_valid(self):
        tmpl = self.engine.get_template("electronics")
        assert tmpl is not None
        assert tmpl.category == Category.ELECTRONICS

    def test_get_template_case_insensitive(self):
        tmpl = self.engine.get_template("ELECTRONICS")
        assert tmpl is not None

    def test_get_template_invalid(self):
        tmpl = self.engine.get_template("nonexistent")
        assert tmpl is None

    def test_detect_electronics(self):
        assert self.engine.detect_category("iPhone 15 Pro Max") == Category.ELECTRONICS
        assert self.engine.detect_category("wireless bluetooth headphone") == Category.ELECTRONICS
        assert self.engine.detect_category("USB-C charger cable") == Category.ELECTRONICS

    def test_detect_fashion(self):
        assert self.engine.detect_category("women's summer dress floral") == Category.FASHION
        assert self.engine.detect_category("leather wallet men bifold") == Category.FASHION
        assert self.engine.detect_category("running sneakers") in (Category.FASHION, Category.SPORTS)

    def test_detect_beauty(self):
        assert self.engine.detect_category("vitamin C serum for face") == Category.BEAUTY
        assert self.engine.detect_category("hydrating moisturizer cream") == Category.BEAUTY

    def test_detect_home_garden(self):
        assert self.engine.detect_category("bamboo shelf storage organizer") == Category.HOME_GARDEN
        assert self.engine.detect_category("garden tool set") == Category.HOME_GARDEN

    def test_detect_toys(self):
        assert self.engine.detect_category("LEGO building blocks 500 pieces") == Category.TOYS
        assert self.engine.detect_category("board game family puzzle") == Category.TOYS

    def test_detect_food(self):
        assert self.engine.detect_category("organic dark chocolate 70% cacao") == Category.FOOD
        assert self.engine.detect_category("cold brew coffee concentrate") == Category.FOOD

    def test_detect_pet(self):
        assert self.engine.detect_category("dog collar large breed leather") == Category.PET
        assert self.engine.detect_category("cat litter self cleaning") == Category.PET

    def test_detect_baby(self):
        assert self.engine.detect_category("baby stroller lightweight foldable") == Category.BABY
        assert self.engine.detect_category("infant car seat") == Category.BABY

    def test_detect_automotive(self):
        assert self.engine.detect_category("car dash cam 4K") == Category.AUTOMOTIVE
        assert self.engine.detect_category("brake pad replacement") == Category.AUTOMOTIVE

    def test_detect_sports(self):
        assert self.engine.detect_category("yoga mat non-slip extra thick") == Category.SPORTS
        assert self.engine.detect_category("dumbbell set adjustable") == Category.SPORTS

    def test_detect_office(self):
        assert self.engine.detect_category("gel pen set 12 colors notebook") == Category.OFFICE
        assert self.engine.detect_category("desk organizer whiteboard") == Category.OFFICE

    def test_detect_health(self):
        assert self.engine.detect_category("vitamin D3 supplement 5000IU") == Category.HEALTH
        assert self.engine.detect_category("probiotic capsules") == Category.HEALTH

    def test_detect_unknown(self):
        result = self.engine.detect_category("xyzzy foobar baz")
        assert result is None

    def test_enhance_prompt_electronics(self):
        prompt = self.engine.enhance_prompt(
            "Bluetooth speaker", "amazon", "electronics"
        )
        assert "Category Intelligence" in prompt
        assert "Power Words" in prompt
        assert "Title Patterns" in prompt
        assert "SEO Keyword Hints" in prompt

    def test_enhance_prompt_auto_detect(self):
        prompt = self.engine.enhance_prompt(
            "yoga mat", "shopee"
        )
        assert "Category Intelligence" in prompt

    def test_enhance_prompt_platform_tips(self):
        prompt = self.engine.enhance_prompt(
            "wireless headphone", "amazon", "electronics"
        )
        assert "Platform Tips" in prompt

    def test_enhance_prompt_unknown_category(self):
        prompt = self.engine.enhance_prompt(
            "xyzzy quantum gadget", "amazon", "nonexistent"
        )
        # Should fall back to auto-detect, which may fail
        # Either returns content or empty string
        assert isinstance(prompt, str)

    def test_get_power_words_all(self):
        words = self.engine.get_power_words("electronics")
        assert len(words) > 0
        assert len(words) <= 10

    def test_get_power_words_by_type(self):
        words = self.engine.get_power_words("electronics", "urgency")
        assert len(words) > 0
        assert all(isinstance(w, str) for w in words)

    def test_get_power_words_invalid_category(self):
        words = self.engine.get_power_words("nonexistent")
        assert words == []

    def test_get_emoji_palette(self):
        emojis = self.engine.get_emoji_palette("fashion")
        assert len(emojis) > 0
        assert "👗" in emojis

    def test_get_emoji_palette_invalid(self):
        emojis = self.engine.get_emoji_palette("nonexistent")
        assert emojis == []

    def test_format_category_summary(self):
        summary = self.engine.format_category_summary("electronics")
        assert "Electronics & Tech" in summary
        assert "Audiences" in summary
        assert "Power words" in summary

    def test_format_category_summary_invalid(self):
        summary = self.engine.format_category_summary("nonexistent")
        assert "Unknown" in summary

    def test_platform_tips_present(self):
        """At least some categories have platform tips."""
        has_tips = False
        for tmpl in CATEGORY_TEMPLATES.values():
            if tmpl.platform_tips:
                has_tips = True
                break
        assert has_tips

    def test_avoid_words_are_strings(self):
        for cat, tmpl in CATEGORY_TEMPLATES.items():
            for w in tmpl.avoid_words:
                assert isinstance(w, str), f"{cat}: avoid_word not string: {w}"
