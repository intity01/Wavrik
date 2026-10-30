from src.ui.theme.key_colors import build_qss, key_hue, key_index
from src.ui.theme.tokens import KEY_HUES, key_tint


def test_key_index_reads_camelot_codes():
    assert key_index("8A") == "8"
    assert key_index("Camelot: 11B (F# major)") == "11"
    assert key_index("12a") == "12"
    assert key_index("--") == ""
    assert key_index("") == ""
    assert key_index("13A") == ""


def test_key_hue_uses_wheel_position_for_both_modes():
    assert key_hue("8A") == KEY_HUES[7]
    assert key_hue("8B") == KEY_HUES[7]
    assert key_hue("1A") == KEY_HUES[0]
    assert key_hue("", "#000000") == "#000000"


def test_key_tint_is_light_on_light_theme_and_dark_on_dark_theme():
    light = int(key_tint("#D9497F", "light").lstrip("#"), 16)
    dark = int(key_tint("#D9497F", "dark").lstrip("#"), 16)
    assert min((light >> 16) & 255, (light >> 8) & 255, light & 255) > 200
    assert max((dark >> 16) & 255, (dark >> 8) & 255, dark & 255) < 90


def test_key_qss_covers_all_twelve_positions():
    qss = build_qss("light")
    for i in range(1, 13):
        assert f'keyIndex="{i}"' in qss
