import pytest

from monitor_dim.winapi import MOD_CONTROL, MOD_NOREPEAT, MOD_SHIFT, parse_hotkey


def test_parse_hotkey_supports_function_keys_and_modifiers():
    modifiers, virtual_key = parse_hotkey("Ctrl+Shift+F9")

    assert modifiers == MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT
    assert virtual_key == 0x78


@pytest.mark.parametrize("value", ["", "Ctrl", "Ctrl+Banana", "F25", "A+B"])
def test_parse_hotkey_rejects_unsupported_values(value):
    with pytest.raises(ValueError):
        parse_hotkey(value)
