
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    from gui.ui import FnTranslateUI
    print("Imported FnTranslateUI successfully")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
