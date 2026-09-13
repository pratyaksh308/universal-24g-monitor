import argparse
import sys
import json
import time
import platform
import signal
import threading
from pathlib import Path

# Safely get the directory whether running as a script or a compiled .exe
if getattr(sys, 'frozen', False):
    ROOT_DIR = Path(sys.executable).parent
else:
    ROOT_DIR = Path(__file__).resolve().parent

# Check right next to the executable first, then check the data folder
USER_CONFIG_DIR = Path.home() / ".config" / "universal-24g-monitor"
USER_DEVICES_FILE = USER_CONFIG_DIR / "devices.json"

LOCAL_DEVICES_FILE = ROOT_DIR / "devices.json"
LEGACY_DEVICES_FILE = ROOT_DIR / "data" / "devices.json"
PACKAGED_DEVICES_FILE = Path("/usr/share/universal-24g-monitor/data/devices.json")

if platform.system() == "Linux":
    from transport.linux_hidraw import poll_battery
elif platform.system() == "Windows":
    from transport.windows_hidapi import poll_battery
else:
    raise NotImplementedError(f"Unsupported OS: {platform.system()}")

def load_matrix():
    # Iterate through paths in priority order to resolve B1
    for path in (USER_DEVICES_FILE, LOCAL_DEVICES_FILE, LEGACY_DEVICES_FILE, PACKAGED_DEVICES_FILE):
        if path.exists():
            with open(path, "r") as f:
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

stop_event = threading.Event()

def signal_handler(signum, frame):
    print("\n🛑 Daemon stopped gracefully.")
    stop_event.set()

def run_daemon(interval=60):
    # Resolves B8: Handle system termination signals properly
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"🚀 Universal 2.4GHz Monitor active (polling every {interval}s)...")

    while not stop_event.is_set():
        matrix = load_matrix()
        for _, config in matrix.items():
            for vid in config.get("vids", []):
                level = poll_battery(config, vid)
                if level is not None:
                    print(f"[{time.strftime('%H:%M:%S')}] 🔋 {config['name']}: {level}%")

        # Replaces time.sleep() for responsive shutdown
        stop_event.wait(interval)

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