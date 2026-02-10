import logging
import sys
from pathlib import Path
from collections import deque
from logging.handlers import RotatingFileHandler


class MemoryLogHandler(logging.Handler):
    """In-memory ring buffer for recent log entries. Always works, no file I/O."""
    
    def __init__(self, capacity: int = 1000):
        super().__init__()
        self.buffer: deque = deque(maxlen=capacity)
    
    def emit(self, record):
        self.buffer.append(self.format(record))
    
    def get_logs(self, n: int = 50) -> list[str]:
        return list(self.buffer)[-n:]


# Global memory handler instance (accessible by the API)
memory_handler = MemoryLogHandler(capacity=1000)


def setup_logger(name: str = "PaperPlane", log_file: str = "logs/activity.log") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Memory Handler (always works — the API reads from this)
    mem_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    memory_handler.setFormatter(mem_formatter)
    logger.addHandler(memory_handler)
    
    # Console Handler (always works)
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File Handler (may fail on permission issues with bind mounts)
    try:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s', 
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        logger.warning(f"Could not create log file {log_file}: {e}. Using memory + stdout only.")
        
    return logger

# Global instance
logger = setup_logger()
