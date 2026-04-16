from typing import List, Dict

class ContextManager:
    """
    Manages the conversation context (message history).
    """
    def __init__(self):
        self.history: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str):
        """Adds a message to the history."""
        self.history.append({"role": role, "content": content})

    def get_history(self) -> List[Dict[str, str]]:
        """Returns the full message history."""
        return self.history

    def clear_history(self):
        """Clears the message history."""
        self.history = []
