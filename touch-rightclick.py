#!/usr/bin/env python3
"""
Эмуляция ПКМ (правая кнопка мыши) через долгий тап на тачскрине.
Использует evdev для чтения событий тачскрина и xdotool для эмуляции клика.

Установка автозапуска:
  1. Поместить скрипт: ~/.local/bin/touch-rightclick.py
  2. chmod +x ~/.local/bin/touch-rightclick.py
  3. Добавить в автозапуск XFCE (~/.config/autostart/touch-rightclick.desktop):
     [Desktop Entry]
     Type=Application
     Name=Touch Right Click
     Exec=/home/orangepi/.local/bin/touch-rightclick.py
     Hidden=false
     NoDisplay=false
     X-XFCE-Autostart-Phase=2
     X-XFCE-Autostart-Enabled=true
"""

import evdev
import subprocess
import time
import sys
import os

# --- Конфигурация ---
LONG_PRESS_MS = 400       # мс — время для ПКМ
MOVE_THRESHOLD = 20       # пикселей — допустимое движение (для исключения drag)
DEVICE_PATH = None        # автоопределение, или задать вручную: "/dev/input/event6"

# --- Логирование ---
LOG = "/tmp/touch-rightclick.log"

def log(msg):
    with open(LOG, "a") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

def find_touchscreen():
    """Находит первое устройство с EV_ABS и BTN_TOUCH."""
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
            caps = dev.capabilities(absinfo=False)
            # Проверяем, что это тачскрин: есть EV_ABS + BTN_TOUCH
            has_abs = evdev.ecodes.EV_ABS in caps
            has_touch = evdev.ecodes.EV_KEY in caps and evdev.ecodes.BTN_TOUCH in caps[evdev.ecodes.EV_KEY]
            if has_abs and has_touch:
                log(f"Найден тачскрин: {dev.name} ({dev.path})")
                return path
        except:
            pass
    return None

def send_rmb():
    """Эмулирует клик правой кнопкой мыши через xdotool."""
    try:
        subprocess.run(
            ["xdotool", "click", "3"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "DISPLAY": ":0"}
        )
        log("ПКМ ✅")
    except Exception as e:
        log(f"Ошибка xdotool: {e}")

def main():
    dev_path = DEVICE_PATH or find_touchscreen()
    if not dev_path:
        log("❌ Тачскрин не найден!")
        sys.exit(1)

    device = evdev.InputDevice(dev_path)
    log(f"🚀 Запуск: {device.name} ({dev_path})")
    log(f"Параметры: LONG_PRESS={LONG_PRESS_MS}ms, MOVE_THRESHOLD={MOVE_THRESHOLD}px")

    touched = False
    touch_time = 0
    touch_x, touch_y = 0, 0

    for event in device.read_loop():
        if event.type == evdev.ecodes.EV_KEY:
            if event.code == evdev.ecodes.BTN_TOUCH:
                if event.value == 1:  # касание
                    touched = True
                    touch_time = time.monotonic()
                    touch_x, touch_y = -1, -1  # сброс, ждём первую координату
                elif event.value == 0:  # отпускание
                    if touched:
                        elapsed_ms = (time.monotonic() - touch_time) * 1000
                        if elapsed_ms >= LONG_PRESS_MS:
                            send_rmb()
                    touched = False

        elif event.type == evdev.ecodes.EV_ABS and touched:
            # Отслеживаем движение
            if event.code == evdev.ecodes.ABS_X:
                if touch_x == -1:
                    touch_x = event.value
                else:
                    # Если движение превышает порог — это drag, сбрасываем
                    if abs(event.value - touch_x) > MOVE_THRESHOLD:
                        touched = False

            elif event.code == evdev.ecodes.ABS_Y:
                if touch_y == -1:
                    touch_y = event.value
                else:
                    if abs(event.value - touch_y) > MOVE_THRESHOLD:
                        touched = False

        elif event.type == evdev.ecodes.EV_ABS and not touched:
            # Игнорируем ABS события без касания
            pass

        # EV_SYN — синхронизация пакета, ничего не делаем
        # EV_MSC — вспомогательные события, игнорируем

if __name__ == "__main__":
    main()
