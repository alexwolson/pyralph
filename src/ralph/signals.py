"""Ralph signal constants and utilities.

Signals are used to communicate between Ralph agents and the loop controller.
They are embedded in agent output using the format: <ralph>SIGNAL_NAME</ralph>
"""

from enum import Enum
from typing import Optional


class Signal(str, Enum):
    """Ralph signals for agent-loop communication.
    
    Signals are emitted by agents to indicate state changes or requests.
    The loop controller detects these in agent output and takes appropriate action.
    """
    
    # Task lifecycle signals
    COMPLETE = "COMPLETE"      # Agent believes task is complete
    ROTATE = "ROTATE"          # Agent requests fresh context (token limit)
    GUTTER = "GUTTER"          # Agent is stuck and needs different provider
    
    # Interactive signals
    QUESTION = "QUESTION"      # Agent has a question for the user
    
    # Verification signals
    VERIFY_PASS = "VERIFY_PASS"  # Verification agent approves completion
    VERIFY_FAIL = "VERIFY_FAIL"  # Verification agent rejects completion
    
    # Internal signals (not emitted by agents, used by loop)
    WARN = "WARN"              # Token count approaching threshold
    
    # Interview mode signal
    DONE = "DONE"              # Interview task file creation complete
    
    def __str__(self) -> str:
        """Return the signal value for string comparison."""
        return self.value


def make_tag(signal: Signal) -> str:
    """Create a signal tag string for embedding in output.
    
    Args:
        signal: The Signal enum value
        
    Returns:
        The formatted tag string, e.g., "<ralph>COMPLETE</ralph>"
    """
    return f"<ralph>{signal.value}</ralph>"


def detect_signal(text: str) -> Optional[Signal]:
    """Detect if text contains a Ralph signal tag.
    
    Args:
        text: Text to search for signal tags
        
    Returns:
        The detected Signal, or None if no signal found.
        Returns the first signal found if multiple are present.
    """
    # Check for each signal's tag in the text
    for signal in Signal:
        if make_tag(signal) in text:
            return signal
    return None


# Pre-built tag constants for common use
TAG_COMPLETE = make_tag(Signal.COMPLETE)
TAG_ROTATE = make_tag(Signal.ROTATE)
TAG_GUTTER = make_tag(Signal.GUTTER)
TAG_QUESTION = make_tag(Signal.QUESTION)
TAG_VERIFY_PASS = make_tag(Signal.VERIFY_PASS)
TAG_VERIFY_FAIL = make_tag(Signal.VERIFY_FAIL)
TAG_DONE = make_tag(Signal.DONE)


# Signal sets for common checks
CRITICAL_SIGNALS = frozenset({
    Signal.ROTATE,
    Signal.GUTTER,
    Signal.COMPLETE,
    Signal.QUESTION,
    Signal.VERIFY_PASS,
    Signal.VERIFY_FAIL,
})

VERIFICATION_SIGNALS = frozenset({
    Signal.VERIFY_PASS,
    Signal.VERIFY_FAIL,
    Signal.ROTATE,
    Signal.GUTTER,
})
