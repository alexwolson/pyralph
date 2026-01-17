"""Shared debug logging module for Ralph.

Provides configurable logging using Python's standard logging module.
Replaces hardcoded debug log paths with proper configurable logging.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Module-level logger
_logger: Optional[logging.Logger] = None
_verbose: bool = False
_debug_file: Optional[Path] = None


def setup_logging(
    verbose: bool = False,
    debug_file: Optional[Path] = None,
    log_level: int = logging.INFO,
) -> logging.Logger:
    """Configure the Ralph logger.
    
    Args:
        verbose: Enable verbose console output
        debug_file: Optional file path for debug log output (JSON lines format)
        log_level: Logging level for console output
        
    Returns:
        Configured logger instance
    """
    global _logger, _verbose, _debug_file
    
    _verbose = verbose
    _debug_file = debug_file
    
    # Create or get logger
    logger = logging.getLogger("ralph")
    logger.setLevel(logging.DEBUG)  # Capture all, filter at handler level
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_level = logging.DEBUG if verbose else log_level
    console_handler.setLevel(console_level)
    
    # Format: simple for normal, detailed for verbose
    if verbose:
        console_format = logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
            datefmt="%H:%M:%S"
        )
    else:
        console_format = logging.Formatter("%(message)s")
    
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler if debug file specified
    if debug_file:
        debug_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(debug_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(file_handler)
    
    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    """Get the Ralph logger, creating with defaults if not configured."""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


def debug_log(
    location: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    hypothesis_id: str = "A",
) -> None:
    """Write structured debug log entry.
    
    This function maintains backward compatibility with the old _debug_log
    function signature while using proper Python logging.
    
    Args:
        location: Code location (e.g., "loop.py:178")
        message: Human-readable message
        data: Optional structured data dictionary
        hypothesis_id: Debug tracking ID
    """
    logger = get_logger()
    
    # Build structured log entry
    log_entry = {
        "location": location,
        "message": message,
        "data": data or {},
        "hypothesisId": hypothesis_id,
        "timestamp": int(time.time() * 1000),
    }
    
    # Log as JSON if file logging enabled, otherwise as formatted string
    if _debug_file:
        logger.debug(json.dumps(log_entry))
    elif _verbose:
        # Formatted debug output for console
        data_str = f" | {data}" if data else ""
        logger.debug(f"[{location}] {message}{data_str}")


def is_verbose() -> bool:
    """Check if verbose mode is enabled."""
    return _verbose
