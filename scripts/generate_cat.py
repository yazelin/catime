"""Generate a cat image using nanobanana-py, upload as GitHub Release asset. Run by GitHub Actions hourly."""

import asyncio
import json
import os
import random
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── gemini-web 自架 API 支援 ──
# 設定 GEMINI_WEB_BASE_URL 環境變數即可將所有 API 呼叫導向自架的 gemini-web 服務
# 例如：GEMINI_WEB_BASE_URL=https://ching-tech.ddns.net/gemini-web
_GEMINI_WEB_BASE_URL = os.getenv("GEMINI_WEB_BASE_URL")


def _create_genai_client():
    """建立 google-genai client（支援自架 gemini-web API）"""
    from google import genai
    if _GEMINI_WEB_BASE_URL:
        return genai.Client(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            http_options={"api_version": "v1beta", "base_url": _GEMINI_WEB_BASE_URL},
        )
    return genai.Client()


def _patch_nanobanana():
    """將 nanobanana-py 的 API 端點導向自架 gemini-web 服務"""
    if _GEMINI_WEB_BASE_URL:
        import nanobanana_py.image_generator
        nanobanana_py.image_generator.API_BASE_URL = _GEMINI_WEB_BASE_URL + "/v1beta/models"


_patch_nanobanana()

SUMMARY_PROMPT = (
    "You are analyzing recent AI-generated cat image prompts to identify repetitive patterns.\n\n"
    "Here are the most recent prompts and stories:\n{entries}\n\n"
    "Identify overused themes, settings, styles, poses, lighting, and vocabulary.\n"
    "Output a JSON object with exactly this format:\n"
    '{{"avoid_list": ["繁體中文短語 1", "繁體中文短語 2", ...]}}\n\n'
    "Rules:\n"
    "- Each item should be a short phrase in 繁體中文 (e.g. '生物發光森林', '貓凝望月亮', '宇宙空靈光芒')\n"
    "- List 8-15 items that appear too frequently\n"
    "- Focus on specific repeated combos, not generic concepts"
)

NEWS_PROMPT = (
    "Search for today's interesting world news and current events.\n\n"
    "Pick 3-5 news items that are:\n"
    "- Fun, heartwarming, quirky, cultural, scientific, sports, weather, travel, tourism, or lifestyle related\n"
    "- From DIFFERENT regions of the world\n"
    "- AVOID: war, terrorism, political controversy, violent crime, natural disasters with casualties\n\n"
    "For each item, write a 1-sentence summary in 繁體中文. MUST include the city/country where it happened.\n\n"
    "Output a JSON object with exactly this format:\n"
    '{{"news": ["繁體中文摘要 1", "繁體中文摘要 2", ...]}}'
)

IDEA_PROMPT = (
    "You are a wildly creative storyteller and visual director inventing a unique scene for an AI cat image.\n\n"
    "{news_section}"
    "{avoid_section}"
    "Requirements:\n"
    "(1) A cat must be the subject or prominently featured\n"
    "(2) The cat MUST be DOING something specific (cooking, skateboarding, repairing a clock, reading a map, etc.)\n"
    "(3) The scene MUST be set in a specific, concrete place (a 1950s diner, a Tokyo subway car, a greenhouse, a lighthouse, etc.)\n"
    "(4) Be wildly creative - surprise me with unexpected combinations\n"
    "{style_section}"
    "(5) Use the visual style specified in TODAY'S STYLE PALETTE above. If none provided, pick any creative style.\n"
    "(6) For photography styles: describe the scene realistically - real cats in real places. "
    "Do NOT add fantasy or magical elements. Think like a photographer, not a painter.\n"
    "(7) Vary the scene composition - sometimes include other characters (people, other animals, crowds) "
    "or objects the cat interacts with. A lone cat is fine occasionally, but don't default to it every time.\n\n"
    "Output a JSON object with exactly this format:\n"
    '{{"idea": "繁體中文場景描述，1-2句，包含藝術風格", "story": "繁體中文短故事，2-3句", "title": "作品名稱，3-10個字的繁體中文", "inspiration": "original 或引用的新聞摘要"}}\n\n'
    "The title should be poetic, evocative, and concise (3-10 Chinese characters). Like a painting title.\n"
    "Examples: 晨光裡的守望、雨巷漫步、星空下的琴音、午後的秘密\n\n"
    "For the 'inspiration' field:\n"
    "- If your idea was inspired by one of the news items, copy that exact news summary as the value.\n"
    "- If your idea is purely from imagination (not based on any news), set it to \"original\".\n\n"
    "idea, story, title, and inspiration should all be in Traditional Chinese (except 'original' stays English)."
)

