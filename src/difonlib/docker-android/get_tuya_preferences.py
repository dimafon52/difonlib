#!/usr/bin/env python3
"""
tuya_get_config.py
~~~~~~~~~~~~~~~~~~
Полностью автоматическое извлечение конфигурационного файла Tuya SmartLife.

Алгоритм:
  1. Поднимает Android-эмулятор в Docker-контейнере (budtmo/docker-android).
  2. Подключается к эмулятору через ADB и ждёт полной загрузки Android.
  3. Устанавливает APK Tuya SmartLife.
  4. Автоматически логинится в приложение через uiautomator2 (UI-автоматизация
     поверх ADB — без VNC, без участия человека).
  5. Извлекает файл shared_prefs/preferences_global_key*.xml, в котором
     хранятся local_key устройств, токены и региональный endpoint.
  6. Останавливает контейнер.

Зависимости:
  pip install uiautomator2

Использование:
  python3 tuya_get_config.py --email YOUR@EMAIL --password YOUR_PASS
  python3 tuya_get_config.py --email YOUR@EMAIL --password YOUR_PASS --country Israel
  python3 tuya_get_config.py --email YOUR@EMAIL --password YOUR_PASS --no-docker
  python3 tuya_get_config.py --email YOUR@EMAIL --password YOUR_PASS --keep-docker

Аргументы:
  --email       Логин аккаунта Tuya / SmartLife
  --password    Пароль аккаунта
  --country     Название страны для выбора кода (+X) на экране логина
                (default: Israel)
  --no-docker   Пропустить запуск/остановку Docker — контейнер уже запущен
  --keep-docker Не останавливать контейнер после завершения (удобно для отладки)

Отладка:
  При любой ошибке UI скрипт сохраняет скриншот (.png) и дамп иерархии
  виджетов (.xml) в текущую директорию. Имена файлов соответствуют шагу:
    tuya_01_start.png/xml        — стартовый экран приложения
    tuya_02_login_screen.png/xml — экран ввода логина/пароля
    tuya_03_filled.png/xml       — заполненная форма перед нажатием Log in
    tuya_04_after_login.png/xml  — состояние после попытки входа
    tuya_err_*.png/xml           — экран в момент конкретной ошибки
"""

import subprocess
import time
import sys
import os
import glob
import argparse
from typing import Optional

# ── Зависимости ──────────────────────────────────────────────────────────────
try:
    import uiautomator2 as u2
except ImportError:
    print("[!] uiautymator2 не установлен: pip install uiautomator2")
    sys.exit(1)

# ── Настройки ─────────────────────────────────────────────────────────────────
# ADB подключается к эмулятору внутри Docker по TCP (порт проброшен на хост).
ADB_HOST = "127.0.0.1"
ADB_PORT = 5555

# Docker-образ с предустановленным Android-эмулятором и поддержкой KVM.
DOCKER_IMAGE = "budtmo/docker-android:emulator_11.0"
CONTAINER_NAME = "android-arm-emulator-container"

# Путь к APK на хосте (относительно рабочей директории).
APK_PATH = "./apk/com.tuya.smartlife_3.6.1.apk"

# Android package name приложения.
PACKAGE = "com.tuya.smartlife"

# Путь к shared_prefs внутри эмулятора (требует root — выдаётся автоматически).
REMOTE_PREFS_DIR = f"/data/data/{PACKAGE}/shared_prefs"

# Куда сохранять извлечённые файлы на хосте.
OUTPUT_DIR = "./shared_prefs"


# ── Низкоуровневые утилиты ───────────────────────────────────────────────────


def run(
    cmd: str, check: bool = True, capture: bool = False
) -> subprocess.CompletedProcess:
    """Выполняет shell-команду с выводом в консоль.

    Args:
        cmd:     Команда для выполнения (передаётся в shell).
        check:   Бросать CalledProcessError при ненулевом коде возврата.
        capture: Перехватывать stdout/stderr вместо вывода на экран.

    Returns:
        CompletedProcess с полями returncode, stdout, stderr.
    """
    print(f"  $ {cmd}")
    kwargs = dict(shell=True, check=check)
    if capture:
        kwargs.update(capture_output=True, text=True)
    return subprocess.run(cmd, **kwargs)


