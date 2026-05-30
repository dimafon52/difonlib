#!/usr/bin/env python3
"""
tuya_get_config.py
Автоматический запуск TuyaSmartLife в Android-эмуляторе (Docker),
логин через uiautomator2 и извлечение shared_prefs/preferences_global_key*.xml
"""

import subprocess
import time
import sys
import os
import glob
import argparse

# ── Зависимости ──────────────────────────────────────────────────────────────
try:
    import uiautomator2 as u2
except ImportError:
    print("[!] uiautomator2 не установлен: pip install uiautomator2")
    sys.exit(1)

# ── Настройки ────────────────────────────────────────────────────────────────
ADB_HOST = "127.0.0.1"
ADB_PORT = 5555
DOCKER_IMAGE = "budtmo/docker-android:emulator_11.0"
CONTAINER_NAME = "android-arm-emulator-container"
APK_PATH = "./apk/com.tuya.smartlife_3.6.1.apk"
PACKAGE = "com.tuya.smartlife"
REMOTE_PREFS_DIR = f"/data/data/{PACKAGE}/shared_prefs"
OUTPUT_DIR = "./shared_prefs"


# ── Утилиты ──────────────────────────────────────────────────────────────────
def run(cmd, check=True, capture=False):
    print(f"  $ {cmd}")
    kwargs = dict(shell=True, check=check)
    if capture:
        kwargs.update(capture_output=True, text=True)
    return subprocess.run(cmd, **kwargs)


def adb(cmd, capture=False, check=True):
    return run(f"adb -s {ADB_HOST}:{ADB_PORT} {cmd}", capture=capture, check=check)