RENDER_PROMPT = (
    "You are a prompt engineer converting a creative idea into a concise image generation prompt.\n\n"
    "Idea: {idea}\n"
    "Story: {story}\n"
    "{style_snippets_section}\n"
    "Requirements:\n"
    "(1) The date and time '{timestamp}' MUST be visually displayed in the image\n"
    "(2) Include specific art style, composition, lighting, and color details\n"
    "(3) Do NOT include any resolution keywords (like 4K, 8K, 16K, etc.)\n"
    "(4) The image must clearly show a cat doing the described activity\n"
    "(5) CRITICAL - match the prompt style to the medium:\n"
    "    - If PHOTOGRAPHY: use camera terms (e.g. '35mm lens, f/1.8, natural light, shallow depth of field, "
    "grain, candid shot'). The output MUST look like a real photograph, NOT a painting or digital art. "
    "Do NOT use words like 'breathtaking', 'intricate', 'ethereal', 'brushstrokes', or 'palette'.\n"
    "    - If ILLUSTRATION/ART: describe artistic medium, technique, and visual style.\n"
    "(6) If style reference snippets are provided below, incorporate them into the prompt.\n\n"
    "Output a JSON object with exactly this format:\n"
    '{{"prompt": "English image prompt here"}}'
)

def safe_load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Failed to read {path}: {e}")
        return default


def load_json_list(path: Path) -> list:
    data = safe_load_json(path, [])
    if isinstance(data, list):
        return data
    print(f"Invalid JSON structure in {path}, expected list.")
    return []


def load_json_dict(path: Path, default: dict | None = None) -> dict:
    fallback = default or {}
    data = safe_load_json(path, fallback)
    if isinstance(data, dict):
        return data
    print(f"Invalid JSON structure in {path}, expected object.")
    return fallback


def atomic_write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    tmp_path.replace(path)

def load_style_reference() -> dict:
    """Load style_reference.json, return empty dict if not found."""
    style_path = Path(__file__).parent / "style_reference.json"
    if not style_path.exists():
        return {}
    try:
        return json.loads(style_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


STYLE_FILTER_PROMPT = (
    "You are filtering style options for an AI cat image generator.\n\n"
    "AVOID LIST (overused themes to skip):\n{avoid_list}\n\n"
    "STYLE OPTIONS by category:\n{style_options}\n\n"
    "For each style option, decide if it matches or overlaps with ANY avoid list item.\n"
    "Match broadly: if the avoid item's concept covers the style, exclude it.\n"
    "Examples: '暖色調/秋季調色' should exclude '暖色調（琥珀/秋日）', "
    "'光滑亮面質感' should exclude '亮面塑膠/玩具質感', "
    "'微縮模型效果' should exclude '微縮立體模型'.\n\n"
    "Output a JSON object mapping each category to a list of indices (0-based) to EXCLUDE:\n"
    '{{"art_style": [0, 3], "composition": [1], "lighting": [], ...}}\n'
    "If no styles should be excluded in a category, use an empty list []."
)


def _filter_styles_with_ai(styles: dict, avoid_list: list[str]) -> dict[str, set[int]]:
    """Use Gemini Flash to determine which style indices to exclude per category."""
    # Format style options for the prompt
    lines = []
    for category, entries in styles.items():
        opts = ", ".join(f"[{i}] {e['zh']} ({e['en']})" for i, e in enumerate(entries))
        lines.append(f"{category}: {opts}")
    style_options = "\n".join(lines)
    avoid_text = "\n".join(f"- {item}" for item in avoid_list)

    try:
        from google import genai

        client = _create_genai_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=STYLE_FILTER_PROMPT.format(avoid_list=avoid_text, style_options=style_options),
        )
        # Parse with no required keys — partial results are fine
        result = parse_ai_response_generic(response.text, [])
        if result and isinstance(result, dict):
            excluded = {}
            for category in styles:
                indices = result.get(category, [])
                if isinstance(indices, list):
                    excluded[category] = set(int(i) for i in indices if isinstance(i, (int, float)))
                else:
                    excluded[category] = set()
            total = sum(len(v) for v in excluded.values())
            print(f"Style filter: AI excluded {total} styles across {len(excluded)} categories.")
            return excluded
    except Exception as e:
        print(f"Style filter AI call failed ({e}), skipping filter.")
    return {}


def pick_random_styles(avoid_list: list[str] | None = None) -> dict:
    """Pick one random style from each category, using AI to filter avoided styles.

    Returns {category: {zh, en, prompt}}.
    """
    styles = load_style_reference()
    if not styles:
        return {}
    excluded = _filter_styles_with_ai(styles, avoid_list) if avoid_list else {}
    picks = {}
    for category, entries in styles.items():
        excl = excluded.get(category, set())
        candidates = [e for i, e in enumerate(entries) if i not in excl] if excl else entries
        if not candidates:
            candidates = entries  # fallback if all filtered out
        if candidates:
            picks[category] = random.choice(candidates)
    return picks


def format_style_suggestion(picks: dict) -> str:
    """Format picked styles into a prompt section for IDEA_PROMPT."""
    if not picks:
        return ""
    lines = []
    for category, style in picks.items():
        lines.append(f"- {category}: {style['zh']} ({style['en']})")
    style_list = "\n".join(lines)
    return (
        "TODAY'S STYLE PALETTE (use these as your visual direction):\n"
        f"{style_list}\n"
        "You MUST use the art_style pick as your visual style. "
        "Incorporate the other picks (composition, lighting, texture, color_palette) naturally.\n\n"
    )


