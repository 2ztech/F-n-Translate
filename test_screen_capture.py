# test_screen_capture.py
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from mss import mss
from PIL import Image

def test_mss():
    try:
        print("Testing MSS screen capture...")
        with mss() as sct:
            print(f"Found {len(sct.monitors)} monitors:")
            for i, monitor in enumerate(sct.monitors):
                print(f"Monitor {i}: {monitor}")
            
            # Try to capture from monitor 1 (usually primary)
            if len(sct.monitors) > 1:
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                print(f"Successfully captured screenshot: {screenshot.size}")
                
                # Save test image
                img.save("test_capture.png")
                print("Saved test image as 'test_capture.png'")
                return True
            else:
                print("No monitors found beyond the virtual screen")
                return False
                
    except Exception as e:
        print(f"MSS test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_mss()
