# ==========================
# Makefile for difonlib
# ==========================

all: setup check-all build check test
setup: clean .setup 
# Все проверки: стиль, типы, тесты
check-all: fix lint format-check typecheck

# ----- Commands -------
info:
	tree -L 3
	uv tree

# Use make add pkg=package-name
add: 
	uv add "$(pkg)"

# Use make add-tool pkg=package-name
add-tool:
	uv add --dev "$(pkg)"

# Создание виртуального окружения и установка зависимостей
.setup:
	uv venv --clear
	uv sync --group dev

# Запуск тестов
test:
	uv run pytest -s # -s if during test used input(".....")

# Локальная сборка пакета (wheel + sdist)
build:
	uv build

# Проверка собранного пакета
check:
	uv run twine check dist/*

# Очистка временных файлов
clean:
	rm -rf dist/ build/ *.egg-info .pytest_cache
	find . -name '__pycache__' -type d -exec rm -rf {} +

# -------------------------------
# Качество кода
# -------------------------------

# Проверка стиля и типизации
lint:
	uv run ruff check src/ tests/

# Автоматическое исправление стилевых ошибок
fix:
	uv run ruff check src/ tests/ --fix
	uv run black src/ tests/

# Проверка форматирования (без изменений)
format-check:
	uv run black --check src/ tests/

# Проверка типизации
typecheck:
	uv run mypy src/

# -------------------------------
# Обновление и публикация
# -------------------------------

# Обновление зависимостей
update:
	uv lock --upgrade
	uv sync
	uv sync --group dev

# Показ дерева зависимостей
deps:
	uv tree --group dev

# Публикация на PyPI (использует токен из переменной окружения)
publish:
	uv publish --token $${PYPI_TOKEN}

# Публикация на тестовый PyPI
publish-test:
	uv publish --repository testpypi --token $${PYPI_TOKEN}