def format_style_prompt_snippet(picks: dict) -> str:
    """Get the combined prompt snippets from picked styles for RENDER_PROMPT."""
    if not picks:
        return ""
    snippets = [style["prompt"] for style in picks.values()]
    return ", ".join(snippets)


REPO = os.environ.get("GITHUB_REPOSITORY", "yazelin/catime")
# RELEASE_TAG is now set dynamically in main() based on current month

# ── Character System ──

def load_character_index() -> dict | None:
    """Load characters/index.json. Returns None if not found."""
    index_path = Path("characters/index.json")
    if not index_path.exists():
        return None
    try:
        return json.loads(index_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def load_character(char_id: str) -> dict | None:
    """Load a character profile by ID."""
    index = load_character_index()
    if not index:
        return None
    for entry in index.get("characters", []):
        if entry["id"] == char_id and entry.get("enabled", True):
            char_path = Path("characters") / entry["file"]
            if char_path.exists():
                try:
                    return json.loads(char_path.read_text())
                except (json.JSONDecodeError, OSError):
                    pass
    return None


def get_current_season(month: int, index: dict) -> str | None:
    """Get season name for the given month."""
    for season, months in index.get("seasonal_months", {}).items():
        if month in months:
            return season
    return None


def select_character(now: datetime) -> dict | None:
    """Select a character for this generation, or None for original.

    Returns the full character profile dict, or None.
    """
    index = load_character_index()
    if not index or not index.get("characters"):
        return None

    prob = index.get("probability", {})
    original_prob = prob.get("original", 0.50)
    recurring_prob = prob.get("recurring", 0.35)
    # seasonal_prob is the remainder

    roll = random.random()

    if roll < original_prob:
        print("Character roll: original (no character)")
        return None

    # Load all enabled characters
    all_chars = []
    for entry in index["characters"]:
        if not entry.get("enabled", True):
            continue
        char = load_character(entry["id"])
        if char:
            all_chars.append(char)

    if not all_chars:
        return None

    cooldown_hours = index.get("cooldown_hours", 24)

    def is_available(char: dict) -> bool:
        """Check if character is not in cooldown."""
        last = char.get("last_appeared")
        if not last:
            return True
        try:
            last_dt = datetime.strptime(last, "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
            return (now - last_dt).total_seconds() > cooldown_hours * 3600
        except ValueError:
            return True

    def weight(char: dict) -> float:
        """Less appearances = higher weight."""
        return 1.0 / (1 + char.get("appearances", 0))

    current_season = get_current_season(now.month, index)

    if roll < original_prob + recurring_prob:
        # Recurring: pick any available character
        candidates = [c for c in all_chars if is_available(c)]
        if not candidates:
            print("Character roll: recurring, but all in cooldown → original")
            return None
        print(f"Character roll: recurring ({len(candidates)} available)")
    else:
        # Seasonal: prefer seasonal variant, same characters just themed
        candidates = [c for c in all_chars if is_available(c)]
        if not candidates:
            print("Character roll: seasonal, but all in cooldown → original")
            return None
        print(f"Character roll: seasonal/{current_season} ({len(candidates)} available)")

    # Weighted random pick
    weights = [weight(c) for c in candidates]
    total = sum(weights)
    r = random.random() * total
    cumulative = 0
    for i, w in enumerate(weights):
        cumulative += w
        if r <= cumulative:
            chosen = candidates[i]
            break
    else:
        chosen = candidates[-1]

    # Determine if seasonal theme applies
    is_seasonal = roll >= original_prob + recurring_prob and current_season
    chosen = dict(chosen)  # copy to avoid mutating cache
    chosen["_is_seasonal"] = is_seasonal
    chosen["_season"] = current_season if is_seasonal else None

    print(f"Selected character: {chosen['name']['zh']} ({chosen['id']})"
          + (f" [seasonal: {current_season}]" if is_seasonal else ""))
    return chosen


def format_character_for_idea(char: dict) -> str:
    """Format character info for IDEA_PROMPT injection."""
    appearance = char.get("appearance", {})
    personality = char.get("personality", {})

    appearance_lines = []
    for key in ["breed", "body", "face", "fur_pattern", "size"]:
        if key in appearance:
            appearance_lines.append(appearance[key])
    if appearance.get("distinctive_features"):
        appearance_lines.extend(appearance["distinctive_features"])

    traits = "、".join(personality.get("traits", []))
    quirks = "、".join(personality.get("quirks", []))

    seasonal_note = ""
    if char.get("_is_seasonal") and char.get("_season"):
        season = char["_season"]
        variant = char.get("seasonal_variants", {}).get(season, "")
        if variant:
            seasonal_note = f"\n季節主題（{season}）：{variant}\n你必須將這個季節主題融入場景設計中。\n"

    return (
        f"TODAY'S CHARACTER: {char['name']['zh']} ({char['name']['en']})\n"
        f"外觀：{'。'.join(appearance_lines)}\n"
        f"個性：{traits}\n"
        f"小癖好：{quirks}\n"
        f"背景故事：{char.get('story_context', '')}\n"
        f"偏好場景：{'、'.join(char.get('preferred_settings', []))}\n"
        f"{seasonal_note}\n"
        f"你必須讓這個角色成為畫面的主角。\n"
        f"場景和行為要符合這個角色的個性和偏好。\n"
        f"保持角色的外觀特徵一致，這是系列角色。\n"
    )


def format_character_for_render(char: dict) -> str:
    """Format character visual snippet for RENDER_PROMPT injection."""
    snippet = char.get("visual_prompt_snippet", "")
    if not snippet:
        return ""

    seasonal_addition = ""
    if char.get("_is_seasonal") and char.get("_season"):
        season = char["_season"]
        variant = char.get("seasonal_variants", {}).get(season, "")
        if variant:
            seasonal_addition = f" Seasonal theme: {season} - the cat should be dressed/styled appropriately for {season}."

    return (
        f"\n⚠️ CHARACTER CONSISTENCY — NON-NEGOTIABLE:\n"
        f"{snippet}\n"
        f"Every HARD CONSTRAINT above is MANDATORY. Do NOT skip any.\n"
        f"If the art style makes any feature hard to show, simplify the style — NEVER drop the feature.{seasonal_addition}\n"
    )


def update_character_after_generation(char_id: str, cat_number: int, timestamp: str):
    """Update character appearance count and last_appeared timestamp."""
    index = load_character_index()
    if not index:
        return

    for entry in index["characters"]:
        if entry["id"] == char_id:
            char_path = Path("characters") / entry["file"]
            if char_path.exists():
                try:
                    char = json.loads(char_path.read_text())
                    char["appearances"] = char.get("appearances", 0) + 1
                    char["last_appeared"] = timestamp
                    char_path.write_text(json.dumps(char, indent=2, ensure_ascii=False) + "\n")
                    print(f"Updated {char_id}: appearances={char['appearances']}, last_appeared={timestamp}")
                except (json.JSONDecodeError, OSError) as e:
                    print(f"Failed to update character {char_id}: {e}")
            break


def get_recent_context(n: int = 10) -> dict:
    """Return the last n prompts and stories from catlist.json.

    Note: This function is no longer used by the main two-stage pipeline.
    It is kept for backwards compatibility and debugging purposes.
    The two-stage pipeline uses creative_notes (avoid_list) instead of
    feeding full historical prompts to prevent style imitation.
    """
    catlist_path = Path("catlist.json")
    if not catlist_path.exists():
        return {'prompts': [], 'stories': []}
    cats = load_json_list(catlist_path)
    valid_cats = [c for c in cats if isinstance(c, dict) and c.get("prompt")][-n:]
    return {
        'prompts': [c["prompt"] for c in valid_cats],
        'stories': [c.get("story", "") for c in valid_cats if c.get("story")]
    }


def parse_ai_response(text: str) -> dict:
    """Parse AI response that may contain JSON with prompt and story."""
    text = text.strip()

    # Try to extract JSON from markdown code block
    code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if code_block_match:
        text = code_block_match.group(1)

    # Try to parse as JSON
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "prompt" in data:
            return {
                'prompt': data.get("prompt", ""),
                'story': data.get("story", "")
            }
    except json.JSONDecodeError:
        pass

    # Fallback: treat entire text as prompt
    return {'prompt': text, 'story': ''}


def parse_ai_response_generic(text: str, required_keys: list) -> dict | None:
    """Parse AI response JSON with flexible required keys.

    Returns the parsed dict if all required_keys are present, or None on failure.
    """
    text = text.strip()

    # Try to extract JSON from markdown code block
    code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if code_block_match:
        text = code_block_match.group(1)

    try:
        data = json.loads(text)
        if isinstance(data, dict) and all(k in data for k in required_keys):
            return data
    except json.JSONDecodeError:
        pass

    return None


def load_creative_notes() -> dict:
    """Load creative_notes.json, return empty structure if not found."""
    notes_path = Path("creative_notes.json")
    notes = load_json_dict(notes_path, {"avoid_list": [], "updated_at": None})
    if not isinstance(notes.get("avoid_list"), list):
        notes["avoid_list"] = []
    return notes


def load_monthly_detail(month: str) -> list:
    """Load a monthly detail file (cats/YYYY-MM.json). Returns [] if not found."""
    month_path = Path("cats") / f"{month}.json"
    return load_json_list(month_path)


def maybe_update_creative_notes(cat_number: int) -> dict:
    """Update creative_notes.json every 5 cats. Returns current notes."""
    notes = load_creative_notes()

    if cat_number % 5 != 0:
        return notes

    print(f"Cat #{cat_number} is a multiple of 5, updating creative notes...")
    catlist_path = Path("catlist.json")
    if not catlist_path.exists():
        return notes

    cats = load_json_list(catlist_path)
    # Collect recent months from index timestamps (newest last)
    months = sorted({
        c["timestamp"][:7]
        for c in cats
        if isinstance(c, dict)
        and c.get("status", "success") == "success"
        and isinstance(c.get("timestamp"), str)
    })
    # Load details from recent months until we have enough entries
    all_details = []
    for month in reversed(months):
        all_details = load_monthly_detail(month) + all_details
        if sum(1 for c in all_details if c.get("prompt")) >= 10:
            break
    recent = [c for c in all_details if c.get("prompt")][-10:]
    if not recent:
        return notes

    entries_text = "\n".join(
        f"- Prompt: {c['prompt']}\n  Story: {c.get('story', '')}\n  Idea: {c.get('idea', '')}"
        for c in recent
    )

    try:
        from google import genai

        client = _create_genai_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=SUMMARY_PROMPT.format(entries=entries_text),
        )
        result = parse_ai_response_generic(response.text, ["avoid_list"])
        if result and isinstance(result["avoid_list"], list):
            notes = {
                "avoid_list": result["avoid_list"],
                "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            }
            Path("creative_notes.json").write_text(
                json.dumps(notes, indent=2, ensure_ascii=False) + "\n"
            )
            print(f"Creative notes updated with {len(notes['avoid_list'])} avoid items.")
            return notes
        print("Summary response missing avoid_list, keeping old notes.")
    except Exception as e:
        print(f"Creative notes update failed ({e}), keeping old notes.")

    return notes


def fetch_news_inspiration() -> list[str]:
    """Use Gemini with Google Search grounding to fetch today's interesting news.

    Returns a list of short news summaries, or empty list on failure.
    """
    print("Stage 0: Fetching today's news for inspiration...")
    try:
        from google import genai
        from google.genai import types

        client = _create_genai_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=NEWS_PROMPT,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )
        result = parse_ai_response_generic(response.text, ["news"])
        if result and isinstance(result["news"], list):
            news = result["news"][:5]
            for i, item in enumerate(news, 1):
                print(f"  News {i}: {item[:80]}...")
            return news
        print("  News parse failed, skipping news inspiration.")
    except Exception as e:
        print(f"  News fetch failed ({e}), skipping news inspiration.")
    return []


def generate_prompt_and_story(timestamp: str, creative_notes: dict, character: dict | None = None) -> dict:
    """Three-stage prompt generation: news -> idea -> render.

    Stage 0: NEWS_PROMPT + Google Search -> [news summaries] (optional inspiration)
    Stage 1: IDEA_PROMPT + avoid_list + news -> {"idea": ..., "story": ...}
    Stage 2: RENDER_PROMPT + idea + story + timestamp -> {"prompt": ...}

    Returns: {'prompt': str, 'story': str, 'idea': str, 'avoid_list': list, 'news_inspiration': list}
    """
    avoid_list = creative_notes.get("avoid_list", [])
    avoid_section = ""
    if avoid_list:
        bullets = "\n".join(f"- {item}" for item in avoid_list)
        avoid_section = (
            "IMPORTANT: Avoid these overused themes and patterns:\n"
            f"{bullets}\n\n"
        )

    # Stage 0: Fetch news inspiration (70% chance; 30% force original)
    if random.random() < 0.30:
        print("Inspiration roll: forced original (30% chance)")
        news = []
    else:
        news = fetch_news_inspiration()
    news_section = ""
    if news:
        bullets = "\n".join(f"- {item}" for item in news)
        news_section = (
            "Here are some current world events for inspiration. "
            "You MAY creatively incorporate one into the cat scene, or ignore them entirely. "
            "Aim for roughly half news-inspired, half pure imagination.\n"
            f"{bullets}\n\n"
        )

    # Character section for prompts
    character_idea_section = format_character_for_idea(character) if character else ""
    character_render_section = format_character_for_render(character) if character else ""

    # Pick random styles from style_reference.json, filtering out avoided styles
    style_picks = pick_random_styles(avoid_list)
    style_section = format_style_suggestion(style_picks)
    style_snippets = format_style_prompt_snippet(style_picks)
    style_snippets_section = f"Style reference snippets: {style_snippets}\n" if style_snippets else ""

    if style_picks:
        print(f"Style picks: {', '.join(s['en'] for s in style_picks.values())}")

    char_id = character["id"] if character else None
    char_name = character["name"]["zh"] if character else None
    is_seasonal = character.get("_is_seasonal", False) if character else False
    season = character.get("_season") if character else None

    fallback = {
        'prompt': f"A cute cat with the date and time '{timestamp}' displayed in the image, high quality, detailed",
        'story': "一隻可愛的貓咪正在享受美好的一天。",
        'idea': '',
        'title': '貓咪日常',
        'inspiration': 'original',
        'avoid_list': avoid_list,
        'news_inspiration': news,
        'style_picks': {k: v['en'] for k, v in style_picks.items()},
        'character': char_id,
        'character_name': char_name,
        'is_seasonal': is_seasonal,
        'season': season,
    }

    # Stage 1: Generate idea and story
    print(f"Stage 1: Generating idea (avoid_list has {len(avoid_list)} items, news has {len(news)} items)...")
    idea = ""
    story = ""
    title = ""
    inspiration = "original"
    try:
        from google import genai

        client = _create_genai_client()
        idea_input = IDEA_PROMPT.format(news_section=news_section, avoid_section=avoid_section, style_section=style_section)
        if character_idea_section:
            idea_input = character_idea_section + "\n" + idea_input
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=idea_input,
        )
        result = parse_ai_response_generic(response.text, ["idea", "story"])
        if result:
            idea = result["idea"]
            story = result["story"]
            title = result.get("title", "")
            inspiration = result.get("inspiration", "original")
            print(f"Title: {title}")
            print(f"Inspiration: {'🎨 原創' if inspiration == 'original' else '📰 ' + inspiration[:60]}")
            print(f"Idea: {idea[:120]}...")
            print(f"Story: {story[:80]}...")
        else:
            print("Stage 1 parse failed, using fallback.")
            return fallback
    except Exception as e:
        print(f"Stage 1 failed ({e}), using fallback.")
        return fallback

    # Stage 2: Convert idea to image prompt
    print("Stage 2: Converting idea to image prompt...")
    try:
        render_input = RENDER_PROMPT.format(idea=idea, story=story, timestamp=timestamp, style_snippets_section=style_snippets_section)
        if character_render_section:
            render_input = render_input + "\n" + character_render_section
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=render_input,
        )
        result = parse_ai_response_generic(response.text, ["prompt"])
        if result:
            prompt = result["prompt"]
            print(f"Prompt: {prompt[:120]}...")
            return {
                'prompt': prompt,
                'story': story,
                'idea': idea,
                'title': title or '貓咪日常',
                'inspiration': inspiration,
                'avoid_list': avoid_list,
                'news_inspiration': news,
                'style_picks': {k: v['en'] for k, v in style_picks.items()},
                'character': char_id,
                'character_name': char_name,
                'is_seasonal': is_seasonal,
                'season': season,
            }
        else:
            print("Stage 2 parse failed, using idea as prompt fallback.")
            return {
                'prompt': f"{idea}. The date and time '{timestamp}' is visually displayed in the image. {style_snippets}",
                'story': story,
                'idea': idea,
                'title': title or '貓咪日常',
                'inspiration': inspiration,
                'avoid_list': avoid_list,
                'news_inspiration': news,
                'style_picks': {k: v['en'] for k, v in style_picks.items()},
                'character': char_id,
                'character_name': char_name,
                'is_seasonal': is_seasonal,
                'season': season,
            }
    except Exception as e:
        print(f"Stage 2 failed ({e}), using idea as prompt fallback.")
        return {
            'prompt': f"{idea}. The date and time '{timestamp}' is visually displayed in the image. {style_snippets}",
            'story': story,
            'idea': idea,
            'title': title or '貓咪日常',
            'inspiration': inspiration,
            'avoid_list': avoid_list,
            'news_inspiration': news,
            'style_picks': {k: v['en'] for k, v in style_picks.items()},
            'character': char_id,
            'character_name': char_name,
            'is_seasonal': is_seasonal,
            'season': season,
        }


