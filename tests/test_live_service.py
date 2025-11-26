import time
import multiprocessing
import logging
import os
import sys

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.live_translation_service import LiveTranslationProcess

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestLiveService")

def test_live_service():
    logger.info("Starting test_live_service")
    
    status_queue = multiprocessing.Queue()
    command_queue = multiprocessing.Queue()
    stop_event = multiprocessing.Event()
    
    # Start the process
    process = LiveTranslationProcess(
        monitor_index=0,  # Assuming primary monitor
        source_lang="eng",
        target_lang="msa",
        status_queue=status_queue,
        command_queue=command_queue,
        stop_event=stop_event
    )
    
    process.start()
    logger.info(f"Process started with PID: {process.pid}")
    
    # Let it run for a few seconds to generate some logs/cache
    time.sleep(10)
    
    # Check if it's still alive
    if process.is_alive():
        logger.info("Process is running correctly")
    else:
        logger.error("Process died prematurely")
        return
    
    # Send stop event (Immediate Stop)
    logger.info("Setting STOP event")
    stop_event.set()
    
    # Wait for it to exit
    process.join(timeout=5)
    
    if not process.is_alive():
        logger.info("Process stopped successfully via Event")
    else:
        logger.error("Process failed to stop via Event, terminating...")
        process.terminate()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    test_live_service()
