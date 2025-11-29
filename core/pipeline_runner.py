import sys
import os
import argparse
import signal
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# Add parent directory to path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from component.pipeline_manager import PipelineManager

def main():
    parser = argparse.ArgumentParser(description='Run the screen capture pipeline.')
    parser.add_argument('--monitor', type=int, default=1, help='Monitor index to capture')
    args = parser.parse_args()

    app = QApplication(sys.argv)

    # Handle Ctrl+C
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Create and start the pipeline
    try:
        manager = PipelineManager(monitor_index=args.monitor)
        
        # Connect signals to stdout for the parent process to read
        manager.status_update.connect(lambda msg: print(f"STATUS:{msg}", flush=True))
        manager.error_occurred.connect(lambda err: print(f"ERROR:{err}", flush=True))
        
        manager.start()
        print(f"STATUS:Pipeline process started for monitor {args.monitor}", flush=True)
        
        # Run the application
        sys.exit(app.exec_())
    except Exception as e:
        print(f"ERROR:Failed to start pipeline: {e}", flush=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
