"""
Context Engineering module (Manus-aligned).

Provides append-only context management, todo recitation,
error preservation, template randomization, and file-based memory.
"""

from .models import ContextEntry
from .context_manager import ContextManager
from .todo_recitation import TodoRecitation
from .error_preservation import ErrorPreservation
from .template_randomizer import TemplateRandomizer
from .file_memory import FileBasedMemory

__all__ = [
    "ContextEntry",
    "ContextManager",
    "TodoRecitation",
    "ErrorPreservation",
    "TemplateRandomizer",
    "FileBasedMemory",
]
