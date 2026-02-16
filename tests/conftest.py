import sys
import pathlib
p = pathlib.Path(__file__).resolve().parents[2] / 'tests'
sys.path.insert(0, str(p))
from mock_helpers import MockOpenAI, MockGemini

import pytest

@pytest.fixture
def mock_openai(monkeypatch):
    mock = MockOpenAI()
    monkeypatch.setattr("openai", mock)
    return mock

@pytest.fixture
def mock_gemini(monkeypatch):
    mock = MockGemini()
    monkeypatch.setattr("gemini", mock)
    return mock
