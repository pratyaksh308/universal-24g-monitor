import json
import time
import platform
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DEVICES_FILE = ROOT_DIR / "data" / "devices.json"

if platform.system() == "Linux":
    from transport.linux_hidraw import poll_battery
elif platform.system() == "Windows":
    from transport.windows_hidapi import poll_battery
else:
    raise NotImplementedError(f"Unsupported OS: {platform.system()}")

def run_daemon():
    print(f"🚀 Starting Universal 2.4GHz Monitor [{platform.system()} Mode]...")
    with open(DEVICES_FILE, "r") as f:
        matrix = json.load(f)

    try:
        while True:
            for _, config in matrix.items():
                for vid in config.get("vids", []):
                    level = poll_battery(config, vid)
                    if level is not None:
                        print(f"🔋 {config['name']}: {level}%")
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 Daemon stopped.")

if __name__ == "__main__":
    run_daemon()