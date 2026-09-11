import os
import selectors
import time
import glob

def target_battery_packet():
    nodes = []
    for p in glob.glob('/sys/class/hidraw/hidraw*'):
        try:
            if "3554" in open(f"{p}/device/uevent").read():
                nodes.append(f"/dev/{os.path.basename(p)}")
        except: pass

    sel = selectors.DefaultSelector()
    fds = {}

    for node in nodes:
        try:
            fd = os.open(node, os.O_RDWR | os.O_NONBLOCK)
            fds[node] = fd
            sel.register(fd, selectors.EVENT_READ, data=node)
        except Exception: pass

    # The missing link: Report ID 8 + the exact 16-byte payload including the '73' checksum
    payload = bytearray([8, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 73])
    
    for node, fd in fds.items():
        try:
            os.write(fd, payload)
        except Exception: pass

    print("🎧 Trap set with correct checksum. Waiting for the mouse to reply...")
    start_time = time.time()
    
    while time.time() - start_time < 3.0:
        events = sel.select(timeout=0.5)
        for key, mask in events:
            try:
                data = os.read(key.fileobj, 64)
                if data and len(data) >= 16:
                    packet = list(data)
                    print(f"\n✅ SUCCESS! CAUGHT PACKET on {key.data}")
                    print(f"   Length: {len(packet)} bytes")
                    print(f"   Decimal: {packet}")
                    if len(packet) > 5:
                        print(f"   🎯 Battery Value (Index 5): {packet[5]}")
                    
                    for fd in fds.values(): os.close(fd)
                    sel.close()
                    return
            except BlockingIOError:
                pass

    print("⚠️ Timeout. No response received.")
    for fd in fds.values(): os.close(fd)
    sel.close()

if __name__ == "__main__":
    target_battery_packet()