async def generate_cat_image(output_dir: str, timestamp: str, prompt: str) -> dict:
    """Use nanobanana-py's ImageGenerator to generate a cat image."""
    from nanobanana_py.image_generator import ImageGenerator
    from nanobanana_py.types import ImageGenerationRequest

    generator = ImageGenerator()

    request = ImageGenerationRequest(
        prompt=prompt,
        filename=f"cat_{timestamp.replace(' ', '_').replace(':', '')}",
        resolution="1K",
        file_format="png",
        parallel=1,
        output_count=1,
    )

    os.environ["NANOBANANA_OUTPUT_DIR"] = output_dir
    response = await generator.generate_text_to_image(request)

    if not response.success:
        return {
            "file_path": None,
            "model_used": None,
            "status": "failed",
            "error": f"{response.message} - {response.error}",
        }

    model_info = response.model_used or "unknown"
    if response.used_fallback:
        model_info += f" (fallback from {response.primary_model}, reason: {response.fallback_reason})"

    # Convert PNG to WebP for smaller file size
    png_path = response.generated_files[0]
    webp_path = png_path.rsplit(".", 1)[0] + ".webp"
    try:
        from PIL import Image

        img = Image.open(png_path)
        img.save(webp_path, "WEBP", quality=90)
        os.remove(png_path)
        print(f"Converted to WebP: {os.path.getsize(webp_path) / 1024:.0f}KB")
        final_path = webp_path
    except Exception as e:
        print(f"WebP conversion failed ({e}), using PNG")
        final_path = png_path

    return {
        "file_path": final_path,
        "model_used": model_info,
        "status": "success",
    }


