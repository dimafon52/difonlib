import pytest
from pathlib import Path


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """
    Временная директория для файловых тестов
    """
    return tmp_path


@pytest.fixture
def yaml_config_path(tmp_path: Path) -> Path:
    """
    Путь к временному YAML-конфигу
    """
    return tmp_path / "config.yaml"
