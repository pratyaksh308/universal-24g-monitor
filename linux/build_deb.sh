#!/bin/bash
set -e

BUILD_DIR="deb-build"
rm -rf ${BUILD_DIR}
mkdir -p ${BUILD_DIR}/DEBIAN
mkdir -p ${BUILD_DIR}/usr/share/universal-24g-monitor/data
mkdir -p ${BUILD_DIR}/etc/udev/rules.d

# Copy source files
cp -r transport linux windows cli.py tray.py ${BUILD_DIR}/usr/share/universal-24g-monitor/
cp data/devices.json ${BUILD_DIR}/usr/share/universal-24g-monitor/data/
cp udev/99-universal-24g.rules ${BUILD_DIR}/etc/udev/rules.d/

# Do not ship interpreter caches or writable-by-group files.
find ${BUILD_DIR}/usr/share/universal-24g-monitor -type d -name __pycache__ -prune -exec rm -rf {} +
find ${BUILD_DIR}/usr/share/universal-24g-monitor -type d -exec chmod 755 {} +
find ${BUILD_DIR}/usr/share/universal-24g-monitor -type f -name '*.py' -exec chmod 755 {} +
find ${BUILD_DIR}/usr/share/universal-24g-monitor -type f -name '*.sh' -exec chmod 755 {} +
find ${BUILD_DIR}/usr/share/universal-24g-monitor -type f \( -name '*.json' -o -name '*.rules' \) -exec chmod 644 {} +
chmod 644 ${BUILD_DIR}/etc/udev/rules.d/99-universal-24g.rules

# Create Control File
cat <<EOF > ${BUILD_DIR}/DEBIAN/control
Package: universal-24g-monitor
Version: 1.0.0
Architecture: all
Maintainer: Pratyaksh Kumar Jha
Depends: python3, python3-pil, python3-gi, gir1.2-gtk-3.0, gir1.2-ayatanaappindicator3-0.1
Description: Universal 2.4GHz Monitor
EOF

# Create Postinst Script
cat <<EOF > ${BUILD_DIR}/DEBIAN/postinst
#!/bin/sh
udevadm control --reload-rules && udevadm trigger
EOF
chmod 755 ${BUILD_DIR}/DEBIAN/postinst

# Set permissions and build
fakeroot chown -R root:root ${BUILD_DIR}
fakeroot dpkg-deb --build ${BUILD_DIR} universal-24g-monitor_1.0.0_all.deb
echo "Build complete: universal-24g-monitor_1.0.0_all.deb"