"""Mock helpers for tests."""


class MockOpenAI:
    """Mock OpenAI client for testing."""

    def __init__(self):
        self.calls = []


class MockGemini:
    """Mock Gemini client for testing."""

    def __init__(self):
        self.images = []

    def generate_image(self, prompt: str) -> dict:
        self.images.append(prompt)
        return {"image_url": "https://example.com/mock.png"}
