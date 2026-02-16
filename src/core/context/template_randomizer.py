"""
Structural noise injection — prevent few-shot lock-in.

Manus Principle 6: "If you put 2-3 similar examples in the prompt,
the LLM will lock onto that format. Introduce structural noise."

Implementation deferred to Phase 2.
"""

import random
from typing import Optional

from ..feature_flags import FeatureFlags, feature_flags as default_flags


class TemplateRandomizer:
    """Randomize prompt wrappers to prevent few-shot pattern lock-in."""

    _INSTRUCTION_WRAPPERS = [
        "{instruction}",
        "Please help with the following: {instruction}",
        "Task: {instruction}",
        "I need your help. {instruction}",
    ]

    _QUALITY_SUFFIXES = [
        "",
        " Be thorough and accurate.",
        " Provide a clear and helpful response.",
        " Think step by step if needed.",
    ]

    def __init__(self, feature_flags: Optional[FeatureFlags] = None):
        self._flags = feature_flags or default_flags

    def wrap_instruction(self, instruction: str) -> str:
        """Wrap instruction with randomized template."""
        wrapper = random.choice(self._INSTRUCTION_WRAPPERS)
        suffix = random.choice(self._QUALITY_SUFFIXES)
        return wrapper.format(instruction=instruction) + suffix
