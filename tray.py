import platform
import sys

if platform.system() == "Linux":
    from linux.linux_tray import main
elif platform.system() == "Windows":
    from windows.windows_tray import main
else:
    print(f"Unsupported OS: {platform.system()}")
    sys.exit(1)

if __name__ == "__main__":
    main()