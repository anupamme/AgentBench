# AgentBench

An eval framework for agentic coding tools.

> ⚠️ Status: Under Active Development — APIs will change

---

## Why AgentBench?

Existing benchmarks like HumanEval and SWE-bench test narrow slices of coding ability — typically single-function completion or isolated bug fixes. Real agentic coding involves multi-step reasoning, codebase navigation, tool use, and test-driven iteration across a full development loop. AgentBench evaluates that complete loop and captures rich traces of *how* agents work — not just whether they pass or fail — enabling deeper analysis of failure modes and improvement opportunities.

---

## Architecture

```
                        ┌─────────────────────────────────────┐
                        │           agentbench CLI             │
                        │  run / experiment / report / compare │
                        └────────────────┬────────────────────┘
                                         │
               ┌─────────────────────────┼─────────────────────────┐
               │                         │                         │
       ┌───────▼───────┐        ┌────────▼────────┐      ┌────────▼────────┐
       │ Task Registry │        │ Agent Adapters  │      │   Experiment    │
       │  (YAML tasks) │        │ Claude Code CLI │      │    Runner       │
       │               │        │ Claude API      │      │  (multi-agent)  │
       └───────┬───────┘        │ Aider / Copilot │      └────────┬────────┘
               │                └────────┬────────┘               │
               └────────────────────┬────┘────────────────────────┘
                                    │
                           ┌────────▼────────┐
                           │    Sandbox      │
                           │  (Docker-based) │
                           │  isolated env   │
                           └────────┬────────┘
                                    │
               ┌────────────────────┼────────────────────┐
               │                    │                    │
       ┌───────▼───────┐   ┌────────▼────────┐  ┌───────▼───────┐
       │ Trace Collect │   │    Scoring      │  │   Failure     │
       │ tool calls    │   │  correctness    │  │ Classifier    │
       │ file diffs    │   │  code quality   │  │ context_miss  │
       │ token usage   │   │  efficiency     │  │ halluc_api    │
       └───────┬───────┘   └────────┬────────┘  └───────┬───────┘
               │                    │                    │
               └────────────────────┼────────────────────┘
                                    │
                           ┌────────▼────────┐
                           │    Results      │
                           │  (JSON / YAML)  │
                           └────────┬────────┘
                                    │
                           ┌────────▼────────┐
                           │   Reporting     │
                           │ table/markdown  │
                           │ compare / diff  │
                           └─────────────────┘
```

---

## Quick Start

```bash
pip install -e ".[dev]"
agentbench --help
```

---

## Project Structure

```
src/agentbench/
├── cli/            # Typer CLI — entry point for all commands
├── core/           # Pydantic models and global configuration
├── sandbox/        # Docker-based isolated execution environments
├── adapters/       # Pluggable agent adapters (Claude, Aider, etc.)
├── trace/          # Trace collection during agent runs
├── scoring/        # Multi-dimensional scoring pipeline
├── classification/ # Failure mode classification
└── reporting/      # Report generation (table, markdown, JSON)
```

---

## Contributing

Contribution guidelines coming soon. For now, open an issue to discuss.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
