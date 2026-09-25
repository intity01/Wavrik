from src.core.parser import normalizeUrl, parseImportText, validateUrl


def test_normalize_accepts_only_public_http_urls():
    assert validateUrl("https://Example.com/watch?v=1&utm_source=test")
    assert normalizeUrl("https://Example.com/watch?v=1&utm_source=test") == "https://example.com/watch?v=1"
    assert not validateUrl("file:///tmp/test")
    assert not validateUrl("ftp://example.com/file")
    assert not validateUrl("https://user:secret@example.com/video")


def test_import_removes_comments_invalid_lines_and_duplicates():
    text = """
    # saved links
    https://example.com/a
    invalid text
    https://example.com/a
    https://example.com/b?utm_campaign=x
    """
    assert parseImportText(text) == ["https://example.com/a", "https://example.com/b"]


def test_normalize_rejects_malformed_port_without_raising():
    assert normalizeUrl("https://example.com:not-a-port/video") == ""
