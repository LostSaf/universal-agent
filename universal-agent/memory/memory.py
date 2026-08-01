"""
memory/memory.py — Short-term (conversation) + long-term (persistent JSON) memory
"""

import json
import os
from datetime import datetime

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "long_term_memory.json")


class Memory:
    """
    Two-layer memory system:
    - short_term: the full message history for the current session
    - long_term:  key facts/summaries persisted to disk across sessions
    """

    def __init__(self):
        self.short_term: list[dict] = []          # current session messages
        self.long_term: dict = self._load()        # persisted across runs

    # ── Long-term persistence ──────────────────────────────────────────────

    def _load(self) -> dict:
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"facts": [], "summaries": [], "last_updated": None}

    def _save(self):
        self.long_term["last_updated"] = datetime.now().isoformat()
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.long_term, f, indent=2, ensure_ascii=False)

    def remember(self, fact: str):
        """Store a fact in long-term memory."""
        if fact not in self.long_term["facts"]:
            self.long_term["facts"].append(fact)
            self._save()

    def add_summary(self, summary: str):
        """Store a session summary in long-term memory."""
        entry = {"timestamp": datetime.now().isoformat(), "summary": summary}
        self.long_term["summaries"].append(entry)
        # Keep last 20 summaries
        self.long_term["summaries"] = self.long_term["summaries"][-20:]
        self._save()

    def recall(self, max_facts: int = 10, max_summaries: int = 3) -> str:
        """Return a formatted string of long-term memories to inject into the system prompt."""
        parts = []
        if self.long_term["facts"]:
            facts = self.long_term["facts"][-max_facts:]
            parts.append("Known facts:\n" + "\n".join(f"- {f}" for f in facts))
        if self.long_term["summaries"]:
            summaries = self.long_term["summaries"][-max_summaries:]
            parts.append("Recent session summaries:\n" + "\n".join(
                f"[{s['timestamp'][:10]}] {s['summary']}" for s in summaries
            ))
        return "\n\n".join(parts) if parts else "No long-term memories yet."

    def forget_all(self):
        """Wipe long-term memory (user-triggered)."""
        self.long_term = {"facts": [], "summaries": [], "last_updated": None}
        self._save()

    # ── Short-term (session) ───────────────────────────────────────────────

    def add_message(self, role: str, content):
        """Append a message to the current session history."""
        self.short_term.append({"role": role, "content": content})

    def get_messages(self) -> list[dict]:
        return self.short_term

    def clear_session(self):
        self.short_term = []

    def session_text(self) -> str:
        """Return a plain-text transcript of the current session for summarisation."""
        lines = []
        for m in self.short_term:
            role = m["role"].upper()
            if isinstance(m["content"], str):
                lines.append(f"{role}: {m['content']}")
            elif isinstance(m["content"], list):
                for block in m["content"]:
                    if isinstance(block, dict) and block.get("type") == "text":
                        lines.append(f"{role}: {block['text']}")
        return "\n".join(lines)
