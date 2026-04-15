from pathlib import Path
import pytest
from difonlib.utils import (
    logdbg,
    is_mac_address,
    # is_mac_address2,
    mac_format,
    UtilsError,
    to_signed,
    swap16,
    swap32,
    fs_remove_dir_content,
    file_get_latest,
    YamlConfig,
)


@pytest.mark.parametrize(
    "mac",
    [
        "AA:BB:CC:DD:EE:FF",
        "aa:bb:cc:dd:ee:ff",
        "01:23:45:67:89:aB",
    ],
)
def test_is_mac_address_valid(mac):
    assert is_mac_address(mac)


@pytest.mark.parametrize(
    "mac",
    [
        "AA-BB-CC-DD-EE-FF",
        "AABBCCDDEEFF",
        "GG:HH:II:JJ:KK:LL",
    ],
)
def test_is_mac_address_invalid(mac):
    assert not is_mac_address(mac)


def test_mac_format_ok():
    assert mac_format("112233445566") == "11:22:33:44:55:66"


def test_mac_format_invalid():
    with pytest.raises(UtilsError):
        mac_format("1234")


def test_to_signed_positive():
    assert to_signed(10, 8) == 10


def test_to_signed_negative():
    assert to_signed(0b11111111, 8) == -1


def test_swap16():
    assert swap16(0x1234) == 0x3412


def test_swap32():
    assert swap32(0x11223344) == 0x44332211


def test_fs_remove_dir_content(tmp_dir: Path):
    f = tmp_dir / "a.txt"
    f.write_text("hello")

    fs_remove_dir_content(str(tmp_dir))

    assert list(tmp_dir.iterdir()) == []


def test_file_get_latest(tmp_dir: Path):
    f1 = tmp_dir / "a.txt"
    f2 = tmp_dir / "b.txt"
    f1.write_text("1")
    f2.write_text("2")

    latest = file_get_latest(str(tmp_dir), "*.txt")
    if latest:
        assert latest.endswith("b.txt")


def test_yaml_config_create_and_save(yaml_config_path):
    cfg = YamlConfig(str(yaml_config_path))
    cfg.config["a"] = 1
    cfg.save()

    cfg2 = YamlConfig(str(yaml_config_path))
    assert cfg2.config["a"] == 1


def test_log_dbg():
    logdbg("hello 12345")
    assert True


def test_show_tmp(tmp_path):
    # Show value of tmp_path fixture
    print(f"Show value of tmp_path fixture: {tmp_path}")
