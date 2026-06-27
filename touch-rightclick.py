#!/usr/bin/env python3
"""
Эмуляция ПКМ (правая кнопка мыши) через долгий тап на тачскрине.

Как это работает:
  1. Открывает тачскрин (через evdev), ждёт готовности если надо
  2. При касании — запоминает время
  3. При отпускании — если прошло > LONG_PRESS_MS И движения было < MOVE_THRESHOLD → ПКМ
  4. Если палец двигался дальше порога — это drag, отмена ПКМ

Автозапуск (~/.config/autostart/touch-rightclick.desktop):
  [Desktop Entry]
  Type=Application
  Name=Touch Right Click
  Comment=Long press → right click for touchscreen
  Exec=env DISPLAY=:0 /home/orangepi/.local/bin/touch-rightclick.py
  Hidden=false
  NoDisplay=false
  X-XFCE-Autostart-Phase=2
  X-XFCE-Autostart-Enabled=true
"""

import evdev
import evdev.ecodes as ec
import subprocess
import time
import sys
import os

# --- Конфигурация ---
LONG_PRESS_MS = 400        # мс — время удержания для ПКМ
MOVE_THRESHOLD = 20        # пикселей — допустимое дрожание пальца
DEVICE_PATH = None         # None = автоопределение, или "/dev/input/eventX"
RETRY_SECONDS = 30         # сколько секунд ждать появления тачскрина при старте
RETRY_INTERVAL = 2         # пауза между попытками найти тачскрин

# Исключения для ПКМ — не эмулировать если активно окно браузера
BROWSER_WM_CLASS = ("chromium", "chrome", "firefox", "Navigator", "Google-chrome")

# --- Логирование ---
LOG = "/tmp/touch-rightclick.log"

def log(msg):
    try:
        with open(LOG, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except:
        pass  # логирование не критично

def find_touchscreen():
    """Ищет тачскрин среди input-устройств. Возвращает путь или None."""
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
            caps = dev.capabilities(absinfo=False)
            has_touch = (
                ec.EV_KEY in caps
                and ec.BTN_TOUCH in caps.get(ec.EV_KEY, [])
                and ec.EV_ABS in caps
            )
            if has_touch:
                log(f"Найден тачскрин: {dev.name} ({dev.path})")
                return path
        except Exception:
            continue
    return None

def find_touchscreen_with_retry():
    """Ищет тачскрин, повторяя попытки если не найден сразу."""
    started = time.monotonic()
    while time.monotonic() - started < RETRY_SECONDS:
        path = find_touchscreen()
        if path:
            return path
        log(f"⏳ Тачскрин не найден, повтор через {RETRY_INTERVAL}с...")
        time.sleep(RETRY_INTERVAL)
    return None

def is_browser_active():
    """Проверяет, не в браузере ли сейчас фокус (Chromium эмулирует ПКМ сам)."""
    try:
        env_display = {"DISPLAY": os.environ.get("DISPLAY", ":0")}
        win_id = subprocess.run(
            ["xdotool", "getactivewindow"],
            capture_output=True, text=True, timeout=2,
            env={**os.environ, **env_display}
        ).stdout.strip()
        if not win_id:
            return False
        result = subprocess.run(
            ["xprop", "-id", win_id, "WM_CLASS"],
            capture_output=True, text=True, timeout=2,
            env={**os.environ, **env_display}
        ).stdout.strip()
        # WM_CLASS(STRING) = "chromium-browser", "Chromium-browser"
        for cls in BROWSER_WM_CLASS:
            if cls.lower() in result.lower():
                return True
    except Exception:
        pass
    return False


def send_rmb():
    """Клик правой кнопкой мыши через xdotool, если активное окно не браузер."""
    if is_browser_active():
        log("⏭ Пропуск ПКМ — активен браузер (он сам обрабатывает долгий тап)")
        return
    try:
        subprocess.run(
            ["xdotool", "click", "3"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}
        )
        log("ПКМ ✅")
    except Exception as e:
        log(f"❌ Ошибка xdotool: {e}")

def main():
    log("🚀 Запуск touch-rightclick.py")
    log(f"   LONG_PRESS={LONG_PRESS_MS}ms, MOVE_THRESHOLD={MOVE_THRESHOLD}px")
    log(f"   DISPLAY={os.environ.get('DISPLAY', '(не задан, будет :0)')}")

    # Найти тачскрин
    dev_path = DEVICE_PATH or find_touchscreen_with_retry()
    if not dev_path:
        log("❌ Тачскрин не найден! Выход.")
        sys.exit(1)

    device = evdev.InputDevice(dev_path)
    # ⚠️ Не используем device.grab() — это ломает ЛКМ в X
    log(f"✅ Запущен: {device.name}")

    touched = False
    touch_time = 0
    touch_x = -1
    touch_y = -1

    for event in device.read_loop():
        if event.type == ec.EV_KEY and event.code == ec.BTN_TOUCH:
            if event.value == 1:  # коснулись
                touched = True
                touch_time = time.monotonic()
                touch_x = -1
                touch_y = -1
            elif event.value == 0:  # отпустили
                if touched:
                    elapsed_ms = (time.monotonic() - touch_time) * 1000
                    if elapsed_ms >= LONG_PRESS_MS:
                        send_rmb()
                touched = False

        elif event.type == ec.EV_ABS and touched:
            if event.code == ec.ABS_X:
                if touch_x == -1:
                    touch_x = event.value
                elif abs(event.value - touch_x) > MOVE_THRESHOLD:
                    touched = False  # начался drag

            elif event.code == ec.ABS_Y:
                if touch_y == -1:
                    touch_y = event.value
                elif abs(event.value - touch_y) > MOVE_THRESHOLD:
                    touched = False  # начался drag

        # EV_SYN (0) — синхронизация, игнорируем
        # EV_MSC — вспомогательные события, игнорируем

if __name__ == "__main__":
    main()
