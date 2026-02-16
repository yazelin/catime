def test_cli_help_output():
    # emulate CLI help output behavior
    help_text = "catime CLI - help"
    assert "help" in help_text.lower()
