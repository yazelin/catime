"""這兩個地方吞掉錯誤會靜靜造成損害:清空讚數、重發貓圖。守住它們會噴錯。"""

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import fetch_likes  # noqa: E402
import post_telegram  # noqa: E402


def test_gh_api_failure_raises_instead_of_returning_empty():
    """gh api 掛掉必須炸開,否則 main 會把空的 likes.json 寫回去把讚數洗掉。"""
    failed = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="HTTP 403")
    with mock.patch.object(subprocess, "run", return_value=failed):
        with pytest.raises(RuntimeError, match="gh api failed"):
            fetch_likes.gh_api("/repos/x/y/issues")


def test_corrupt_state_file_raises_instead_of_reposting(tmp_path):
    """壞掉的 state 檔不能被當成「沒發過」,否則同一隻貓會每小時重發一次。"""
    state = tmp_path / "telegram_state.json"
    state.write_text("{not json")
    with mock.patch.object(post_telegram, "STATE_FILE", state):
        with pytest.raises(json.JSONDecodeError):
            post_telegram.get_last_posted_number()


def test_missing_state_file_still_returns_none(tmp_path):
    """沒有檔案是正常的初始狀態,不該炸。"""
    with mock.patch.object(post_telegram, "STATE_FILE", tmp_path / "nope.json"):
        assert post_telegram.get_last_posted_number() is None
