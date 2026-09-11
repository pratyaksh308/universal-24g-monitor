import argparse
import sys
import json
import time
import platform
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DEVICES_FILE = ROOT_DIR / "data" / "devices.json"

if platform.system() == "Linux":
    from transport.linux_hidraw import poll_battery
elif platform.system() == "Windows":
    from transport.windows_hidapi import poll_battery
else:
    raise NotImplementedError(f"Unsupported OS: {platform.system()}")

def load_matrix():
    if not DEVICES_FILE.exists():
        print(f"❌ Error: Database not found at {DEVICES_FILE}")
        sys.exit(1)
    with open(DEVICES_FILE, "r") as f:
        return json.load(f)

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
    matrix = load_matrix()
    print(f"🚀 Universal 2.4GHz Monitor Daemon active (polling every {interval}s)...")
    try:
        while True:
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