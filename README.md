# OPI Zero 3W — Драйвер тачскрина (hid-multitouch)

Исправление тачскрина для Orange Pi Zero 3W (ядро 6.6.98-sun60iw2).

## Проблема 📛

В ядре `6.6.98-sun60iw2` **отключена** поддержка HID-мультитача:

```
# CONFIG_HID_MULTITOUCH is not set
```

Тачскрин (например, QDtech MPI5001 с USB ID `0484:5750`) определяется системой как HID-устройство, создаётся `/dev/input/event1`, но события касания **не обрабатываются** — мультитач-свойства (`ABS_MT_*`) отсутствуют.

В `/lib/modules/6.6.98-sun60iw2/kernel/drivers/hid/` лежит битый модуль, собранный для Raspberry Pi (vermagic `6.6.98+`), который не загружается.

## Решение ✅

Собрать правильный модуль `hid-multitouch.ko` для ядра `6.6.98-sun60iw2` из исходников.

### Требования

- Orange Pi Zero 3W с установленным SSH-доступом
- Пароль `sudo` от `orangepi`
- Интернет на OPI (для скачивания исходников, если потребуется)

### Пошагово

#### 1. Подготовка

На OPI Zero 3W должны быть установлены заголовки ядра:

```bash
sudo apt update
sudo apt install -y linux-headers-current-sun60iw2 gcc make
```

#### 2. Сборка модуля

```bash
# Создаём директорию
mkdir -p /tmp/hidbuild && cd /tmp/hidbuild

# Берём исходник hid-multitouch из основного ядра Linux 6.6
curl -sLO "https://raw.githubusercontent.com/torvalds/linux/v6.6/drivers/hid/hid-multitouch.c"
curl -sLO "https://raw.githubusercontent.com/torvalds/linux/v6.6/drivers/hid/hid-ids.h"

# Makefile
cat > Makefile << 'MAKEEOF'
obj-m := hid-multitouch.o
ccflags-y := -I/tmp/hidbuild
KERNEL_BUILD := /lib/modules/$(shell uname -r)/build
all:
	$(MAKE) -C $(KERNEL_BUILD) M=$(PWD) modules
clean:
	$(MAKE) -C $(KERNEL_BUILD) M=$(PWD) clean
MAKEEOF

# Патчим utsrelease.h, чтобы vermagic совпадал с ядром
sudo sed -i 's/"6.6.98"/"6.6.98-sun60iw2"/' \
  /usr/src/linux-headers-6.6.98-sun60iw2/include/generated/utsrelease.h

# Собираем
make -C /lib/modules/$(uname -r)/build M=$(pwd) modules
```

#### 3. Установка

```bash
# Удаляем битый модуль (с Raspberry Pi)
sudo rm -f /lib/modules/$(uname -r)/kernel/drivers/hid/hid-multitouch.ko

# Копируем собранный
sudo cp /tmp/hidbuild/hid-multitouch.ko \
  /lib/modules/$(uname -r)/kernel/drivers/hid/

# Обновляем зависимости модулей
sudo depmod -a

# Загружаем
sudo modprobe hid-multitouch
```

#### 4. Автозагрузка при старте

```bash
# Автозагрузка модуля
echo "hid-multitouch" | sudo tee /etc/modules-load.d/hid-multitouch.conf

# Права на устройство (udev-правило)
cat << 'RULEEOF' | sudo tee /etc/udev/rules.d/99-touchscreen.rules
ACTION=="add", KERNEL=="event1", SUBSYSTEM=="input", \
  ATTRS{idVendor}=="0484", ATTRS{idProduct}=="5750", MODE="0666"
RULEEOF

sudo udevadm control --reload-rules
```

#### 5. Проверка

```bash
# Модуль загружен?
lsmod | grep hid_multi

# События касания приходят? (нажми на экран)
sudo evtest /dev/input/event1
```

## Структура репозитория 📁

```
hid-multitouch/
├── README.md               # Эта инструкция
├── build-hid-multitouch.sh # Автоматический скрипт сборки
├── hid-multitouch.c        # Исходник (из v6.6)
├── hid-ids.h               # Хедер (из v6.6)
└── 99-touchscreen.rules    # Udev-правило
```

## Совместимость 🧪

Проверено:
- **Плата:** Orange Pi Zero 3W (Allwinner A733)
- **Ядро:** `6.6.98-sun60iw2`
- **ОС:** Orange Pi 1.0.0 Bullseye (Debian 11)
- **Дисплей:** HZWDONE 7" IPS (HDMI + USB тач)
- **Тачскрин:** QDtech MPI5001 (USB ID `0484:5750`)
- **Контроллер:** ASMedia ASM2364, JMicron JMS583, RTL9210 (NVMe-мосты не влияют)

## Настройка кликов (ЛКМ/ПКМ) 🖱️

На тачскрине (HID-тач или резистивный XPT2046) по умолчанию:

| Действие | Результат |
|----------|-----------|
| Одиночное касание | **ЛКМ** ✅ |
| Долгий тап (>~300 мс) | **ПКМ** (контекстное меню) ✅ |
| Перетаскивание | Drag (ЛКМ + движение) ✅ |

