import os
import glob
import selectors
import time

def poll_battery(config: dict, vid: str):
    nodes = []
    for p in glob.glob('/sys/class/hidraw/hidraw*'):
        try:
            with open(f"{p}/device/uevent", "r") as f:
                if vid.lower() in f.read().lower():
                    nodes.append(f"/dev/{os.path.basename(p)}")
        except Exception:
            pass

    if not nodes:
        return None

    sel = selectors.DefaultSelector()
    fds = {}

    for node in nodes:
        try:
            fd = os.open(node, os.O_RDWR | os.O_NONBLOCK)
            fds[node] = fd
            sel.register(fd, selectors.EVENT_READ, data=node)
        except Exception:
            pass

    payload = bytearray(config["payload"])
    for fd in fds.values():
        try:
            os.write(fd, payload)
        except OSError:
            pass

    battery_level = None
    start_time = time.time()

    while time.time() - start_time < 2.0:
        events = sel.select(timeout=0.5)
        for key, _ in events:
            try:
                data = os.read(key.fileobj, 64)
                if data and len(data) >= config["length"]:
                    battery_level = data[config["battery_index"]]
                    break
            except BlockingIOError:
                pass
        if battery_level is not None:
            break

    for fd in fds.values():
        os.close(fd)
    sel.close()

    return battery_level