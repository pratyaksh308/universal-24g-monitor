import hid
import time

def poll_battery(config, vid):
    battery_level = None
    payload = bytes(config["payload"])
    battery_index = config.get("battery_index", -1)
    expected_length = config.get("length", 0)

    if battery_index < 0 or expected_length <= 0:
        return None

    for dev_info in hid.enumerate(vid):
        dev = hid.device()
        try:
            dev.open_path(dev_info['path'])
            dev.set_nonblocking(1)
            dev.write(payload)

            start_time = time.time()
            while time.time() - start_time < 1.0:
                data = dev.read(64)
                if data:
                    n = len(data)
                    if n == expected_length and battery_index < n:
                        battery_level = data[battery_index]
                    elif n == expected_length - 1 and (battery_index - 1) >= 0 and (battery_index - 1) < n:
                        battery_level = data[battery_index - 1]

                    if battery_level is not None:
                        if not (0 <= battery_level <= 100):
                            battery_level = None
                        break
                time.sleep(0.05)
        except Exception:
            pass
        finally:
            try:
                dev.close()
            except Exception:
                pass

        if battery_level is not None:
            break

    return battery_level