def ensure_release_exists():
    """Create the 'cats' release if it doesn't exist."""
    result = subprocess.run(
        ["gh", "release", "view", RELEASE_TAG, "--repo", REPO],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        subprocess.run(
            [
                "gh", "release", "create", RELEASE_TAG,
                "--repo", REPO,
                "--title", "Cat Images",
                "--notes", "Auto-generated cat images, one every hour.",
            ],
            check=True,
        )


def upload_image_as_release_asset(image_path: str) -> str:
    """Upload image as a GitHub Release asset. Returns the public download URL."""
    filename = Path(image_path).name

    subprocess.run(
        [
            "gh", "release", "upload", RELEASE_TAG,
            image_path,
            "--repo", REPO,
            "--clobber",
        ],
        check=True,
    )

    # Release asset URL format
    return f"https://github.com/{REPO}/releases/download/{RELEASE_TAG}/{filename}"


def get_or_create_monthly_issue(now: datetime) -> str:
    """Get or create a monthly issue for cat images. Returns issue number as string."""
    month_label = now.strftime("%Y-%m")
    title = f"Cat Gallery - {month_label}"

    # Search for existing issue with this title
    result = subprocess.run(
        ["gh", "issue", "list", "--repo", REPO, "--search", f'"{title}" in:title', "--json", "number,title", "--limit", "10"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        issues = json.loads(result.stdout)
        for issue in issues:
            if issue["title"] == title:
                return str(issue["number"])

    # Create new monthly issue
    result = subprocess.run(
        ["gh", "issue", "create", "--repo", REPO, "--title", title, "--body", f"Auto-generated cat images for {month_label}."],
        capture_output=True, text=True, check=True,
    )
    # Extract issue number from URL output
    url = result.stdout.strip()
    return url.split("/")[-1]


def post_issue_comment(issue_number: str, image_url: str, number: int, timestamp: str, model_used: str, prompt: str = "", story: str = "", idea: str = "", title: str = "", inspiration: str = "") -> int | None:
    """Post a comment on the monthly issue with the cat image. Returns comment_id or None."""
    prompt_line = f"**Prompt:** {prompt}\n" if prompt else ""
    story_line = f"**Story:** {story}\n" if story else ""
    idea_line = f"**Idea:** {idea}\n" if idea else ""
    title_display = f" — {title}" if title else ""
    if inspiration and inspiration != "original":
        inspiration_line = f"**靈感來源:** 📰 {inspiration}\n"
    elif inspiration == "original":
        inspiration_line = "**靈感來源:** 🎨 AI 原創\n"
    else:
        inspiration_line = ""
    body = (
        f"## Cat #{number}{title_display}\n"
        f"**Time:** {timestamp}\n"
        f"**Model:** `{model_used}`\n"
        f"{inspiration_line}"
        f"{idea_line}"
        f"{prompt_line}"
        f"{story_line}\n"
        f"![cat-{number}]({image_url})"
    )
    result = subprocess.run(
        ["gh", "issue", "comment", issue_number, "--repo", REPO, "--body", body],
        capture_output=True, text=True, check=True,
    )
    # gh issue comment prints the comment URL, e.g. https://github.com/.../issues/3#issuecomment-123456
    comment_url = result.stdout.strip()
    match = re.search(r"issuecomment-(\d+)", comment_url)
    if match:
        return int(match.group(1))
    return None


def update_catlist_and_push(entry: dict) -> int:
    """Update catlist.json and monthly detail file, commit and push."""
    index_fields = {"number", "timestamp", "url", "model", "status", "error", "title", "inspiration", "character", "character_name", "is_seasonal", "season"}
    detail_fields = {"number", "prompt", "story", "idea", "title", "inspiration", "news_inspiration", "avoid_list", "style_picks", "comment_id", "character", "character_name", "is_seasonal", "season"}

    # Write lightweight index entry to catlist.json
    catlist_path = Path("catlist.json")
    cats = load_json_list(catlist_path)
    index_entry = {k: entry[k] for k in index_fields if k in entry}
    cats.append(index_entry)
    atomic_write_json(catlist_path, cats)

    git_add_files = ["catlist.json"]

    # Write detail entry to monthly file (only for successful cats with detail data)
    has_detail = any(entry.get(k) for k in detail_fields if k != "number")
    if has_detail:
        month = entry["timestamp"][:7]  # "YYYY-MM"
        cats_dir = Path("cats")
        cats_dir.mkdir(exist_ok=True)
        month_path = cats_dir / f"{month}.json"
        monthly = load_json_list(month_path)
        detail_entry = {k: entry[k] for k in detail_fields if k in entry}
        monthly.append(detail_entry)
        atomic_write_json(month_path, monthly)
        git_add_files.append(str(month_path))

    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(
        ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
        check=True,
    )

    if Path("creative_notes.json").exists():
        git_add_files.append("creative_notes.json")
    # Include character file updates (appearance counts)
    char_dir = Path("characters")
    if char_dir.exists():
        for f in char_dir.glob("*.json"):
            git_add_files.append(str(f))
    subprocess.run(["git", "add"] + git_add_files, check=True)

    status = entry["status"]
    number = entry.get("number")
    timestamp = entry["timestamp"]
    msg = f"Add cat #{number} - {timestamp}" if status == "success" else f"Failed cat - {timestamp}"
    subprocess.run(["git", "commit", "-m", msg], check=True)

    # Retry push with rebase in case of concurrent pushes
    for attempt in range(3):
        result = subprocess.run(["git", "push"], capture_output=True, text=True)
        if result.returncode == 0:
            break
        print(f"Push failed (attempt {attempt + 1}), rebasing...")
        subprocess.run(["git", "pull", "--rebase"], check=True)
    else:
        raise RuntimeError("Failed to push after 3 attempts")
    return number or 0


def already_has_cat_this_hour(now: datetime) -> bool:
    """Check if a successful cat already exists for the current hour."""
    catlist_path = Path("catlist.json")
    if not catlist_path.exists():
        return False
    cats = load_json_list(catlist_path)
    hour_prefix = now.strftime("%Y-%m-%d %H:")
    return any(
        isinstance(c, dict)
        and c.get("status", "success") == "success"
        and isinstance(c.get("timestamp"), str)
        and c["timestamp"].startswith(hour_prefix)
        for c in cats
    )


def main():
    global RELEASE_TAG
    
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%d %H:%M UTC")
    
    # Dynamically set release tag based on current month (e.g., "cats-2026-03")
    RELEASE_TAG = f"cats-{timestamp[:7]}"
    print(f"📦 Using release tag: {RELEASE_TAG}")

    # Skip if this hour already has a successful cat
    if already_has_cat_this_hour(now):
        print(f"Cat already exists for hour {now.strftime('%Y-%m-%d %H')} UTC, skipping.")
        return

    # Read current count for numbering (needed before creative notes update)
    catlist_path = Path("catlist.json")
    cats = load_json_list(catlist_path)
    next_number = len(cats) + 1

    # Update creative notes if needed (every 5 cats)
    creative_notes = maybe_update_creative_notes(next_number)

    # Select character (or None for original)
    character = select_character(now)

    print(f"Generating cat #{next_number} for {timestamp}...")
    prompt_data = generate_prompt_and_story(timestamp, creative_notes, character)
    prompt = prompt_data['prompt']
    story = prompt_data['story']
    idea = prompt_data.get('idea', '')
    avoid_list = prompt_data.get('avoid_list', [])
    news_inspiration = prompt_data.get('news_inspiration', [])
    style_picks = prompt_data.get('style_picks', {})
    title = prompt_data.get('title', '貓咪日常')
    inspiration = prompt_data.get('inspiration', 'original')
    char_id = prompt_data.get('character')
    char_name = prompt_data.get('character_name')
    is_seasonal = prompt_data.get('is_seasonal', False)
    season = prompt_data.get('season')
    result = asyncio.run(generate_cat_image("/tmp", timestamp, prompt))

    if result["status"] == "failed":
        print(f"Generation failed: {result['error']}", file=sys.stderr)
        entry = {
            "number": None,
            "timestamp": timestamp,
            "url": None,
            "model": "all failed",
            "status": "failed",
            "error": result["error"],
        }
        update_catlist_and_push(entry)
        sys.exit(1)

    image_path = result["file_path"]
    model_used = result["model_used"]
    print(f"Model used: {model_used}")

    print("Ensuring release exists...")
    ensure_release_exists()

    print("Uploading image as release asset...")
    image_url = upload_image_as_release_asset(image_path)
    print(f"Image URL: {image_url}")

    print("Posting issue comment...")
    comment_id = None
    try:
        issue_number = get_or_create_monthly_issue(now)
        print(f"Using monthly issue #{issue_number}")
        comment_id = post_issue_comment(issue_number, image_url, next_number, timestamp, model_used, prompt, story, idea, title, inspiration)
        if comment_id:
            print(f"Comment ID: {comment_id}")
    except Exception as e:
        print(f"Issue comment failed ({e}), continuing without comment_id.")

    entry = {
        "number": next_number,
        "timestamp": timestamp,
        "prompt": prompt,
        "story": story,
        "idea": idea,
        "avoid_list": avoid_list,
        "title": title,
        "inspiration": inspiration,
        "news_inspiration": news_inspiration,
        "style_picks": style_picks,
        "url": image_url,
        "model": model_used,
        "status": "success",
    }
    if comment_id:
        entry["comment_id"] = comment_id
    if char_id:
        entry["character"] = char_id
        entry["character_name"] = char_name
    if is_seasonal and season:
        entry["is_seasonal"] = True
        entry["season"] = season

    # Update character appearance stats
    if char_id:
        update_character_after_generation(char_id, next_number, timestamp)

    print("Updating catlist.json...")
    update_catlist_and_push(entry)

    print(f"Done! Cat #{next_number}" + (f" (character: {char_name})" if char_name else ""))


if __name__ == "__main__":
    main()
