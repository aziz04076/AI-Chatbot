from typing import List, Dict, Any
import logging

logger = logging.getLogger("NexusAI-Memory")

class ConversationMemory:
    """
    Manages session and persistent context windows with auto-summarization
    to maintain high fidelity across long conversational turns.
    """
    def __init__(self):
        # session_id -> list of {"role": str, "content": str}
        self._sessions: Dict[str, List[Dict[str, str]]] = {}
        self._summaries: Dict[str, str] = {}

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        return self._sessions.get(session_id, [])

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append({"role": role, "content": content})
        self._check_and_summarize(session_id)

    def _check_and_summarize(self, session_id: str):
        """Auto-summarizes when history exceeds 8 turns."""
        history = self._sessions.get(session_id, [])
        if len(history) > 8 and session_id not in self._summaries:
            logger.info(f"Auto-summarizing long conversation for session {session_id}")
            # Compact summary of the discussion
            topics = [msg["content"][:60] for msg in history[:6] if msg["role"] == "user"]
            summary = f"Prior discussion focused on: {'; '.join(topics)}."
            self._summaries[session_id] = summary

    def get_prompt_context(self, session_id: str, max_messages: int = 6) -> List[Dict[str, str]]:
        """Returns summarized context plus the recent turns."""
        history = self._sessions.get(session_id, [])
        recent = history[-max_messages:] if len(history) > max_messages else history

        summary = self._summaries.get(session_id)
        if summary and recent:
            return [{"role": "system", "content": f"Context Summary of previous turns: {summary}"}] + recent
        return recent

    def clear(self, session_id: str):
        self._sessions.pop(session_id, None)
        self._summaries.pop(session_id, None)

memory_manager = ConversationMemory()
