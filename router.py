# This module checks the user's spoken words and classifies them into one of 4 categories:

# DIRECT_TOOL: Commands with an obvious tool (time, media controls, system stats) that can execute instantly.
# CONVERSATION: Normal chat that needs LLM thinking.
# AGENT_TASK: Multi-step reasoning tasks.
# UNKNOWN: Default fallback to LLM.


# backend/router.py
import re
from typing import Tuple, Optional, Any

class IntentRouter:
    """
    Evaluates raw user transcripts to bypass the LLM for deterministic commands.
    """

    # Direct keyword patterns for instant zero-LLM execution
    PATTERNS = {
        "time": [
            r"\b(what('s| is) the time|current time|tell me the time|what time is it)\b",
            r"\b(what('s| is) the date|today('s)? date)\b"
        ],
        "media_pause": [
            r"\b(pause( the)? (music|song|video|playback)?)\b",
            r"\b(stop( the)? (music|song|audio))\b"
        ],
        "media_play": [
            r"\b(play( the)? (music|song|playback)?|resume( the)? (music|song)?)\b"
        ],
        "media_next": [
            r"\b(next (track|song)|skip (this )?(song|track))\b"
        ],
        "system_status": [
            r"\b(cpu usage|ram usage|system status|check system|computer status)\b"
        ],
    }

    @classmethod
    def classify(cls, text: str) -> Tuple[str, Optional[str]]:
        """
        Returns (intent_type, action_name)
        intent_type: 'DIRECT_TOOL' or 'CONVERSATION'
        """
        cleaned = text.strip().lower()

        for action, regex_list in cls.PATTERNS.items():
            for pattern in regex_list:
                if re.search(pattern, cleaned):
                    return ("DIRECT_TOOL", action)

        return ("CONVERSATION", None)
    
    

# Line-by-Line Explanation:
# PATTERNS: A dictionary containing fast regular expressions that catch common deterministic voice commands.
# re.search(pattern, cleaned): Checks if the user's spoken sentence matches any of the fast-path triggers.
# return ("DIRECT_TOOL", action): Signals to the agent to trigger the tool immediately without waiting for the LLM.
