import argparse
import sys
import json
import time
import platform
from pathlib import Path

# Safely get the directory whether running as a script or a compiled .exe
if getattr(sys, 'frozen', False):
    ROOT_DIR = Path(sys.executable).parent
else:
    ROOT_DIR = Path(__file__).resolve().parent

# Check right next to the executable first, then check the data folder
LOCAL_DEVICES_FILE = ROOT_DIR / "devices.json"
LEGACY_DEVICES_FILE = ROOT_DIR / "data" / "devices.json"

USER_CONFIG_DIR = Path.home() / ".config" / "universal-24g-monitor"
USER_DEVICES_FILE = USER_CONFIG_DIR / "devices.json"

if platform.system() == "Linux":
    from transport.linux_hidraw import poll_battery
elif platform.system() == "Windows":
    from transport.windows_hidapi import poll_battery
else:
    raise NotImplementedError(f"Unsupported OS: {platform.system()}")

def load_matrix():
    # 1. Prioritize custom user config
    if USER_DEVICES_FILE.exists():
        with open(USER_DEVICES_FILE, "r") as f:
            return json.load(f)
    
    # 2. Check right next to the .exe / script
    if LOCAL_DEVICES_FILE.exists():
        with open(LOCAL_DEVICES_FILE, "r") as f:
            return json.load(f)
            
    # 3. Fallback to /data/ folder for devs running from source
    if LEGACY_DEVICES_FILE.exists():
        with open(LEGACY_DEVICES_FILE, "r") as f:
            return json.load(f)

    # 4. Safe failure: Do NOT sys.exit(1) here, or the tray thread will die silently.
    print("⚠️ Warning: devices.json not found. Please place it next to the executable.")
    return {}

def get_status(json_output=False):
    matrix = load_matrix()
    results = []

    for _, config in matrix.items():
        for vid in config.get("vids", []):
            level = poll_battery(config, vid)
            if level is not None:
                results.append({
                    "name": config["name"],
                    "vendor_id": vid,
                    "battery": level
                })

    if json_output:
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print("⚠️ No supported devices detected or device is asleep.")
        for item in results:
            print(f"🔋 {item['name']}: {item['battery']}%")

def run_daemon(interval=60):
    print(f"🚀 Universal 2.4GHz Monitor active (polling every {interval}s)...")
    try:
        while True:
            matrix = load_matrix()
            for _, config in matrix.items():
                for vid in config.get("vids", []):
                    level = poll_battery(config, vid)
                    if level is not None:
                        print(f"[{time.strftime('%H:%M:%S')}] 🔋 {config['name']}: {level}%")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n🛑 Daemon stopped.")

def main():
    parser = argparse.ArgumentParser(
        prog="universal-24g-monitor",
        description="Universal battery telemetry monitor for 2.4GHz wireless peripherals."
    )
    parser.add_argument(
        "-s", "--status",
        action="store_true",
        help="Query and print current battery level once, then exit."
    )
    parser.add_argument(
        "-d", "--daemon",
        action="store_true",
        help="Run continuously as a background polling daemon."
    )
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=60,
        help="Polling interval in seconds for daemon mode (default: 60)."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format (ideal for Waybar, Polybar, or scripts)."
    )

    args = parser.parse_args()

    if args.daemon:
        run_daemon(interval=args.interval)
    elif args.status or args.json:
        get_status(json_output=args.json)
    else:
        get_status(json_output=False)

if __name__ == "__main__":
    main()