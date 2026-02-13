# Frozen modules manifest for MicroPython build
# This includes the standard RP2 manifest plus our HID device code

# Include the default manifest for this board
include("$(PORT_DIR)/boards/manifest.py")

# Include USB HID library from micropython-lib
require("usb-device-hid")

# Freeze our device code into the firmware
freeze("device")
