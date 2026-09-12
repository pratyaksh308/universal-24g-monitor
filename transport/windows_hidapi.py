import hid
import time

def poll_battery(config: dict, vid):
    try:
        # Bulletproof parsing: Handles JSON integers (13652), hex strings ("0x3554"), or raw strings ("3554")
        target_vid = vid if isinstance(vid, int) else int(str(vid), 16)
    except ValueError:
        return None

    devices = hid.enumerate(target_vid, 0)
    if not devices:
        return None

    payload = config["payload"]
    battery_level = None

    for dev_info in devices:
        path = dev_info['path']
        dev = hid.device()
        try:
            dev.open_path(path)
            dev.set_nonblocking(1)
            dev.write(payload)
            
            start_time = time.time()
            while time.time() - start_time < 1.0:
                data = dev.read(64)
                if data:
                    if len(data) == config["length"]:
                        battery_level = data[config["battery_index"]]
                        break
                    elif len(data) == config["length"] - 1:
                        battery_level = data[config["battery_index"] - 1]
                        break
                time.sleep(0.05)
            dev.close()
            if battery_level is not None:
                break
        except Exception:
            pass

    return battery_level