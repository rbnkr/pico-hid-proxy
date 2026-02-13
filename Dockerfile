FROM debian:bookworm-slim

ARG MICROPYTHON_TAG=v1.27.0
ARG BOARD=RPI_PICO2_W

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake gcc-arm-none-eabi libnewlib-arm-none-eabi \
    libstdc++-arm-none-eabi-newlib \
    libusb-1.0-0-dev pkg-config git python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Clone MicroPython at a pinned tag
RUN git clone --depth 1 --branch ${MICROPYTHON_TAG} \
    https://github.com/micropython/micropython.git /micropython

# Init submodules and build mpy-cross
WORKDIR /micropython
RUN git submodule update --init lib/tinyusb lib/micropython-lib \
    && cd ports/rp2 && make BOARD=${BOARD} submodules \
    && make -C /micropython/mpy-cross -j$(nproc)

# Copy in project files
COPY manifest.py /project/manifest.py
COPY device/ /project/device/

# Build firmware
WORKDIR /micropython/ports/rp2
RUN make BOARD=${BOARD} FROZEN_MANIFEST=/project/manifest.py -j$(nproc)

# Copy .uf2 to a known location for extraction
RUN cp build-${BOARD}/firmware.uf2 /firmware.uf2
