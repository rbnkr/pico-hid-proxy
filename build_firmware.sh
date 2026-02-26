#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOARD="${BOARD:-RPI_PICO2_W}"
IMAGE_TAG="pico-firmware-build"

echo "=== Building MicroPython firmware (Docker) ==="
echo "Board: $BOARD"
echo ""

docker build \
    --build-arg BOARD="$BOARD" \
    -t "$IMAGE_TAG" \
    "$PROJECT_DIR"

# Extract the .uf2 from the image
mkdir -p "$PROJECT_DIR/firmware"
docker run --rm "$IMAGE_TAG" cat /firmware.uf2 > "$PROJECT_DIR/firmware/pico_hid_firmware.uf2"

echo ""
echo "=== Success! ==="
echo "Firmware: $PROJECT_DIR/firmware/pico_hid_firmware.uf2"
echo ""
echo "To flash: hold BOOTSEL, plug in Pico, copy the .uf2 file to the drive"
