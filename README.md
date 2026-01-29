
Источник: [ChatGPT](https://chatgpt.com/c/69037b0e-fd30-8327-b05f-bf9d1a439315).

# Steps to create a Python library:
   1. make setup
   2. edit yours sources: 
      * src/difonlib/
      * tests/
   3. make test
   4. make    *- see Makefile all*

---

# Add my library

### ✅ Правильный формат SSH-URL для Bitbucket

Используй один из **этих трёх корректных вариантов** 👇

#### Вариант 1 (рекомендуется)

```bash
uv add "git+ssh://git@bitbucket.org/dimafon_devel/difonlib.git"
```

#### Вариант 2 (эквивалентно, если используешь токен или https)

```bash
uv add "git+https://bitbucket.org/dimafon_devel/difonlib.git"
uv add  git+https://bitbucket.org/dimafon_devel/difonlib.git@main
```

#### Вариант 3 — с конкретной веткой или тегом

```bash
uv add "git+ssh://git@bitbucket.org/dimafon_devel/difonlib.git@main"
uv add "git+ssh://git@bitbucket.org/dimafon_devel/difonlib.git@v0.1.0"
```

#### Вариант 4 — с commit
```bash
uv add git+ssh://git@bitbucket.org/dimafon_devel/difonlib.git@a1b2c3d

```

## ⚙️ Совет: зафиксируй версию

Чтобы всегда использовать стабильную версию:

```bash
git tag -a v0.1.0 -m "First release"
git push origin v0.1.0
```

и затем в зависимостях указывай:

```toml
"difonlib @ git+ssh://git@bitbucket.org/dimafon_devel/difonlib.git@v0.1.0"
```


---


### 💡 Почему не работает `bitbucket.org:repo`

Формат `git@bitbucket.org:repo.git` — это *короткий SCP-стиль* (работает в `git clone`, но не в стандартных URL-парсерах, таких как `uv`, `pip`, `hatch` и т.п.).
`uv` ожидает полноценный URI (`git+ssh://.../repo.git`).

---

### ✅ Проверка

После успешного добавления:

```bash
uv tree
```

ты должен увидеть примерно:

```
test_difonlib v0.1.0
└── difonlib v0.1.0 (from git+ssh://git@bitbucket.org/dimafon_devel/difonlib.git@main)
```

Отлично 👌
Давай сделаем **современную схему** — Python-библиотека с упаковкой и публикацией через **`uv`**, без `setuptools` и `setup.py`.
`uv` — это новый, сверхбыстрый инструмент от Astral (авторы `ruff`, `uvicorn`, `pip-tools`), который полностью заменяет `pip`, `build`, `venv` и даже `hatch`.

---

## 🧱 1. Структура проекта

Допустим, библиотека называется `mylib`.

```
mylib/
├── src/
│   └── mylib/
│       ├── __init__.py
│       ├── core.py
│       └── utils.py
├── tests/
│   └── test_core.py
├── README.md
├── LICENSE
├── pyproject.toml
└── uv.lock
```

> ✅ Подход `src/` предотвращает случайные импорты не из пакета при тестах.
> ✅ `uv.lock` создаётся автоматически при первой установке зависимостей.

---

## ⚙️ 2. `pyproject.toml` — современный минимализм

```toml
[project]
name = "mylib"
version = "0.1.0"
description = "My awesome modern Python library"
readme = "README.md"
requires-python = ">=3.9"
license = { text = "MIT" }

authors = [
  { name = "Dmitry Fonary", email = "you@example.com" }
]

dependencies = [
  "requests>=2.31",
]

[project.urls]
Homepage = "https://github.com/username/mylib"
Issues = "https://github.com/username/mylib/issues"

[tool.uv]
# Здесь uv хранит настройки окружения, зависимостей и сборки
package = true

[tool.pytest.ini_options]
addopts = "-v"
testpaths = ["tests"]
```

---

## 🚀 3. Установка и инициализация окружения

1. Установи `uv`, если ещё не установлен:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Инициализируй окружение и зависимости:

   ```bash
   uv init mylib
   cd mylib
   uv add --dev pytest
   ```

   Это создаст `uv.lock` и виртуальное окружение `.venv/`.

## 🧪 4. Тестирование

Файл `tests/test_core.py`:

```python
from mylib.core import double

def test_double():
    assert double(2) == 4
```

Запуск тестов:

```bash
uv run pytest
```

---

## 📦 5. Сборка библиотеки

Собрать wheel и sdist:

```bash
uv build
```

Результат:

```
dist/
 ├── mylib-0.1.0.tar.gz
 └── mylib-0.1.0-py3-none-any.whl
```

---

## 📤 6. Публикация

1. Создай API-токен на [PyPI](https://pypi.org/manage/account/token/).

2. Опубликуй:

   ```bash
   uv publish --token pypi-AgEIcH...
   ```

   или для теста:

   ```bash
   uv publish --repository testpypi --token pypi-AgEIcH...
   ```

---

## 📁 7. Пример содержимого `src/mylib/core.py`

```python
def double(x: int) -> int:
    """Удваивает число."""
    return x * 2
```

---

## 💡 8. Опционально: добавить `py.typed`

Если библиотека типизирована — добавь пустой файл `py.typed` в `src/mylib/`:

```bash
touch src/mylib/py.typed
```

И включи его в `pyproject.toml`:

```toml
[tool.uv.include]
files = ["src/mylib/py.typed", "README.md", "LICENSE"]
```

---

## 🧩 9. Пример полезных команд

| Цель                   | Команда              |
| ---------------------- | -------------------- |
| Установка зависимостей | `uv sync`            |
| Добавить пакет         | `uv add rich`        |
| Удалить пакет          | `uv remove requests` |
| Сборка пакета          | `uv build`           |
| Запуск тестов          | `uv run pytest`      |
| Публикация             | `uv publish`         |

---

## Problems

``` bash
uv run mypy src/ src/wwwww/main.py:4: error: Skipping analyzing "difonlib.utils": module is installed, but missing library stubs or py.typed marker [import-untyped] src/wwwww/main.py:4: note: See https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-imports Found 1 error in 1 file (checked 1 source file) make: *** [Makefile:59: typecheck] Error 1 [dima@archryzen wwwww]$
```

Отлично, что ты запустил `mypy` — сообщение очень типичное для **своих библиотек**, установленных через `uv` или `pip`, но без метки типизации.

---

## 🔍 Что происходит

`mypy` пишет:

```
Skipping analyzing "difonlib.utils": module is installed, but missing library stubs or py.typed marker
```

👉 Это значит, что `difonlib` **установлена как пакет**, но `mypy` не видит в ней файла `py.typed`, который сообщает:

> «Эта библиотека содержит аннотации типов (type hints), и их можно проверять».

---

## ✅ Решение: добавить `py.typed`

1. Внутри твоего пакета (`src/difonlib/`) создай пустой файл:

```
src/difonlib/py.typed
```

(просто пустой файл без расширения)

2. Убедись, что он включается в сборку:
   В `pyproject.toml` добавь под `[tool.uv]` секцию для включения не-Python файлов:

```toml
[tool.uv]
package = true
include = ["src/difonlib/py.typed"]
```

или, если используешь PEP 621-style (через `project`):

```toml
[project]
name = "difonlib"
version = "0.1.0"
description = "Python utils"
readme = "README.md"
requires-python = ">=3.10"

[tool.uv]
package = true

[tool.setuptools.package-data]
difonlib = ["py.typed"]
```

---

## 🧩 Альтернатива (временный обход)

Если пока ты не хочешь размечать библиотеку как типизированную, можно отключить предупреждение:

```bash
uv run mypy src/ --ignore-missing-imports
```

или в `Makefile`:

```makefile
typecheck:
	uv run mypy src/ --ignore-missing-imports
```

но это **скрывает** все ошибки в импортируемых пакетах, включая твой собственный — не рекомендуется надолго.

---

## ⚙️ После исправления

После добавления `py.typed` — перестрой пакет:

```bash
make build
uv sync --group dev
```

и снова проверь:

```bash
uv run mypy src/
```

📜 Теперь вывод должен быть чистым:

```
Success: no issues found in 1 source file
```

---

