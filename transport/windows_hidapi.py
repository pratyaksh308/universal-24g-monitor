import hid
import time

def poll_battery(config: dict, vid: str):
    # Convert string VID to hexadecimal integer for hidapi
    try:
        target_vid = int(vid, 16)
    except ValueError:
        return None

    # Enumerate all interfaces associated with this receiver
    paths = [device['path'] for device in hid.enumerate(target_vid, 0)]
    if not paths:
        return None

    payload = config["payload"]
    open_devices = []

    # 1. Open all accessible paths and transmit the wake command
    for path in paths:
        dev = hid.device()
        try:
            dev.open_path(path)
            dev.set_nonblocking(1)
            dev.write(payload)
            open_devices.append(dev)
        except OSError:
            # Windows actively blocks standard mouse/keyboard nodes.
            # We ignore them and only hold onto the vendor configuration nodes.
            pass

    battery_level = None
    start_time = time.time()

    # 2. Poll all open interfaces for the asynchronous response
    while time.time() - start_time < 2.0:
        for dev in open_devices:
            try:
                data = dev.read(64)
                # Windows hidapi usually returns the exact same byte array as Linux hidraw
                if data:
                    if len(data) == config["length"]:
                        battery_level = data[config["battery_index"]]
                        break
                    # Fallback just in case the Windows USB stack strips the Report ID byte
                    elif len(data) == config["length"] - 1:
                        battery_level = data[config["battery_index"] - 1]
                        break
            except Exception:
                pass
        
        if battery_level is not None:
            break
        
        time.sleep(0.05)

    # 3. Clean up
    for dev in open_devices:
        try:
            dev.close()
        except Exception:
            pass

    return battery_level