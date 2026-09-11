import os
import fcntl
import glob

def scan_kreo():
    nodes = []
    for path in glob.glob('/sys/class/hidraw/hidraw*'):
        try:
            with open(f"{path}/device/uevent", 'r') as f:
                if "3554" in f.read():
                    nodes.append(f"/dev/{os.path.basename(path)}")
        except: pass
    return nodes

print("🔎 Brute-Forcing Kreo Anzu Feature Reports...")
nodes = scan_kreo()

for n in nodes:
    try:
        fd = os.open(n, os.O_RDWR | os.O_NONBLOCK)
        print(f"\n--- Probing {n} ---")
        
        # Test Report IDs 1 through 9
        for report_id in range(1, 10):
            length = 13 # Base length from WebHID trace
            IOC_GET = (3 << 30) | (length << 16) | (ord('H') << 8) | 0x07
            buf = bytearray([report_id] + [0] * (length - 1))
            
            try:
                fcntl.ioctl(fd, IOC_GET, buf)
                data = list(buf)
                
                # Check if buffer has any actual data besides zeros
                if sum(data[1:]) > 0:
                    print(f"✅ ID {report_id} | DATA: {[hex(b) for b in data]} | DEC: {data}")
                else:
                    print(f"💤 ID {report_id} | Empty (zeros)")
            except OSError as e:
                # [Errno 32] Broken pipe means the ID doesn't exist on this node
                print(f"❌ ID {report_id} | Rejected ({e})")
                
        os.close(fd)
    except Exception as e:
        print(f"⚠️ Could not open {n}: {e}")