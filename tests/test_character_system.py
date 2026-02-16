def test_character_creation(tmp_path):
    # simple character data file
    f = tmp_path / "char.json"
    f.write_text('{"name": "Momo", "level": 1}')
    assert f.exists()
    s = f.read_text()
    assert 'Momo' in s
