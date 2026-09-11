import pystray
from PIL import Image, ImageDraw
import threading
import time
import platform
from cli import load_matrix

if platform.system() == "Linux":
    from transport.linux_hidraw import poll_battery
elif platform.system() == "Windows":
    from transport.windows_hidapi import poll_battery

def create_image(percentage):
    image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    draw.rectangle([10, 20, 50, 44], outline="white", width=2)
    draw.rectangle([50, 26, 54, 38], fill="white")
    
    fill_width = int(36 * (percentage / 100.0))
    if fill_width > 0:
        fill_color = "green" if percentage > 20 else "red"
        draw.rectangle([12, 22, 12 + fill_width, 42], fill=fill_color)
        
    return image

def update_tray(icon):
    while icon.visible:
        try:
            matrix = load_matrix()
            display_level = 0 
            label = "No Device"
            
            for _, config in matrix.items():
                for vid in config.get("vids", []):
                    level = poll_battery(config, vid)
                    if level is not None:
                        display_level = level
                        label = f"{config['name']}: {level}%"
                        break
            
            icon.icon = create_image(display_level)
            icon.title = label
            print(f"[Tray Updated] {label}")
        except Exception as e:
            print(f"[Tray Error] {e}")
            
        time.sleep(30)

def setup_tray(icon):
    icon.visible = True
    # Start polling thread only after the tray icon is fully running
    threading.Thread(target=update_tray, args=(icon,), daemon=True).start()

def main():
    icon = pystray.Icon(
        "24g_monitor",
        create_image(0),
        "Initializing Monitor..."
    )
    icon.run(setup=setup_tray)

if __name__ == "__main__":
    main()