def test_image_generation_with_mock(mock_gemini):
    out = mock_gemini.generate_image("a cat in ukiyo-e style")
    assert out.get("image_url", "") .startswith("https://")
    assert len(mock_gemini.images) == 1
