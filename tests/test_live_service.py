import time
import multiprocessing
import logging
from services.live_translation_service import LiveTranslationProcess

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestLiveService")

def test_live_service():
    logger.info("Starting test_live_service")
    
    status_queue = multiprocessing.Queue()
    command_queue = multiprocessing.Queue()
    
    # Start the process
    process = LiveTranslationProcess(
        monitor_index=0,  # Assuming primary monitor
        source_lang="eng",
        target_lang="msa",
        status_queue=status_queue,
        command_queue=command_queue
    )
    
    process.start()
    logger.info(f"Process started with PID: {process.pid}")
    
    # Let it run for a few seconds
    time.sleep(10)
    
    # Check if it's still alive
    if process.is_alive():
        logger.info("Process is running correctly")
    else:
        logger.error("Process died prematurely")
        return
    
    # Send stop command
    logger.info("Sending STOP command")
    command_queue.put("STOP")
    
    # Wait for it to exit
    process.join(timeout=5)
    
    if not process.is_alive():
        logger.info("Process stopped successfully")
    else:
        logger.error("Process failed to stop, terminating...")
        process.terminate()

if __name__ == "__main__":
    # Windows support for multiprocessing
    multiprocessing.freeze_support()
    test_live_service()