def adb(
    cmd: str, capture: bool = False, check: bool = True
) -> subprocess.CompletedProcess:
    """Обёртка над run() — добавляет '-s HOST:PORT' для точного выбора устройства.

    Использование явного -s обязательно когда на хосте несколько ADB-устройств
    (физические телефоны, другие эмуляторы), иначе adb падает с
    'more than one device/emulator'.
    """
    return run(f"adb -s {ADB_HOST}:{ADB_PORT} {cmd}", capture=capture, check=check)


def wait_boot(timeout: int = 120) -> None:
    """Блокирует выполнение до полной загрузки Android.

    Опрашивает системное свойство sys.boot_completed каждые 3 секунды.
    Свойство принимает значение '1' когда все системные сервисы запущены
    и устройство готово к работе.

    Raises:
        TimeoutError: Если Android не загрузился за timeout секунд.
    """
    print("[*] Ожидание загрузки Android...")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = adb("shell getprop sys.boot_completed", capture=True, check=False)
        if r.returncode == 0 and r.stdout.strip() == "1":
            print("[+] Android загружен.")
            return
        time.sleep(3)
    raise TimeoutError("Android не загрузился за отведённое время.")


def wait_package(pkg: str, timeout: int = 60) -> None:
    """Ждёт появления пакета в списке установленных приложений.

    После успешного 'adb install' пакет не сразу виден через pm list packages —
    нужно подождать регистрации в Package Manager.

    Raises:
        TimeoutError: Если пакет не появился за timeout секунд.
    """
    print(f"[*] Ожидание пакета {pkg}...")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = adb(f"shell pm list packages {pkg}", capture=True)
        if pkg in r.stdout:
            print(f"[+] Пакет {pkg} найден.")
            return
        time.sleep(3)
    raise TimeoutError(f"Пакет {pkg} не появился.")


# ── UI-утилиты (uiautomator2) ─────────────────────────────────────────────────


def dump_ui(d: u2.Device, label: str = "ui_dump") -> None:
    """Сохраняет скриншот и XML-дамп иерархии UI для диагностики.

    Скриншот снимается через 'adb shell screencap' (надёжнее чем
    uiautomator2.screenshot, который требует записи в /data/local/tmp).
    XML-дамп получается через d.dump_hierarchy() и сразу печатает все
    текстовые метки на экране — удобно для подбора локаторов.

    Args:
        d:     Подключённое uiautomator2 устройство.
        label: Префикс имён файлов (label.png, label.xml).
    """
    try:
        remote_png = f"/data/local/tmp/{label}.png"
        adb(f"shell screencap -p {remote_png}", check=False)
        adb(f"pull {remote_png} ./{label}.png", check=False)
    except Exception as e:
        print(f"  [dbg] screenshot error: {e}")
    try:
        import re as _re

        xml = d.dump_hierarchy()
        with open(f"./{label}.xml", "w", encoding="utf-8") as f:
            f.write(xml)
        # Быстрый просмотр всех текстов на экране прямо в консоли
        texts = _re.findall(r'text="([^"]+)"', xml)
        texts = [t for t in texts if t.strip()]
        print(f"  [dbg] {label} тексты: {texts[:25]}")
    except Exception as e:
        print(f"  [dbg] dump_hierarchy error: {e}")


def click_if_exists(d: u2.Device, texts: list, timeout: int = 5) -> bool:
    """Кликает по первому найденному элементу из списка текстов.

    Перебирает тексты в порядке приоритета — первый совпавший побеждает.
    Используется для навигации по экранам с неизвестным заранее текстом кнопок
    (разные версии приложения могут использовать разные формулировки).

    Args:
        d:       Устройство uiautomator2.
        texts:   Список текстов кнопок в порядке приоритета.
        timeout: Время ожидания каждого элемента в секундах.

    Returns:
        True если элемент найден и кликнут, False иначе.
    """
    for t in texts:
        el = d(text=t)
        if el.exists(timeout=timeout):
            print(f"  [ui] click: '{t}'")
            el.click()
            time.sleep(1.5)
            return True
    return False


