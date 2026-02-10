"""Unit tests for core functions in scripts/generate_cat.py."""

import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

# Import generate_cat as a module from scripts/
SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import generate_cat  # noqa: E402


# ── Fixtures ──


@pytest.fixture
def style_picks():
    """Minimal style picks fixture."""
    return {
        "art_style": {"zh": "水彩畫", "en": "Watercolor", "prompt": "watercolor painting, soft edges"},
        "lighting": {"zh": "黃金時刻", "en": "Golden Hour", "prompt": "golden hour warm glow"},
    }


@pytest.fixture
def character_fixture():
    """Minimal character dict fixture."""
    return {
        "id": "mochi",
        "name": {"zh": "麻糬", "en": "Mochi"},
        "appearance": {
            "breed": "白色英國短毛貓",
            "body": "圓潤短胖",
            "face": "大圓眼",
        },
        "personality": {"traits": ["好奇", "貪吃"], "quirks": ["打呼嚕"]},
        "story_context": "住在甜點店的貓",
        "preferred_settings": ["甜點店", "廚房"],
        "visual_prompt_snippet": "white British Shorthair, round body",
        "_is_seasonal": False,
        "_season": None,
    }


@pytest.fixture
def character_index():
    """Minimal character index fixture."""
    return {
        "characters": [
            {"id": "mochi", "file": "mochi.json", "enabled": True},
            {"id": "captain", "file": "captain.json", "enabled": False},
        ],
        "probability": {"original": 0.50, "recurring": 0.35, "seasonal": 0.15},
        "cooldown_hours": 24,
        "seasonal_months": {
            "summer": [6, 7, 8],
            "winter": [12, 1, 2],
        },
    }


# ── Prompt Generation Logic ──


class TestFormatStyleSuggestion:
    def test_empty_picks(self):
        assert generate_cat.format_style_suggestion({}) == ""

    def test_with_picks(self, style_picks):
        result = generate_cat.format_style_suggestion(style_picks)
        assert "TODAY'S STYLE PALETTE" in result
        assert "Watercolor" in result
        assert "Golden Hour" in result
        assert "水彩畫" in result

    def test_contains_must_use(self, style_picks):
        result = generate_cat.format_style_suggestion(style_picks)
        assert "MUST use the art_style pick" in result


class TestFormatStylePromptSnippet:
    def test_empty(self):
        assert generate_cat.format_style_prompt_snippet({}) == ""

    def test_combines_snippets(self, style_picks):
        result = generate_cat.format_style_prompt_snippet(style_picks)
        assert "watercolor painting, soft edges" in result
        assert "golden hour warm glow" in result
        assert ", " in result


class TestParseAiResponse:
    def test_valid_json(self):
        text = '{"prompt": "a cute cat", "story": "once upon a time"}'
        result = generate_cat.parse_ai_response(text)
        assert result["prompt"] == "a cute cat"
        assert result["story"] == "once upon a time"

    def test_json_in_code_block(self):
        text = '```json\n{"prompt": "a cat in rain", "story": "rainy day"}\n```'
        result = generate_cat.parse_ai_response(text)
        assert result["prompt"] == "a cat in rain"

    def test_plain_text_fallback(self):
        text = "just a prompt without json"
        result = generate_cat.parse_ai_response(text)
        assert result["prompt"] == text
        assert result["story"] == ""

    def test_missing_prompt_key(self):
        text = '{"idea": "something", "story": "other"}'
        result = generate_cat.parse_ai_response(text)
        # Falls through to plain text since no "prompt" key
        assert result["story"] == ""


class TestParseAiResponseGeneric:
    def test_valid(self):
        text = '{"idea": "a cat cooking", "story": "chef cat"}'
        result = generate_cat.parse_ai_response_generic(text, ["idea", "story"])
        assert result["idea"] == "a cat cooking"

    def test_missing_key(self):
        text = '{"idea": "a cat"}'
        result = generate_cat.parse_ai_response_generic(text, ["idea", "story"])
        assert result is None

    def test_invalid_json(self):
        result = generate_cat.parse_ai_response_generic("not json", ["prompt"])
        assert result is None

    def test_code_block(self):
        text = '```\n{"avoid_list": ["theme1"]}\n```'
        result = generate_cat.parse_ai_response_generic(text, ["avoid_list"])
        assert result["avoid_list"] == ["theme1"]


class TestFormatCharacterForIdea:
    def test_basic_output(self, character_fixture):
        result = generate_cat.format_character_for_idea(character_fixture)
        assert "麻糬" in result
        assert "Mochi" in result
        assert "白色英國短毛貓" in result
        assert "好奇" in result
        assert "甜點店" in result
        assert "必須讓這個角色成為畫面的主角" in result

    def test_seasonal_variant(self, character_fixture):
        character_fixture["_is_seasonal"] = True
        character_fixture["_season"] = "summer"
        character_fixture["seasonal_variants"] = {"summer": "穿夏天花襯衫"}
        result = generate_cat.format_character_for_idea(character_fixture)
        assert "季節主題" in result
        assert "穿夏天花襯衫" in result


