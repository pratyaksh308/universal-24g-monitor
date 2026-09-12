import pystray
from PIL import Image, ImageDraw, ImageFont
import threading
import time
import platform
from cli import load_matrix

if platform.system() == "Linux":
    from transport.linux_hidraw import poll_battery
elif platform.system() == "Windows":
    from transport.windows_hidapi import poll_battery

def create_image(percentage, charging=False):
    # The canvas is 64x64. We scale the coordinates outward to make the icon significantly larger.
    image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Larger battery body outline
    draw.rounded_rectangle([4, 16, 56, 48], radius=6, outline=(240, 240, 240, 255), width=3)
    # Larger battery terminal nub on the right
    draw.rounded_rectangle([56, 24, 60, 40], radius=2, fill=(240, 240, 240, 255))
    
    # New internal fill calculation for the larger bounding box (inner bounds: x=7 to 53)
    fill_max_width = 46
    fill_width = int(fill_max_width * (percentage / 100.0))
    
    if fill_width > 0:
        if percentage > 50:
            fill_color = (46, 204, 113, 255)
        elif percentage > 20:
            fill_color = (241, 196, 15, 255)
        else:
            fill_color = (231, 76, 60, 255)
            
        draw.rounded_rectangle([7, 19, 7 + fill_width, 45], radius=4, fill=fill_color)
        
    if charging:
        # Scaled up charging badge
        draw.rounded_rectangle([16, 12, 44, 52], radius=4, fill=(0, 0, 0, 180))
        # Scaled up and re-centered lightning bolt
        bolt = [(30, 14), (20, 34), (29, 34), (24, 50), (41, 28), (30, 28)]
        draw.polygon(bolt, fill=(255, 223, 0, 255), outline=(255, 255, 255, 255))
    else:
        try:
            font = ImageFont.load_default()
            text = f"{percentage}%"
            # Adjusted text position for the new larger center
            draw.text((20, 26), text, fill=(255, 255, 255, 255), font=font)
        except Exception:
            pass
        
    return image

def update_tray(icon):
    last_raw_level = None
    frozen_level = 0
    is_charging = False
    missed_polls = 0
    last_known_device_name = "Wireless Mouse"
    
    while icon.visible:
        try:
            matrix = load_matrix()
            raw_level = None 
            device_found = False
            matched_config = None
            
            for _, config in matrix.items():
                for vid in config.get("vids", []):
                    level = poll_battery(config, vid)
                    if level is not None:
                        raw_level = level
                        device_found = True
                        matched_config = config
                        break
                if device_found:
                    break
            
            if device_found and raw_level is not None:
                missed_polls = 0  
                
                device_name = matched_config.get("name", "Wireless Mouse")
                last_known_device_name = device_name
                
                if last_raw_level is not None:
                    if raw_level > last_raw_level:
                        if not is_charging:
                            frozen_level = last_raw_level
                            is_charging = True
                            
                    elif raw_level < last_raw_level:
                        if is_charging:
                            if (last_raw_level - raw_level) >= 10:
                                is_charging = False
                                frozen_level = raw_level
                        else:
                            frozen_level = raw_level
                else:
                    frozen_level = raw_level
                
                last_raw_level = raw_level
                
                # Swapped "Discharging" for the standard terminology "On Battery"
                status = "Charging" if is_charging else "On Battery"
                label = f"{device_name}\nBattery Level: {frozen_level}%\nStatus: {status}"
                
                icon.icon = create_image(frozen_level, charging=is_charging)
                icon.title = label
                
                print(f"[Tray Updated] {device_name} | Display: {frozen_level}% | Status: {status} (Raw Hardware: {raw_level}%)")
                
            else:
                missed_polls += 1
                if missed_polls >= 2:
                    label = f"{last_known_device_name}\nStatus: Offline / BT Mode\n(No Signal)"
                    icon.icon = create_image(0, charging=False)
                    icon.title = label
                    is_charging = False
                    last_raw_level = None 
                    print(f"[Tray Updated] {label.replace(chr(10), ' | ')}")
                else:
                    print("[Tray Warning] Missed single packet, debouncing...")

        except Exception as e:
            print(f"[Tray Error] {e}")
            
        time.sleep(5)

def setup_tray(icon):
    icon.visible = True
    threading.Thread(target=update_tray, args=(icon,), daemon=True).start()

def on_exit(icon, item):
    icon.stop()

def do_nothing(icon, item):
    pass

def main():
    # Create a professional menu using disabled items as headers
    custom_menu = pystray.Menu(
        pystray.MenuItem("🔋 Universal 2.4G Monitor", action=do_nothing, enabled=False),
        pystray.MenuItem("Version 1.0.0", action=do_nothing, enabled=False),
        pystray.MenuItem("Exit", on_exit)
    )

    icon = pystray.Icon(
        "24g_monitor",
        create_image(0, charging=False),
        "Initializing Monitor...",
        menu=custom_menu
    )
    icon.run(setup=setup_tray)

if __name__ == "__main__":
    main()