### Если ПКМ (долгий тап) не работает

Проверь настройки libinput:

```bash
# Список устройств ввода
xinput list

# Параметры тачскрина (id — номер из списка выше)
xinput list-props <id> | grep -i "long"

# Включить эмуляцию ПКМ через долгий тап (0 = выкл, 1 = вкл)
xinput set-prop <id> "libinput Long Press Enabled" 1

# Порог срабатывания ПКМ (мс)
xinput set-prop <id> "libinput Long Press Time" 400
```

> **Для XFCE:** Кнопка «Mouse» → вкладка «Touchpad» — опция «Use two-finger tap for right click» работает только для тачпадов. На тачскрине ПКМ включается через libinput (см. выше).

### Постоянная настройка (автозагрузка)

Создай `~/.xinitrc` или профиль XFCE, например через `~/.xprofile`:

```bash
cat >> ~/.xprofile << 'XPROF'
# Включение долгого тапа как ПКМ для тачскрина
TOUCH_ID=$(xinput list | grep -i "touch" | grep -oP 'id=\K\d+' | head -1)
if [ -n "$TOUCH_ID" ]; then
  xinput set-prop $TOUCH_ID "libinput Long Press Enabled" 1
  xinput set-prop $TOUCH_ID "libinput Long Press Time" 400
fi
XPROF
```

## Настройка экранной клавиатуры Onboard 🎹

Onboard — лёгкая экранная клавиатура для X11, идеальна для тачскрина OPI Zero 3W.

### Установка

```bash
sudo apt update
sudo apt install -y onboard
```

### Включение авто-показа при фокусе текстовых полей

Onboard 1.4.1 на Debian 11 поддерживает авто-показ через AT-SPI (Accessibility Bridge).

```bash
# 1️⃣ Включить авто-показ
DISPLAY=:0 gsettings set org.onboard.auto-show enabled true

# 2️⃣ Проверить
gsettings get org.onboard.auto-show enabled
# → true

# 3️⃣ (Опционально) Как клавиатура позиционируется при появлении
gsettings set org.onboard.auto-show reposition-method-floating 'prevent-occlusion'
# Варианты: 'none' | 'prevent-occlusion' | 'reduce-travel'
```

### Автозапуск при входе в XFCE

```bash
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/onboard.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Onboard
Exec=onboard
Hidden=false
NoDisplay=false
X-XFCE-Autostart-Phase=2
X-XFCE-Autostart-Enabled=true
EOF
```

> ⚠️ **Важно:** Флаг `--auto-show` **не поддерживается** версией onboard 1.4.1. Не добавляй его в `Exec=` — onboard не запустится. Авто-показ настраивается через gsettings (см. выше).

### Onboard + Chromium

Чтобы Onboard автоматически появлялась при фокусе полей ввода в Chromium:

1. AT-SPI bridge должен быть запущен (обычно уже работает на XFCE):
   ```bash
   ps aux | grep at-spi-bus-launcher
   ```

2. Chromium нужно запускать с флагом `--force-renderer-accessibility`:
   ```bash
   chromium-browser --force-renderer-accessibility %U
   ```

   Для постоянной настройки добавь в ярлык Chromium:
   ```bash
   sudo sed -i 's/Exec=\/usr\/bin\/chromium-browser/Exec=\/usr\/bin\/chromium-browser --force-renderer-accessibility/' \
     /usr/share/applications/chromium-browser.desktop
   # Или скопируй в ~/.local/share/applications/
   cp /usr/share/applications/chromium-browser.desktop ~/.local/share/applications/
   sed -i 's/Exec=\/usr\/bin\/chromium-browser/Exec=\/usr\/bin\/chromium-browser --force-renderer-accessibility/' \
     ~/.local/share/applications/chromium-browser.desktop
   ```

### Проверка

```bash
# Onboard запущена?
ps aux | grep onboard

# Авто-показ активен?
displays=:0 gsettings get org.onboard.auto-show enabled

# Accessibility bridge работает?
ps aux | grep at-spi
```

Тапни в адресную строку Chromium — Onboard должна появиться. Тапни вне поля — скроется.

## Структура репозитория 📁

```
hid-multitouch/
├── README.md               # Эта инструкция
├── build-hid-multitouch.sh # Автоматический скрипт сборки
├── hid-multitouch.c        # Исходник (из v6.6)
├── hid-ids.h               # Хедер (из v6.6)
└── 99-touchscreen.rules    # Udev-правило
```

## Совместимость 🧪

Проверено:
- **Плата:** Orange Pi Zero 3W (Allwinner A733)
- **Ядро:** `6.6.98-sun60iw2`
- **ОС:** Orange Pi 1.0.0 Bullseye (Debian 11)
- **Дисплей:** HZWDONE 7" IPS (HDMI + USB тач)
- **Тачскрин:** QDtech MPI5001 (USB ID `0484:5750`)
- **Контроллер:** ASMedia ASM2364, JMicron JMS583, RTL9210 (NVMe-мосты не влияют)

## Благодарности 🦞

Починили вместе с [Пятницей](https://github.com/Haidegger22) и Джарвисом 🤖💚
