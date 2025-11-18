# monitor_utils.py
import logging
from mss import mss
import platform

logger = logging.getLogger("MonitorUtils")

def get_windows_monitors():
    """Get monitor information specifically for Windows"""
    try:
        with mss() as sct:
            monitors = sct.monitors
            logger.info(f"Found {len(monitors)} monitors using MSS")
            
            # Format monitors for the UI
            formatted_monitors = []
            for i, monitor in enumerate(monitors):
                if i == 0:  # Skip the "all monitors" option
                    continue
                    
                formatted_monitors.append({
                    'index': i,
                    'name': f'Monitor {i}',
                    'width': monitor.get('width', 1920),
                    'height': monitor.get('height', 1080),
                    'left': monitor.get('left', 0),
                    'top': monitor.get('top', 0)
                })
            
            return formatted_monitors
            
    except Exception as e:
        logger.error(f"Failed to get monitors: {str(e)}")
        return []

def get_monitor_count():
    """Get the number of monitors"""
    try:
        with mss() as sct:
            return len(sct.monitors) - 1  # Exclude the "all monitors" option
    except:
        return 0
