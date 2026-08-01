"""
agent.py — Universal AI Agent entry point
------------------------------------------
Run:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python agent.py
"""

import os
import sys
import anthropic

from memory.memory import Memory
from core.planner import make_plan
from core.loop import run_task


BANNER = """
╔══════════════════════════════════════════════════════════╗
║              🤖  Universal AI Agent                      ║
║  Tools: web search · fetch pages · run code · files     ║
║  Memory: persistent across sessions                      ║
║  Planning: complex goals auto-decomposed                 ║
╚══════════════════════════════════════════════════════════╝
Commands:  /memory   show long-term memory
           /forget   wipe long-term memory
           /clear    clear session history
           /quit     exit
"""


def summarise_session(memory: Memory, client: anthropic.Anthropic):
    """Ask Claude to summarise the session and store it in long-term memory."""
    transcript = memory.session_text()
    if not transcript.strip():
        return
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": f"Summarise this agent session in 1-2 sentences for future reference:\n\n{transcript[-3000:]}"
        }]
    )
    summary = response.content[0].text.strip()
    memory.add_summary(summary)
    print(f"\n📝 Session summary saved: {summary}")


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌  ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    memory = Memory()

    print(BANNER)

    # Greet with memory context
    recalled = memory.recall(max_facts=5, max_summaries=1)
    if recalled != "No long-term memories yet.":
        print(f"🧠 I remember some things from last time:\n{recalled}\n")

    try:
        while True:
            try:
                user_input = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input:
                continue

            # ── Built-in commands ──────────────────────────────────────────
            if user_input.lower() == "/quit":
                break
            elif user_input.lower() == "/memory":
                print("\n🧠 Long-term memory:\n" + memory.recall())
                continue
            elif user_input.lower() == "/forget":
                memory.forget_all()
                print("🗑️  Long-term memory wiped.")
                continue
            elif user_input.lower() == "/clear":
                memory.clear_session()
                print("🗑️  Session history cleared.")
                continue

            # ── Plan + execute ─────────────────────────────────────────────
            print("\n⏳ Planning…")
            plan = make_plan(user_input, memory.recall(), client)

            if len(plan) == 1:
                # Simple goal — run directly
                run_task(plan[0], memory, client, verbose=True)
            else:
                print(f"\n📋 Plan ({len(plan)} steps):")
                for idx, step in enumerate(plan, 1):
                    print(f"   {idx}. {step}")

                results = []
                for idx, step in enumerate(plan, 1):
                    print(f"\n{'─'*55}\n🚀 Step {idx}/{len(plan)}")
                    result = run_task(step, memory, client, verbose=True)
                    results.append(result)

                # Final synthesis
                print(f"\n{'─'*55}\n✅ All steps complete. Synthesising…\n")
                synthesis_prompt = (
                    f"The user asked: {user_input}\n\n"
                    f"Here are the results of each step:\n" +
                    "\n\n".join(f"Step {i+1}: {r}" for i, r in enumerate(results)) +
                    "\n\nWrite a clean, concise final answer for the user."
                )
                run_task(synthesis_prompt, memory, client, max_iterations=1, verbose=True)

    finally:
        summarise_session(memory, client)
        print("\n👋 Goodbye!\n")


if __name__ == "__main__":
    main()
