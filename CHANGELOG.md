# Changelog

## v0.1.0 — 2026-03-28

Initial public release.

### Features

- **Task registry** — 50+ benchmark tasks in YAML format spanning Python, JavaScript, Go, TypeScript; difficulty levels easy through expert
- **Task types** — `bug_fix`, `feature_add`, `refactor`, `test_generation`, `dependency_upgrade`, `debug_from_logs`, `multi_file_edit`, `code_review`, `documentation`, `performance`
- **Agent adapters** — Anthropic API adapter (including AWS Bedrock support), Claude Code CLI adapter, mock adapter for testing
- **Docker sandboxes** — fully isolated per-run containers with configurable setup commands and constraints (max turns, max tokens, timeout, network access)
- **Trace collection** — structured event log capturing every tool call, file read/write, command execution, and test run with timestamps and token counts
- **Scoring pipeline** — primary pass/fail criterion (test suite, lint, type check) plus secondary quality checks (diff size, custom scripts)
- **Failure taxonomy** — 10 failure categories (`context_miss`, `wrong_diagnosis`, `correct_plan_bad_execution`, `hallucinated_api`, `incomplete_fix`, `no_verification`, `ignored_test_failure`, `timeout_or_loop`, `regression`, `over_engineering`) with heuristic classification and confidence scores
- **Reporting engine** — table, detail, markdown, and failure-analysis report formats
- **Comparison engine** — side-by-side comparison of two result sets with Fisher's exact test for statistical significance
- **CLI** — `agentbench run`, `experiment`, `report`, `compare`, `trace`, `validate`, `scaffold`, `deep-validate`
- **Task tooling** — `agentbench scaffold` to create new tasks from templates, `agentbench deep-validate` to verify tasks in Docker
- **Experiment configs** — YAML-based multi-agent experiment configuration with runs-per-task and parallelism control
- **Docker base images** — reusable sandbox images for Python, Node.js, and multi-language environments
- **CI pipeline** — separate lint, unit-test, integration-test, and task-validation jobs; PyPI release on tag push