def wait_any(d: u2.Device, texts: list, timeout: int = 30) -> Optional[str]:
    """Ждёт появления любого из перечисленных текстов на экране.

    Используется как барьер синхронизации — ждём пока UI перейдёт
    в ожидаемое состояние, не полагаясь на фиксированные sleep().

    Args:
        d:       Устройство uiautomator2.
        texts:   Список текстов-маркеров нужного состояния экрана.
        timeout: Максимальное время ожидания в секундах.

    Returns:
        Первый найденный текст, или None если ни один не появился.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for t in texts:
            if d(text=t).exists(timeout=0):
                return t
        time.sleep(1)
    return None


def adb_input_text(value: str) -> None:
    """Вводит текст через 'adb shell input text'.

    Предпочтительнее uiautomator2.set_text() для паролей: set_text использует
    внутренний буфер обмена Android, который может искажать спецсимволы
    (!, @, #, $, ...) в зависимости от раскладки клавиатуры эмулятора.
    adb input text передаёт символы напрямую в InputMethod.

    Args:
        value: Текст для ввода. Экранируется через shlex.quote перед
               передачей в shell.
    """
    import shlex

    safe = shlex.quote(value)
    adb(f"shell input text {safe}", check=False)


def set_field(
    d: u2.Device,
    hints: list,
    value: str,
    field_index: "int | None" = None,
    use_adb_input: bool = False,
) -> bool:
    """Находит поле ввода и вводит в него текст.

    Стратегия поиска:
      1. Ищет элемент с текстом-placeholder из списка hints (основной путь).
         После клика по placeholder тот исчезает — переключается на
         focused=True EditText для ввода.
      2. Если placeholder не найден — fallback по индексу среди всех EditText
         на экране (field_index=0 для первого поля, 1 для второго и т.д.).

    Args:
        d:             Устройство uiautomator2.
        hints:         Тексты placeholder-ов в порядке приоритета.
        value:         Значение для ввода.
        field_index:   Индекс EditText как fallback (None = не использовать).
        use_adb_input: Использовать adb_input_text вместо set_text
                       (рекомендуется для паролей).

    Returns:
        True если поле найдено и заполнено, False иначе.
    """
    for hint in hints:
        el = d(text=hint)
        if el.exists(timeout=3):
            print(f"  [ui] set_text field='{hint}'")
            el.click()
            time.sleep(0.8)
            active = d(focused=True, className="android.widget.EditText")
            if active.exists(timeout=3):
                active.clear_text()
                time.sleep(0.3)
                if use_adb_input:
                    adb_input_text(value)
                else:
                    active.set_text(value)
            else:
                if use_adb_input:
                    adb_input_text(value)
                else:
                    el.set_text(value)
            time.sleep(0.5)
            return True
    # Fallback по индексу
    if field_index is not None:
        fields = d(className="android.widget.EditText")
        count = fields.count
        print(f"  [ui] EditText по индексу {field_index} (всего: {count})")
        if count > field_index:
            fields[field_index].click()
            time.sleep(0.5)
            fields[field_index].clear_text()
            time.sleep(0.3)
            if use_adb_input:
                adb_input_text(value)
            else:
                fields[field_index].set_text(value)
            return True
    return False


# ── Основные шаги ─────────────────────────────────────────────────────────────


def start_docker() -> None:
    """Запускает Docker-контейнер с Android-эмулятором.

    Сначала останавливает контейнер с тем же именем если он уже запущен
    (check=False — не падать если контейнера нет).
    Флаги запуска:
      --rm          Автоматически удалить контейнер после остановки.
      --privileged  Необходим для доступа к /dev/kvm (аппаратная виртуализация).
      --device /dev/kvm  Пробрасывает KVM в контейнер для ускорения эмулятора.
      -p 5555:5555  ADB TCP порт для подключения с хоста.
      -p 6080:6080  VNC через браузер (для ручной отладки, не используется скриптом).
    """
    print("\n[1/6] Запуск Docker-контейнера...")
    run(f"docker container stop {CONTAINER_NAME}", check=False)
    time.sleep(2)
    run(
        f"docker run --rm --privileged -d "
        f"-p 6080:6080 -p {ADB_PORT}:{ADB_PORT} "
        f"-e EMULATOR_DEVICE='Samsung Galaxy S10' "
        f"-e WEB_VNC=true "
        f"--device /dev/kvm "
        f"--name {CONTAINER_NAME} "
        f"{DOCKER_IMAGE}"
    )
    time.sleep(15)  # Docker нужно время на старт до того как ADB сможет подключиться


def wait_port(host: str, port: int, timeout: int = 120) -> None:
    """Ждёт открытия TCP-порта — признак готовности ADB в контейнере.

    Docker поднимает эмулятор асинхронно: контейнер стартует быстро,
    но ADB-порт открывается только когда QEMU и adbd внутри готовы.
    Фиксированный sleep(15) ненадёжен на медленных машинах.

    Raises:
        TimeoutError: Если порт не открылся за timeout секунд.
    """
    import socket

    print(f"[*] Ожидание TCP {host}:{port}...")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                print(f"[+] Порт {port} открыт.")
                return
        except OSError:
            time.sleep(2)
    raise TimeoutError(f"Порт {host}:{port} не открылся за {timeout} сек.")


def connect_adb() -> None:
    """Устанавливает ADB-соединение с эмулятором и получает root.

    Последовательность:
      1. kill-server / start-server — чистый старт ADB daemon на хосте.
      2. wait_port — ждём реального открытия TCP-порта (надёжнее sleep).
      3. adb connect — TCP-подключение, повторяем до успеха.
      4. wait_boot — ждём полной загрузки Android.
      5. adb root — перезапускает adbd в контейнере от root.
         Необходимо для доступа к /data/data/* (shared_prefs).
         check=False — 'adbd is already running as root' возвращает код 1.
      6. Повторный connect — после root adbd переподключается.
    """
    print("\n[2/6] Подключение ADB...")
    run("adb kill-server", check=False)
    time.sleep(1)
    run("adb start-server")

    # Ждём реального открытия порта — не полагаемся на sleep
    wait_port(ADB_HOST, ADB_PORT, timeout=120)

    # adb connect может не сработать с первого раза — повторяем
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        r = run(f"adb connect {ADB_HOST}:{ADB_PORT}", capture=True, check=False)
        if "connected" in r.stdout and "failed" not in r.stdout:
            break
        print("  [*] Повтор adb connect...")
        time.sleep(3)
    else:
        raise RuntimeError(f"Не удалось подключиться к {ADB_HOST}:{ADB_PORT}")

    wait_boot()
    adb("root", check=False)
    time.sleep(2)
    run(f"adb connect {ADB_HOST}:{ADB_PORT}", check=False)


def wait_package_manager(timeout: int = 120) -> None:
    """Ждёт готовности Android Package Manager.

    sys.boot_completed=1 не гарантирует готовность PM — на слабом железе
    (< 4 GiB RAM) сервисы поднимаются ещё 30-60 сек после boot.
    Признак готовности: 'pm path android' возвращает непустой результат.
    """
    print("[*] Ожидание Package Manager...")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = adb("shell pm path android", capture=True, check=False)
        if r.returncode == 0 and "package:" in r.stdout:
            print("[+] Package Manager готов.")
            return
        time.sleep(3)
    raise TimeoutError("Package Manager не готов за отведённое время.")


def install_apk() -> None:
    """Устанавливает APK Tuya SmartLife в эмулятор.

    Флаг -r разрешает переустановку поверх существующей версии.
    На слабом железе Package Manager может быть не готов сразу после
    boot_completed — ждём его отдельно, затем повторяем install при ошибке
    'Broken pipe' (PM ещё занят инициализацией).
    """
    print("\n[3/6] Установка APK...")
    if not os.path.exists(APK_PATH):
        raise FileNotFoundError(f"APK не найден: {APK_PATH}")

    wait_package_manager()

    # Повторяем install — Broken pipe возможен даже после готовности PM
    for attempt in range(1, 4):
        print(f"  [*] Попытка установки {attempt}/3...")
        r = adb(f"install -r {APK_PATH}", capture=True, check=False)
        output = r.stdout + r.stderr
        if r.returncode == 0 and "Success" in output:
            print("[+] APK установлен.")
            break
        print(f"  [!] Ошибка: {output.strip()}")
        if attempt < 3:
            print("  [*] Ждём 10 сек и повторяем...")
            time.sleep(10)
    else:
        raise RuntimeError(
            f"Не удалось установить APK после 3 попыток. Последний вывод:\n{output}"
        )

    wait_package(PACKAGE)
    time.sleep(3)


def login_tuya(email: str, password: str, country: str = "Israel") -> None:
    """Автоматически логинится в Tuya SmartLife через UI-автоматизацию.

    Использует uiautomator2 — Python-библиотеку поверх ADB UIAutomator2 API.
    Не требует VNC или физического доступа к экрану.

    Полный flow экранов (версия APK 3.6.1):
      [Стартовый экран]  Register | Log in with existing account
           ↓ клик "Log in with existing account"
      [Privacy Policy]   Disagree | Agree
           ↓ клик "Agree"
      [Loading...]
           ↓ ждём появления полей ввода
      [Экран логина]     страна (+X) | email | password | Log in
           ↓ выбор страны → ввод email → ввод пароля → клик "Log in"
      [Попап геолокации] While using the app | Only this time | Deny
           ↓ клик "Deny"
      [Главный экран]    My Home / All Devices  ← успех

    Args:
        email:    Email или номер телефона аккаунта Tuya.
        password: Пароль аккаунта (вводится через adb input text для
                  корректной обработки спецсимволов).
        country:  Название страны для выбора кода (+X). Используется поиском
                  на экране выбора страны.

    Raises:
        RuntimeError: При любой ошибке UI сохраняет диагностические файлы
                      и бросает исключение с указанием на них.
    """
    print("\n[4/6] Автологин в TuyaSmartLife...")

    d = u2.connect(f"{ADB_HOST}:{ADB_PORT}")
    d.implicitly_wait(10)

    # ── Запуск приложения ────────────────────────────────────────────────────
    print("  [*] Запуск приложения...")
    d.app_start(
        PACKAGE, stop=True
    )  # stop=True — принудительно убить если было запущено

    # Ждём появления любого известного элемента стартового экрана
    first = wait_any(
        d,
        [
            "Log In",
            "Login",
            "Sign In",
            "Get Started",
            "Create Account",
            "Register",
            "Email",
            "Email/Phone Number",
        ],
        timeout=40,
    )

    if first is None:
        dump_ui(d, "tuya_start")
        raise RuntimeError(
            "Приложение не показало стартовый экран. "
            "Смотри tuya_start.png / tuya_start.xml"
        )

    print(f"  [*] Первый элемент на экране: '{first}'")
    dump_ui(d, "tuya_01_start")

    # ── Переход на экран логина ───────────────────────────────────────────────
    clicked_login = click_if_exists(
        d,
        [
            "Log in with existing account",
            "Sign In",
            "Log In",
            "Login",
            "Already have an account?",
            "Existing User",
        ],
        timeout=10,
    )
    if not clicked_login:
        print("  [*] Кнопка входа не найдена — возможно уже на экране ввода")

    # ── Privacy Policy ────────────────────────────────────────────────────────
    # Появляется асинхронно после клика — может показаться во время Loading...
    # Ждём активно: как только появился "Agree" — кликаем и выходим из цикла.
    # Выходим досрочно если уже виден экран логина (поле ввода или код страны).
    def accept_privacy_if_shown(d: u2.Device, timeout: int = 15) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if d(text="Agree").exists(timeout=0):
                print("  [*] Privacy Policy — клик Agree")
                d(text="Agree").click()
                time.sleep(1)
                return True
            if d(text="Mobile number/e-mail address").exists(timeout=0):
                return False
            if d(textContains="+").exists(timeout=0):
                return False
            time.sleep(1)
        return False

    accept_privacy_if_shown(d, timeout=20)

    # Ждём окончания Loading... — барьер перед вводом данных
    print("  [*] Ожидание экрана логина...")
    login_ready = wait_any(
        d,
        [
            "Mobile number/e-mail address",
            "Password",
            "Log in",
        ],
        timeout=30,
    )
    if not login_ready:
        dump_ui(d, "tuya_02_login_screen")
        raise RuntimeError(
            "Экран логина не появился. Смотри tuya_02_login_screen.png/xml"
        )

    dump_ui(d, "tuya_02_login_screen")

    # ── Выбор страны ─────────────────────────────────────────────────────────
    # По умолчанию стоит "USA +1". Кликаем по строке с "+" → открывается
    # список стран с поиском → вводим название → выбираем первый результат.
    if country:
        print(f"  [*] Смена страны на: {country}")
        country_el = d(textContains="+")
        if country_el.exists(timeout=5):
            country_el.click()
            time.sleep(2)
            search = d(text="Search")
            if search.exists(timeout=5):
                search.click()
                time.sleep(0.5)
                d(focused=True).set_text(country)
                time.sleep(2)
            results = d(className="android.widget.TextView", textContains=country)
            if results.exists(timeout=5):
                results.click()
                time.sleep(1.5)
            else:
                d.press("back")
                print(f"  [!] Страна '{country}' не найдена, оставляем текущую")

    # ── Ввод email ────────────────────────────────────────────────────────────
    print("  [*] Ввод email...")
    ok = set_field(
        d,
        hints=[
            "Mobile number/e-mail address",
            "Email",
            "Email/Phone Number",
            "Account",
            "Phone/Email",
        ],
        value=email,
        field_index=0,
    )
    if not ok:
        dump_ui(d, "tuya_err_email")
        raise RuntimeError("Поле email не найдено. Смотри tuya_err_email.png/xml")
    time.sleep(0.5)

    # ── Ввод пароля ───────────────────────────────────────────────────────────
    # use_adb_input=True — обход проблемы искажения спецсимволов через clipboard
    print("  [*] Ввод пароля...")
    ok = set_field(
        d,
        hints=["Password", "Enter password"],
        value=password,
        field_index=1,
        use_adb_input=True,
    )
    if not ok:
        dump_ui(d, "tuya_err_password")
        raise RuntimeError("Поле пароля не найдено. Смотри tuya_err_password.png/xml")

    d.press("back")  # скрыть экранную клавиатуру перед нажатием кнопки
    time.sleep(0.5)
    dump_ui(d, "tuya_03_filled")

    # ── Нажатие кнопки Log in ─────────────────────────────────────────────────
    # На экране два TextView с текстом "Log in": заголовок страницы (не кликабельный)
    # и кнопка (clickable=True). Явный фильтр по clickable исключает заголовок.
    print("  [*] Нажатие кнопки входа...")
    btn = d(text="Log in", clickable=True)
    if btn.exists(timeout=10):
        print("  [ui] click: кнопка 'Log in' (clickable=True)")
        btn.click()
    else:
        # Fallback: берём последний элемент с таким текстом (кнопка всегда ниже заголовка)
        els = d(text="Log in")
        count = els.count
        print(f"  [ui] Log in элементов: {count}, кликаем последний")
        if count > 0:
            els[count - 1].click()
        else:
            dump_ui(d, "tuya_err_submit")
            raise RuntimeError(
                "Кнопка входа не найдена. Смотри tuya_err_submit.png/xml"
            )

    # ── Ожидание результата авторизации ──────────────────────────────────────
    print("  [*] Ожидание авторизации и попапов (60 сек)...")
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        # Немедленно реагируем на ошибку — не ждём зря 60 секунд
        if d(text="Incorrect account or password").exists(timeout=0):
            dump_ui(d, "tuya_err_wrong_password")
            raise RuntimeError(
                "Неверный логин или пароль ('Incorrect account or password'). "
                "Проверьте --email и --password."
            )
        # Успех — появился главный экран
        if wait_any(d, ["My Home", "My home", "All Devices"], timeout=2):
            break
        # Отклоняем попап геолокации и другие системные разрешения
        click_if_exists(
            d,
            ["Deny", "Don't allow", "Only this time", "While using the app"],
            timeout=1,
        )
        click_if_exists(d, ["OK", "Got it"], timeout=1)

    dump_ui(d, "tuya_04_after_login")

    success_marker = wait_any(
        d, ["My Home", "My home", "All Devices", "Smart", "Me"], timeout=10
    )
    if success_marker:
        print(f"  [+] Авторизация успешна (маркер: '{success_marker}').")
    else:
        if wait_any(d, ["Log in", "Log In", "Login"], timeout=3):
            raise RuntimeError(
                "Авторизация не прошла. Смотри tuya_04_after_login.png/xml"
            )
        print("  [!] Маркер главного экрана не найден — продолжаем.")

    # Даём приложению время записать конфиг на диск.
    # shared_prefs сохраняются не мгновенно после логина.
    time.sleep(15)


def pull_prefs() -> list:
    """Извлекает директорию shared_prefs из эмулятора на хост.

    Использует 'adb pull' для копирования всей директории.
    Ищет файл preferences_global_key*.xml — в нём хранятся
    local_key устройств, токены сессии и региональный API endpoint.

    Returns:
        Список путей к найденным XML-файлам.

    Raises:
        FileNotFoundError: Если целевые файлы не найдены после pull.
    """
    print("\n[5/6] Извлечение shared_prefs...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    adb(f"pull {REMOTE_PREFS_DIR} {OUTPUT_DIR}")

    files = glob.glob(f"{OUTPUT_DIR}/**/preferences_global_key*.xml", recursive=True)
    if not files:
        files = glob.glob(f"{OUTPUT_DIR}/**/*.xml", recursive=True)

    if not files:
        raise FileNotFoundError(f"preferences_global_key*.xml не найден в {OUTPUT_DIR}")

    print(f"[+] Найдено файлов: {len(files)}")
    for f in files:
        print(f"    {f}")
    return files


def stop_docker() -> None:
    """Останавливает Docker-контейнер с эмулятором."""
    print("\n[6/6] Остановка контейнера...")
    run(f"docker container stop {CONTAINER_NAME}", check=False)
    print("[+] Готово.")


# ── Точка входа ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Автоматическое извлечение Tuya SmartLife конфигурации (local_key устройств)."
    )
    parser.add_argument(
        "--email", required=True, help="Email или телефон аккаунта Tuya/SmartLife"
    )
    parser.add_argument("--password", required=True, help="Пароль аккаунта")
    parser.add_argument(
        "--country",
        default="Israel",
        help="Страна для выбора кода (+X) на экране логина (default: Israel)",
    )
    parser.add_argument(
        "--no-docker",
        action="store_true",
        help="Не запускать/останавливать Docker — контейнер уже запущен",
    )
    parser.add_argument(
        "--keep-docker",
        action="store_true",
        help="Не останавливать контейнер после завершения (удобно для отладки)",
    )
    args = parser.parse_args()

    try:
        if not args.no_docker:
            start_docker()
        connect_adb()
        install_apk()
        login_tuya(args.email, args.password, args.country)
        files = pull_prefs()
        print("\n[✓] Файлы конфигурации сохранены:")
        for f in files:
            print(f"    {f}")
    finally:
        if not args.no_docker and not args.keep_docker:
            stop_docker()


if __name__ == "__main__":
    main()