def wait_boot(timeout=120):
    """Ждём полной загрузки Android."""
    print("[*] Ожидание загрузки Android...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = adb("shell getprop sys.boot_completed", capture=True)
        if r.returncode == 0 and r.stdout.strip() == "1":
            print("[+] Android загружен.")
            return True
        time.sleep(3)
    raise TimeoutError("Android не загрузился за отведённое время.")


def wait_package(pkg, timeout=60):
    """Ждём появления пакета в системе."""
    print(f"[*] Ожидание пакета {pkg}...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = adb(f"shell pm list packages {pkg}", capture=True)
        if pkg in r.stdout:
            print(f"[+] Пакет {pkg} найден.")
            return True
        time.sleep(3)
    raise TimeoutError(f"Пакет {pkg} не появился.")


# ── Шаги ─────────────────────────────────────────────────────────────────────
def start_docker():
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
    time.sleep(15)  # время на старт Docker


def connect_adb():
    print("\n[2/6] Подключение ADB...")
    run("adb kill-server", check=False)
    time.sleep(1)
    run("adb start-server")
    time.sleep(1)
    run(f"adb connect {ADB_HOST}:{ADB_PORT}")
    wait_boot()
    adb("root", check=False)  # всегда через -s, игнорируем ошибку если уже root
    time.sleep(2)
    run(f"adb connect {ADB_HOST}:{ADB_PORT}")  # переподключение после root


def install_apk():
    print("\n[3/6] Установка APK...")
    if not os.path.exists(APK_PATH):
        raise FileNotFoundError(f"APK не найден: {APK_PATH}")
    adb(f"install -r {APK_PATH}")
    wait_package(PACKAGE)
    time.sleep(3)


def dump_ui(d, label="ui_dump"):
    """Сохраняет скриншот + XML дамп UI для отладки."""
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
        texts = _re.findall(r'text="([^"]+)"', xml)
        texts = [t for t in texts if t.strip()]
        print(f"  [dbg] {label} тексты: {texts[:25]}")
    except Exception as e:
        print(f"  [dbg] dump_hierarchy error: {e}")


def click_if_exists(d, texts, timeout=5):
    """Кликает первый найденный элемент из списка текстов. Возвращает True если нашёл."""
    for t in texts:
        el = d(text=t)
        if el.exists(timeout=timeout):
            print(f"  [ui] click: '{t}'")
            el.click()
            time.sleep(1.5)
            return True
    return False


def wait_any(d, texts, timeout=30):
    """Ждёт появления любого из текстов на экране. Возвращает найденный текст или None."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for t in texts:
            if d(text=t).exists(timeout=0):
                return t
        time.sleep(1)
    return None


def set_field(d, hints, value, field_index=None):
    """Вводит текст в поле по hint-тексту (placeholder) или по индексу EditText."""
    for hint in hints:
        el = d(text=hint)
        if el.exists(timeout=3):
            print(f"  [ui] set_text field='{hint}'")
            el.click()
            time.sleep(0.5)
            # После клика placeholder исчезает — ищем активный EditText
            active = d(focused=True, className="android.widget.EditText")
            if active.exists(timeout=3):
                active.clear_text()
                active.set_text(value)
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
            time.sleep(0.3)
            fields[field_index].clear_text()
            fields[field_index].set_text(value)
            return True
    return False


def login_tuya(email: str, password: str, country: str = "Israel"):
    """Автоматический логин через uiautomator2."""
    print("\n[4/6] Автологин в TuyaSmartLife...")

    d = u2.connect(f"{ADB_HOST}:{ADB_PORT}")
    d.implicitly_wait(10)

    # ── Запуск приложения ────────────────────────────────────────────────────
    print("  [*] Запуск приложения...")
    d.app_start(PACKAGE, stop=True)

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
    dump_ui(d, "tuya_01_start")  # покажет все тексты на экране

    # ── Кнопка входа на стартовом экране ────────────────────────────────────
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

    # ── Privacy Policy может появиться в любой момент — ждём и принимаем ────
    def accept_privacy_if_shown(d, timeout=15):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if d(text="Agree").exists(timeout=0):
                print("  [*] Privacy Policy — клик Agree")
                d(text="Agree").click()
                time.sleep(1)
                return True
            # Если уже на экране логина (есть поле ввода) — выходим
            if d(text="Mobile number/e-mail address").exists(timeout=0):
                return False
            if d(textContains="+").exists(timeout=0):
                return False
            time.sleep(1)
        return False

    accept_privacy_if_shown(d, timeout=20)

    # Ждём окончания Loading... и появления экрана логина
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

    # ── Смена страны (USA +1 → нужная страна) ────────────────────────────────
    if country:
        print(f"  [*] Смена страны на: {country}")
        # Кликаем по строке с кодом страны (содержит "+")
        country_el = d(textContains="+")
        if country_el.exists(timeout=5):
            country_el.click()
            time.sleep(2)
            # Экран выбора страны — ищем поле Search
            search = d(text="Search")
            if search.exists(timeout=5):
                search.click()
                time.sleep(0.5)
                d(focused=True).set_text(country)
                time.sleep(2)
            # Кликаем первый результат
            results = d(className="android.widget.TextView", textContains=country)
            if results.exists(timeout=5):
                results.click()
                time.sleep(1.5)
            else:
                d.press("back")  # отмена если не нашли
                print(f"  [!] Страна '{country}' не найдена, оставляем текущую")

    # ── Ввод email / телефона ────────────────────────────────────────────────
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

    # ── Ввод пароля ──────────────────────────────────────────────────────────
    print("  [*] Ввод пароля...")
    ok = set_field(
        d, hints=["Password", "Enter password"], value=password, field_index=1
    )
    if not ok:
        dump_ui(d, "tuya_err_password")
        raise RuntimeError("Поле пароля не найдено. Смотри tuya_err_password.png/xml")

    d.press("back")  # скрыть клавиатуру
    time.sleep(0.5)
    dump_ui(d, "tuya_03_filled")

    # ── Нажать Log in ─────────────────────────────────────────────────────────
    print("  [*] Нажатие кнопки входа...")
    # На экране два элемента "Log in": заголовок (не кликабельный) и кнопка.
    # Ищем именно кликабельную кнопку.
    btn = d(text="Log in", clickable=True)
    if btn.exists(timeout=10):
        print("  [ui] click: кнопка 'Log in' (clickable=True)")
        btn.click()
    else:
        # Fallback: все Log in элементы — берём последний (кнопка внизу)
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

    # ── Попап геолокации и прочие разрешения ─────────────────────────────────
    print("  [*] Ожидание авторизации и попапов (60 сек)...")
    deadline = time.time() + 60
    while time.time() < deadline:
        # Успех — главный экран
        if wait_any(d, ["My Home", "My home", "All Devices", "My Home"], timeout=2):
            break
        # Отклоняем попапы разрешений
        click_if_exists(
            d,
            ["Deny", "Don't allow", "Only this time", "While using the app"],
            timeout=1,
        )
        # Принимаем если нужно
        click_if_exists(d, ["OK", "Got it"], timeout=1)

    dump_ui(d, "tuya_04_after_login")

    success_marker = wait_any(
        d, ["My Home", "My home", "All Devices", "Smart", "Me", "My Home"], timeout=10
    )
    if success_marker:
        print(f"  [+] Авторизация успешна (маркер: '{success_marker}').")
    else:
        if wait_any(d, ["Log in", "Log In", "Login"], timeout=3):
            raise RuntimeError(
                "Авторизация не прошла. Смотри tuya_04_after_login.png/xml"
            )
        print("  [!] Маркер главного экрана не найден — продолжаем.")

    time.sleep(15)  # даём время на сохранение shared_prefs на диск


def pull_prefs():
    print("\n[5/6] Извлечение shared_prefs...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    adb(f"pull {REMOTE_PREFS_DIR} {OUTPUT_DIR}")

    files = glob.glob(f"{OUTPUT_DIR}/**/preferences_global_key*.xml", recursive=True)
    if not files:
        # Иногда pull кладёт в подпапку shared_prefs/shared_prefs
        files = glob.glob(f"{OUTPUT_DIR}/**/*.xml", recursive=True)

    if not files:
        raise FileNotFoundError(f"preferences_global_key*.xml не найден в {OUTPUT_DIR}")

    print(f"[+] Найдено файлов: {len(files)}")
    for f in files:
        print(f"    {f}")
    return files


def stop_docker():
    print("\n[6/6] Остановка контейнера...")
    run(f"docker container stop {CONTAINER_NAME}", check=False)
    print("[+] Готово.")


# ── Точка входа ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Автоматическое извлечение Tuya shared_prefs"
    )
    parser.add_argument("--email", required=True, help="Tuya аккаунт email")
    parser.add_argument("--password", required=True, help="Tuya пароль")
    parser.add_argument(
        "--country", default="Israel", help="Страна для выбора (default: Israel)"
    )
    parser.add_argument(
        "--no-docker",
        action="store_true",
        help="Не запускать/останавливать Docker (контейнер уже запущен)",
    )
    parser.add_argument(
        "--keep-docker",
        action="store_true",
        help="Не останавливать Docker после завершения",
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
