import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading
import time
import signal
import gi
from PIL import Image, ImageDraw

gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, GLib, AyatanaAppIndicator3

from cli import load_matrix
from transport.linux_hidraw import poll_battery

class LinuxBatteryMonitor:
    def __init__(self):
        self.icon_dir = "/tmp/universal_24g_icons"
        os.makedirs(self.icon_dir, exist_ok=True)
        
        self.indicator = AyatanaAppIndicator3.Indicator.new(
            "universal-24g-monitor",
            self.generate_offline_icon(),
            AyatanaAppIndicator3.IndicatorCategory.HARDWARE
        )
        
        self.indicator.set_title("Universal 2.4GHz Monitor")
        self.indicator.set_label("Universal 2.4GHz Monitor", "")
        self.indicator.set_icon_theme_path(self.icon_dir)
        self.indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
        
        self.menu = Gtk.Menu()
        
        self.header_item = Gtk.MenuItem(label="🔋 Universal 2.4G Monitor (v1.0.0)")
        self.header_item.set_sensitive(False)
        self.menu.append(self.header_item)
        
        self.status_item = Gtk.MenuItem(label="Initializing Monitor...")
        self.status_item.set_sensitive(False)
        self.menu.append(self.status_item)
        
        self.menu.append(Gtk.SeparatorMenuItem())
        
        item_exit = Gtk.MenuItem(label="Exit")
        item_exit.connect("activate", self.stop)
        self.menu.append(item_exit)
        
        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        self.last_raw_level = None
        self.frozen_level = 0
        self.is_charging = False
        self.missed_polls = 0
        self.last_known_device_name = "Wireless Mouse"
        self.stop_event = threading.Event()

    def handle_signal(self, signum, frame):
        self.stop_event.set()
        Gtk.main_quit()

    def generate_offline_icon(self):
        icon_name = "bat_offline"
        icon_path = os.path.join(self.icon_dir, f"{icon_name}.png")
        if not os.path.exists(icon_path):
            image = Image.new('RGBA', (22, 22), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle([1, 6, 19, 16], radius=2, outline=(150, 150, 150, 255), width=1)
            draw.rectangle([20, 9, 21, 13], fill=(150, 150, 150, 255))
            draw.line([1, 6, 19, 16], fill=(150, 150, 150, 255), width=1)
            image.save(icon_path)
        return icon_name

    def generate_icon(self, percentage, charging):
        icon_name = f"bat_{percentage}_{1 if charging else 0}"
        icon_path = os.path.join(self.icon_dir, f"{icon_name}.png")
        
        if not os.path.exists(icon_path):
            image = Image.new('RGBA', (22, 22), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            draw.rounded_rectangle([1, 6, 19, 16], radius=2, outline=(240, 240, 240, 255), width=1)
            draw.rectangle([20, 9, 21, 13], fill=(240, 240, 240, 255))
            
            fill_width = int(16 * (percentage / 100.0))
            if fill_width > 0:
                if percentage >= 50:
                    color = (46, 204, 113, 255)
                elif percentage >= 20:
                    color = (241, 196, 15, 255)
                else:
                    color = (231, 76, 60, 255)
                    
                draw.rounded_rectangle([2, 7, 2 + fill_width, 15], radius=1, fill=color)
                
            if charging:
                bolt = [(10, 4), (6, 11), (10, 11), (9, 17), (14, 9), (10, 9)]
                draw.polygon(bolt, fill=(255, 223, 0, 255))
                
            image.save(icon_path)
            
        return icon_name

    def update_ui(self, menu_label, icon_name, panel_label):
        self.status_item.set_label(menu_label)
        self.indicator.set_icon_full(icon_name, "Battery Level")
        self.indicator.set_label(panel_label, "")
        return False

    def poll_loop(self):
        while True:
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
                    self.missed_polls = 0  
                    device_name = matched_config.get("name", "Wireless Mouse")
                    self.last_known_device_name = device_name
                    
                    if self.last_raw_level is not None:
                        if raw_level > self.last_raw_level:
                            if not self.is_charging:
                                self.frozen_level = self.last_raw_level
                                self.is_charging = True
                        elif raw_level < self.last_raw_level:
                            if self.is_charging and (self.last_raw_level - raw_level) >= 10:
                                self.is_charging = False
                                self.frozen_level = raw_level
                            elif not self.is_charging:
                                self.frozen_level = raw_level
                    else:
                        self.frozen_level = raw_level
                    
                    self.last_raw_level = raw_level
                    status = "Charging" if self.is_charging else "On Battery"
                    
                    menu_label = f"{device_name}\nLevel: {self.frozen_level}%\nStatus: {status}"
                    panel_label = f" {self.frozen_level}%"
                    
                    icon_name = self.generate_icon(self.frozen_level, self.is_charging)
                    GLib.idle_add(self.update_ui, menu_label, icon_name, panel_label)
                    print(f"[Tray Updated] {device_name} | Display: {self.frozen_level}% | Status: {status}")
                    
                else:
                    self.missed_polls += 1
                    if self.missed_polls >= 2:
                        self.is_charging = False
                        self.last_raw_level = None 
                        menu_label = f"{self.last_known_device_name}\nStatus: Sleeping / Offline"
                        icon_name = self.generate_offline_icon()
                        GLib.idle_add(self.update_ui, menu_label, icon_name, "")
                        print(f"[Tray Updated] Offline / Sleeping")
                    else:
                        print(f"[Tray Warning] Missed packet {self.missed_polls}/2, debouncing shallow sleep...")

            except Exception as e:
                print(f"[Tray Error] {e}")
                
            self.stop_event.wait(5)

    def start(self):
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        thread = threading.Thread(target=self.poll_loop, daemon=True)
        thread.start()
        Gtk.main()

    def stop(self, source=None):
        self.stop_event.set()
        Gtk.main_quit()

def main():
    LinuxBatteryMonitor().start()

if __name__ == "__main__":
    app = LinuxBatteryMonitor()
    app.start()