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


def test_normalize_strips_youtube_mix_and_radio():
    mix_url = "https://www.youtube.com/watch?v=j-FrcjMDqL0&list=RDj-FrcjMDqL0&start_radio=1"
    assert normalizeUrl(mix_url) == "https://www.youtube.com/watch?v=j-FrcjMDqL0"

    mix_url2 = "https://music.youtube.com/watch?v=uCTudycHxbk&list=RDuCTudycHxbk&index=1"
    assert normalizeUrl(mix_url2) == "https://music.youtube.com/watch?v=uCTudycHxbk"

    # User-created playlists should still be preserved
    real_playlist = "https://www.youtube.com/watch?v=j-FrcjMDqL0&list=PLrEnWoR732-BHrPp"
    assert "list=PLrEnWoR732-BHrPp" in normalizeUrl(real_playlist)