class TestFormatCharacterForRender:
    def test_basic_output(self, character_fixture):
        result = generate_cat.format_character_for_render(character_fixture)
        assert "white British Shorthair" in result
        assert "NON-NEGOTIABLE" in result

    def test_empty_snippet(self, character_fixture):
        character_fixture["visual_prompt_snippet"] = ""
        result = generate_cat.format_character_for_render(character_fixture)
        assert result == ""


# ── Character Selection Logic ──


class TestGetCurrentSeason:
    def test_summer(self, character_index):
        assert generate_cat.get_current_season(7, character_index) == "summer"

    def test_winter(self, character_index):
        assert generate_cat.get_current_season(12, character_index) == "winter"
        assert generate_cat.get_current_season(1, character_index) == "winter"

    def test_no_season(self, character_index):
        assert generate_cat.get_current_season(4, character_index) is None


class TestSelectCharacter:
    def test_original_roll(self, character_index, character_fixture):
        """Roll < original_prob → returns None (original, no character)."""
        now = datetime(2025, 7, 1, 12, 0, tzinfo=timezone.utc)
        with mock.patch.object(generate_cat, "load_character_index", return_value=character_index), \
             mock.patch("random.random", return_value=0.1):  # 0.1 < 0.50
            result = generate_cat.select_character(now)
            assert result is None

    def test_recurring_roll(self, character_index, character_fixture):
        """Roll in recurring range → picks a character."""
        now = datetime(2025, 7, 1, 12, 0, tzinfo=timezone.utc)
        with mock.patch.object(generate_cat, "load_character_index", return_value=character_index), \
             mock.patch.object(generate_cat, "load_character", return_value=character_fixture), \
             mock.patch("random.random", side_effect=[0.6, 0.5]):  # 0.6 is in recurring range (0.50-0.85)
            result = generate_cat.select_character(now)
            assert result is not None
            assert result["id"] == "mochi"

    def test_no_characters(self):
        """No character index → returns None."""
        now = datetime(2025, 7, 1, 12, 0, tzinfo=timezone.utc)
        with mock.patch.object(generate_cat, "load_character_index", return_value=None):
            result = generate_cat.select_character(now)
            assert result is None

    def test_empty_characters_list(self):
        """Empty characters list → returns None."""
        now = datetime(2025, 7, 1, 12, 0, tzinfo=timezone.utc)
        index = {"characters": [], "probability": {"original": 0.0, "recurring": 1.0}}
        with mock.patch.object(generate_cat, "load_character_index", return_value=index), \
             mock.patch("random.random", return_value=0.5):
            result = generate_cat.select_character(now)
            assert result is None


# ── Style Selection Logic ──


class TestPickRandomStyles:
    def test_empty_reference(self):
        with mock.patch.object(generate_cat, "load_style_reference", return_value={}):
            assert generate_cat.pick_random_styles() == {}

    def test_picks_one_per_category(self):
        fake_styles = {
            "art_style": [
                {"zh": "水彩", "en": "Watercolor", "prompt": "watercolor"},
                {"zh": "油畫", "en": "Oil", "prompt": "oil painting"},
            ],
            "lighting": [
                {"zh": "日光", "en": "Daylight", "prompt": "daylight"},
            ],
        }
        with mock.patch.object(generate_cat, "load_style_reference", return_value=fake_styles):
            random.seed(42)
            result = generate_cat.pick_random_styles()
            assert "art_style" in result
            assert "lighting" in result
            assert result["lighting"]["en"] == "Daylight"

    def test_skips_empty_category(self):
        fake_styles = {
            "art_style": [{"zh": "水彩", "en": "Watercolor", "prompt": "wc"}],
            "empty_cat": [],
        }
        with mock.patch.object(generate_cat, "load_style_reference", return_value=fake_styles):
            result = generate_cat.pick_random_styles()
            assert "art_style" in result
            assert "empty_cat" not in result


# ── Version Synchronization ──


class TestVersionSync:
    def test_versions_match(self):
        """pyproject.toml and __init__.py versions must match."""
        root = Path(__file__).resolve().parent.parent
        pyproject = root / "pyproject.toml"
        init_file = root / "src" / "catime" / "__init__.py"

        # Extract version from pyproject.toml
        pyproject_version = None
        for line in pyproject.read_text().splitlines():
            if line.startswith("version"):
                pyproject_version = line.split('"')[1]
                break

        # Extract version from __init__.py
        init_version = None
        for line in init_file.read_text().splitlines():
            if "__version__" in line:
                init_version = line.split('"')[1]
                break

        assert pyproject_version is not None, "version not found in pyproject.toml"
        assert init_version is not None, "__version__ not found in __init__.py"
        assert pyproject_version == init_version, (
            f"Version mismatch: pyproject.toml={pyproject_version}, __init__.py={init_version}"
        )
