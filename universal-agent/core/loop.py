"""
core/loop.py — Agentic loop: runs a single task until completion or max iterations
"""

import json
import anthropic
from tools.tools import TOOL_DEFINITIONS, dispatch


SYSTEM_PROMPT = """You are a universal AI agent. You have access to tools for web search, fetching pages, running code, reading and writing files, and checking the time.

For each task given to you:
1. Think about what you need to do.
2. Use the appropriate tools to accomplish it.
3. After completing the task, output a concise plain-text summary of what you did and what you found or created.
4. If something fails, try an alternative approach before giving up.

{memory_section}"""


def run_task(
    task: str,
    memory,
    client: anthropic.Anthropic,
    max_iterations: int = 8,
    verbose: bool = True
) -> str:
    """
    Run the agent loop for a single task.
    Returns the final text summary produced by Claude.
    """
    memory_context = memory.recall()
    system = SYSTEM_PROMPT.format(
        memory_section=f"\nWhat you already know (long-term memory):\n{memory_context}"
        if memory_context != "No long-term memories yet."
        else ""
    )

    # Build messages: inject prior short-term context + this task
    messages = memory.get_messages() + [{"role": "user", "content": task}]

    if verbose:
        print(f"\n  📋 Task: {task}")

    final_text = ""

    for i in range(max_iterations):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            tools=TOOL_DEFINITIONS,
            messages=messages
        )

        tool_calls = []
        text_parts = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

        if text_parts:
            final_text = "".join(text_parts)
            if verbose:
                print(f"\n  💬 {final_text}")

        # Done — no more tool calls
        if not tool_calls or response.stop_reason == "end_turn":
            messages.append({"role": "assistant", "content": response.content})
            break

        # Append assistant turn and execute tools
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tc in tool_calls:
            if verbose:
                args_preview = json.dumps(tc.input, ensure_ascii=False)[:100]
                print(f"\n  🔧 {tc.name}({args_preview})")
            result_str = dispatch(tc.name, tc.input)
            if verbose:
                print(f"     → {result_str[:180]}{'…' if len(result_str) > 180 else ''}")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result_str
            })

        messages.append({"role": "user", "content": tool_results})

    # Persist this task + response to short-term memory
    memory.add_message("user", task)
    memory.add_message("assistant", final_text or "[task completed]")

    return final_text
