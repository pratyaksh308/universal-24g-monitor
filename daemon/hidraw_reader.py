import os
import json
import time
import glob
import selectors
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DEVICES_FILE = ROOT_DIR / "data" / "devices.json"

def poll_battery(config, vid):
    nodes = []
    for p in glob.glob('/sys/class/hidraw/hidraw*'):
        try:
            if vid in open(f"{p}/device/uevent").read():
                nodes.append(f"/dev/{os.path.basename(p)}")
        except Exception: 
            pass

    if not nodes:
        return None

    sel = selectors.DefaultSelector()
    fds = {}
    
    # 1. Arm the listener on all active nodes
    for node in nodes:
        try:
            fd = os.open(node, os.O_RDWR | os.O_NONBLOCK)
            fds[node] = fd
            sel.register(fd, selectors.EVENT_READ, data=node)
        except Exception: 
            pass

    # 2. Transmit the 17-byte wake command
    payload = bytearray(config["payload"])
    for fd in fds.values():
        try: 
            os.write(fd, payload)
        except OSError: 
            pass

    # 3. Catch the asynchronous response packet
    battery_level = None
    start_time = time.time()
    
    while time.time() - start_time < 2.0:
        events = sel.select(timeout=0.5)
        for key, mask in events:
            try:
                data = os.read(key.fileobj, 64)
                if data and len(data) >= config["length"]:
                    battery_level = data[config["battery_index"]]
                    break
            except BlockingIOError: 
                pass
        if battery_level is not None:
            break

    # 4. Clean up file descriptors
    for fd in fds.values(): 
        os.close(fd)
    sel.close()
    
    return battery_level

if __name__ == "__main__":
    print("🚀 Starting Universal 2.4GHz Monitor Daemon...")
    with open(DEVICES_FILE, "r") as f:
        matrix = json.load(f)
        
    try:
        while True:
            for device_key, config in matrix.items():
                for vid in config.get("vids", []):
                    level = poll_battery(config, vid)
                    if level is not None:
                        print(f"🔋 {config['name']}: {level}%")
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 Daemon stopped.")