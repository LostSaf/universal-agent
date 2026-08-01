# Universal Agent

A multi-tool agent built on Anthropic's tool-use API. It decomposes a goal into
ordered sub-tasks, executes each one against real tools, and carries memory
across sessions instead of restarting cold every run.

```
you ──▶ planner ──▶ [step 1] ──▶ agent loop ──▶ tools ──┐
                    [step 2] ──▶ agent loop ──▶ tools ──┤
                    [step 3] ──▶ agent loop ──▶ tools ──┤
                                                        ▼
                                                   synthesis ──▶ answer
                                                        │
                                                        ▼
                                              long-term memory
```

## Run it

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
python agent.py
```

You get a REPL. Type a goal. Commands: `/memory`, `/forget`, `/clear`, `/quit`.

```
> find the three most recent papers on speculative decoding and summarise the differences

⏳ Planning…
📋 Plan (3 steps):
   1. Search for recent speculative decoding papers
   2. Fetch and read each paper's abstract
   3. Compare the approaches
```

## Layout

| Path | What it does |
|---|---|
| `agent.py` | Entry point. REPL, plan/execute orchestration, session summarisation. |
| `core/planner.py` | Turns a goal into an ordered list of sub-tasks, or `[goal]` if it's simple enough not to need decomposing. |
| `core/loop.py` | Runs one task to completion: model call → tool call → result → repeat, bounded by `max_iterations`. |
| `tools/tools.py` | The seven tools and the dispatcher that routes a tool-use block to the right handler. |
| `memory/memory.py` | Two layers — session conversation, and persistent facts/summaries in JSON. |

## Design notes

**Planning is conditional, not mandatory.** `make_plan` returns a single-element
list when a goal doesn't need breaking down. A planner that always decomposes
turns "what time is it" into a three-step project and burns tokens proving it.

**The loop is bounded.** `run_task` takes `max_iterations` because the failure
mode of an agentic loop isn't a wrong answer, it's a loop that never terminates
and quietly spends money. Hitting the bound returns what it has rather than
raising.

**Memory is two layers, not one.** Session history is the working context and
dies with the process. Long-term memory holds distilled facts and one-line
session summaries written on exit. Mixing them means either forgetting
everything on restart or dragging an entire transcript into every prompt.

**Tool results are dispatched, not trusted.** `dispatch` is the single place a
model-chosen tool name and argument dict become a real call, which makes it the
single place to validate them. Malformed arguments and tool-level exceptions
come back as tool results the model can react to, rather than exceptions that
kill the run.

## Tools

`search_web` · `fetch_page` · `run_code` · `read_file` · `write_file` ·
`list_files` · `get_datetime`

`run_code` executes Python in a subprocess against a temp file. It is not
sandboxed. Don't point this at anything you care about, and don't run it on a
machine where arbitrary code execution matters.

## Known limitations

- No retry/backoff on API calls — a transient 529 fails the step.
- No token budget across a multi-step plan; each step is bounded, the plan isn't.
- Memory grows unboundedly; there's no compaction pass.
- Single-threaded and synchronous throughout.
