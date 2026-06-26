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

## Благодарности 🦞

Починили вместе с [Пятницей](https://github.com/Haidegger22) и Джарвисом 🤖💚
