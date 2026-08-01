"""
core/planner.py — Decomposes a complex goal into an ordered list of sub-tasks
"""

import json
import anthropic


def make_plan(goal: str, memory_context: str, client: anthropic.Anthropic) -> list[str]:
    """
    Ask Claude to break a goal into concrete sub-tasks.
    Returns a list of step strings, or [goal] if planning isn't needed.
    """
    prompt = f"""You are a planning assistant. Given a goal, decompose it into 2–6 concrete, ordered sub-tasks that an AI agent can execute one by one using tools (web search, fetch page, run code, read/write files).

If the goal is simple and needs only 1 step, return a single-item list.

Long-term memory context (may be relevant):
{memory_context}

Goal: {goal}

Respond ONLY with a JSON array of strings. Example:
["Search for X", "Fetch the top result", "Extract data and write to file"]"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = "\n".join(text.splitlines()[1:])
        text = text.rstrip("`").strip()

    try:
        plan = json.loads(text)
        if isinstance(plan, list) and all(isinstance(s, str) for s in plan):
            return plan
    except Exception:
        pass

    # Fallback: treat the whole goal as one step
    return [goal]
