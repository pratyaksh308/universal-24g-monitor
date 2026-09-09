cat << 'EOF' > README.md
# Universal 2.4GHz Wireless Peripheral Monitor

A lightweight, open-source Linux background daemon and system tray applet to monitor battery levels, connection status, and polling rates for generic/white-label 2.4GHz wireless peripherals (CompX, Beken, SinoWealth, Telink).

## Features
- Low-level, non-blocking `/dev/hidraw*` polling via direct IOCTL.
- Universal tray indicator using PyGObject (`AppIndicator3`).
- Extensible JSON device matrix mapping Vendor IDs (VID) to feature report payloads.
EOF