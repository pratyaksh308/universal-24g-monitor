import os
import glob
import selectors
import time

def poll_battery(config: dict, vid):
    # 1. Normalize VID to a 4-character hex string (e.g., "0x3554" -> "3554")
    try:
        target_vid = vid if isinstance(vid, int) else int(str(vid), 16)
        vid_str = f"{target_vid:04x}".lower()
    except ValueError:
        return None

    # 2. Discover matching hidraw nodes in sysfs
    nodes = []
    for p in glob.glob('/sys/class/hidraw/hidraw*'):
        try:
            with open(f"{p}/device/uevent", "r") as f:
                if vid_str in f.read().lower():
                    nodes.append(f"/dev/{os.path.basename(p)}")
        except Exception:
            pass

    if not nodes:
        return None

    sel = selectors.DefaultSelector()
    fds = {}

    try:
        # 3. Open non-blocking file descriptors for each matching node
        for node in nodes:
            try:
                fd = os.open(node, os.O_RDWR | os.O_NONBLOCK)
                fds[node] = fd
                sel.register(fd, selectors.EVENT_READ, data=node)
            except (PermissionError, OSError):
                # Will trigger if udev rules are missing
                pass

        if not fds:
            return None

        # 4. Write query payload across endpoints
        payload = bytearray(config["payload"])
        for fd in fds.values():
            try:
                os.write(fd, payload)
            except OSError:
                pass

        battery_level = None
        start_time = time.time()
        expected_report_id = config.get("report_id")
        battery_index = config.get("battery_index", -1)
        if battery_index < 0:
            return None

        # 5. Poll with parity for report ID prefixes
        while time.time() - start_time < 1.0:
            events = sel.select(timeout=0.2)
            for key, _ in events:
                try:
                    data = os.read(key.fileobj, 64)
                    if data:
                        # STRICT FILTER: Ignore any packet that doesn't match our expected telemetry Report ID
                        if expected_report_id is not None and data[0] != expected_report_id:
                            continue

                        # Full report matching config
                        if len(data) == config["length"] and battery_index < len(data):
                            battery_level = data[battery_index]
                            break
                        # Stripped report ID offset
                        elif len(data) == config["length"] - 1 and 0 <= battery_index - 1 < len(data):
                            battery_level = data[battery_index - 1]
                            break
                        elif battery_index < len(data):
                            battery_level = data[battery_index]
                            break
                except (BlockingIOError, OSError):
                    pass
            if battery_level is not None:
                break

    finally:
        # Guarantee descriptor cleanup
        for fd in fds.values():
            try:
                os.close(fd)
            except OSError:
                pass
        sel.close()

    return battery_level