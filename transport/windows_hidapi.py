import logging
import time

import hid

logger = logging.getLogger(__name__)


def _normalize_vid(vid):
    if isinstance(vid, int):
        return vid

    if isinstance(vid, str):
        value = vid.strip()
        if not value:
            return None
        if value.lower().startswith("0x"):
            return int(value, 16)

        # USB vendor IDs are typically stored as hexadecimal strings like "3554"
        # but hid.enumerate() expects their integer value (13652).
        if all(ch in "0123456789abcdefABCDEF" for ch in value):
            return int(value, 16)

        return int(value, 10)

    return None


def poll_battery(config, vid):
    battery_level = None
    payload = bytes(config.get("payload", []))
    battery_index = config.get("battery_index", -1)
    expected_length = config.get("length", 0)
    vendor_id = _normalize_vid(vid)

    if battery_index < 0 or expected_length <= 0 or not payload:
        logger.warning("Skipping VID %s: invalid HID payload or battery metadata.", vid)
        return None

    if vendor_id is None:
        logger.warning("Skipping VID %s: invalid vendor ID format.", vid)
        return None

    for dev_info in hid.enumerate(vendor_id):
        dev = hid.device()
        try:
            dev.open_path(dev_info['path'])
            dev.set_nonblocking(1)
            dev.write(payload)

            start_time = time.time()
            while time.time() - start_time < 1.0:
                data = dev.read(64)
                if not data:
                    time.sleep(0.05)
                    continue

                n = len(data)
                candidate_index = None

                if n == expected_length and battery_index < n:
                    candidate_index = battery_index
                elif n == expected_length - 1 and (battery_index - 1) >= 0 and (battery_index - 1) < n:
                    candidate_index = battery_index - 1

                if candidate_index is None:
                    continue

                value = data[candidate_index]
                if 0 <= value <= 100:
                    battery_level = value
                    break

                logger.debug("Discarded invalid battery reading for VID %s: %s", vid, value)

        except Exception as exc:
            logger.debug("HID read failed for VID %s: %s", vid, exc)
        finally:
            try:
                dev.close()
            except Exception:
                pass

        if battery_level is not None:
            break

    return battery_level