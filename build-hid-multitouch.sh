#!/bin/bash
set -e

# build-hid-multitouch.sh — собрать и установить hid-multitouch для OPI Zero 3W
# Запускать на OPI Zero 3W (ядро 6.6.98-sun60iw2)

KERNEL_VER=$(uname -r)
echo "=== Сборка hid-multitouch для ядра $KERNEL_VER ==="

# Проверка ядра
if [[ "$KERNEL_VER" != *"sun60iw2"* ]]; then
    echo "Ошибка: скрипт для OPI Zero 3W (sun60iw2). Текущее ядро: $KERNEL_VER"
    exit 1
fi

# Проверка хедеров
if [ ! -d "/usr/src/linux-headers-$KERNEL_VER" ]; then
    echo "Устанавливаю linux-headers..."
    sudo apt update && sudo apt install -y linux-headers-current-sun60iw2 gcc make
fi

# Директория сборки
BUILD_DIR="/tmp/hidbuild"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Исходники из Linux 6.6
echo "=== Скачиваю исходники ==="
curl -sLO "https://raw.githubusercontent.com/torvalds/linux/v6.6/drivers/hid/hid-multitouch.c"
curl -sLO "https://raw.githubusercontent.com/torvalds/linux/v6.6/drivers/hid/hid-ids.h"

# Makefile
cat > Makefile << 'MAKE_EOF'
obj-m := hid-multitouch.o
ccflags-y := -I/tmp/hidbuild
KERNEL_BUILD := /lib/modules/$(shell uname -r)/build
all:
	$(MAKE) -C $(KERNEL_BUILD) M=$(PWD) modules
clean:
	$(MAKE) -C $(KERNEL_BUILD) M=$(PWD) clean
MAKE_EOF

# Патчим UTS_RELEASE для совпадения vermagic
echo "=== Патчу UTS_RELEASE ==="
sudo sed -i 's/"6.6.98"/"6.6.98-sun60iw2"/' \
    "/usr/src/linux-headers-$KERNEL_VER/include/generated/utsrelease.h"

# Сборка
echo "=== Собираю модуль ==="
make -C "/lib/modules/$KERNEL_VER/build" M="$BUILD_DIR" modules

# Установка
echo "=== Устанавливаю ==="
sudo rm -f "/lib/modules/$KERNEL_VER/kernel/drivers/hid/hid-multitouch.ko"
sudo cp "$BUILD_DIR/hid-multitouch.ko" \
    "/lib/modules/$KERNEL_VER/kernel/drivers/hid/"
sudo depmod -a

# Загрузка
echo "=== Загружаю модуль ==="
sudo modprobe hid-multitouch

# Автозагрузка
echo "=== Настраиваю автозагрузку ==="
echo "hid-multitouch" | sudo tee /etc/modules-load.d/hid-multitouch.conf >/dev/null

# Udev-правило
cat << 'UDEV_EOF' | sudo tee /etc/udev/rules.d/99-touchscreen.rules >/dev/null
ACTION=="add", KERNEL=="event1", SUBSYSTEM=="input", \
  ATTRS{idVendor}=="0484", ATTRS{idProduct}=="5750", MODE="0666"
UDEV_EOF
sudo udevadm control --reload-rules

echo ""
echo "✅ Готово! Модуль hid-multitouch загружен."
echo "   Перезагрузи OPI или отключи/подключи USB тачскрина."
