"""Tests for AI Listing Writer."""
import os
import sys
import json
import time
import pytest
from unittest.mock import patch, MagicMock

# Set env before imports
os.environ["BOT_TOKEN"] = "test-token-123"
os.environ["OPENAI_API_KEY"] = "sk-test-key"
os.environ["OPENAI_BASE_URL"] = "https://api.test.com/v1"

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import Config
from app.platforms import PLATFORMS, get_platform, list_platforms
from app.ai_engine import call_ai
from app.history import HistoryStore


class TestConfig:
    def test_config_loads_env(self):
        c = Config()
        assert c.BOT_TOKEN == "test-token-123"
        assert c.OPENAI_KEY == "sk-test-key"

    def test_config_defaults(self):
        c = Config()
        assert c.OPENAI_MODEL == "gpt-4o-mini"
        assert c.RATE_LIMIT_PER_MIN == 10
        assert c.MAX_HISTORY == 50

    def test_validate_missing_token(self):
        c = Config()
        c.BOT_TOKEN = ""
        with pytest.raises(ValueError, match="BOT_TOKEN"):
            c.validate()

    def test_validate_missing_api_key(self):
        c = Config()
        c.OPENAI_KEY = ""
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            c.validate()


class TestPlatforms:
    def test_all_platforms_have_required_fields(self):
        for key, p in PLATFORMS.items():
            assert "name" in p, f"{key} missing name"
            assert "emoji" in p, f"{key} missing emoji"
            assert "template" in p, f"{key} missing template"
            assert "{product}" in p["template"], f"{key} template missing {{product}}"
            assert "{lang}" in p["template"], f"{key} template missing {{lang}}"

    def test_platform_count(self):
        assert len(PLATFORMS) >= 6

    def test_get_platform(self):
        assert get_platform("amazon") is not None
        assert get_platform("AMAZON") is not None
        assert get_platform("nonexistent") is None

    def test_list_platforms_format(self):
        result = list_platforms()
        assert "/amazon" in result
        assert "/shopee" in result
        assert "Amazon" in result

    def test_new_platforms_exist(self):
        assert "ebay" in PLATFORMS
        assert "walmart" in PLATFORMS


class TestAIEngine:
    @patch("app.ai_engine.requests.post")
    def test_call_ai_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Test listing output"}}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = call_ai("test prompt")
        assert result == "Test listing output"
        mock_post.assert_called_once()

    @patch("app.ai_engine.requests.post")
    def test_call_ai_timeout_retry(self, mock_post):
        import requests as req_lib
        mock_post.side_effect = req_lib.exceptions.Timeout("timeout")

        result = call_ai("test", retries=2)
        assert "失败" in result
        assert mock_post.call_count == 2

    @patch("app.ai_engine.requests.post")
    def test_call_ai_http_error_no_retry(self, mock_post):
        import requests as req_lib
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        err = req_lib.exceptions.HTTPError(response=mock_resp)
        mock_post.side_effect = err

        result = call_ai("test", retries=3)
        assert "401" in result
        assert mock_post.call_count == 1  # No retry for 4xx


class TestHistory:
    def test_in_memory_add_and_get(self):
        store = HistoryStore(redis_url="redis://invalid:9999/0")
        assert store.redis is None

        store.add_record(123, "amazon", "earbuds", "Great product...")
        store.add_record(123, "shopee", "mouse", "Wireless mouse...")

        history = store.get_history(123)
        assert len(history) == 2
        assert history[0]["platform"] == "shopee"  # Most recent first
        assert history[1]["platform"] == "amazon"

    def test_rate_limit(self):
        store = HistoryStore(redis_url="redis://invalid:9999/0")
        for _ in range(5):
            assert store.check_rate_limit(999, max_per_min=5) is True
        assert store.check_rate_limit(999, max_per_min=5) is False

    def test_stats(self):
        store = HistoryStore(redis_url="redis://invalid:9999/0")
        store.add_record(100, "amazon", "p1", "r1")
        store.add_record(100, "amazon", "p2", "r2")
        store.add_record(100, "shopee", "p3", "r3")

        stats = store.get_stats(100)
        assert stats["total"] == 3
        assert stats["platforms"]["amazon"] == 2
        assert stats["platforms"]["shopee"] == 1

    def test_max_history_limit(self):
        store = HistoryStore(redis_url="redis://invalid:9999/0", max_history=3)
        for i in range(5):
            store.add_record(200, "amazon", f"product_{i}", f"result_{i}")
        history = store.get_history(200)
        assert len(history) == 3

    def test_separate_users(self):
        store = HistoryStore(redis_url="redis://invalid:9999/0")
        store.add_record(1, "amazon", "p1", "r1")
        store.add_record(2, "shopee", "p2", "r2")
        assert len(store.get_history(1)) == 1
        assert len(store.get_history(2)) == 1
        assert store.get_history(1)[0]["platform"] == "amazon"


class TestBotCommands:
    """Test bot message routing (without actual Telegram API)."""

    @patch("bot.tg_send")
    @patch("bot.tg_request")
    def test_start_command(self, mock_req, mock_send):
        from bot import process_message
        process_message(123, 1, "/start")
        mock_send.assert_called()
        call_text = mock_send.call_args[0][1]
        assert "AI Listing Writer" in call_text

    @patch("bot.tg_send")
    def test_history_empty(self, mock_send):
        from bot import cmd_history
        cmd_history(99999, 1)
        mock_send.assert_called()
        assert "暂无" in mock_send.call_args[0][1]

    @patch("bot.tg_send")
    def test_stats_empty(self, mock_send):
        from bot import cmd_stats
        cmd_stats(99999, 1)
        mock_send.assert_called()
        assert "暂无" in mock_send.call_args[0][1]

    @patch("bot.generate_listing")
    @patch("bot.tg_send")
    def test_inline_platform(self, mock_send, mock_gen):
        from bot import process_message
        process_message(123, 1, "amazon wireless earbuds")
        mock_gen.assert_called_once_with(123, 1, "amazon", "wireless earbuds")

    @patch("bot.tg_send")
    def test_unknown_input(self, mock_send):
        from bot import process_message
        process_message(123, 1, "hello")
        mock_send.assert_called()
        assert "平台" in mock_send.call_args[0][1]
