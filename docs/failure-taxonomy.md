# Failure Taxonomy

AgentBench classifies agent failures into 10 categories. This document describes each category, how it is detected, and what it means for agent improvement.

## Categories

### `context_miss`

**Description:** The agent didn't read the files relevant to solving the task before attempting edits.

**Detection:** The trace's `FILE_READ` events don't include the files listed in `task.setup.files_to_highlight`, or the files where the known fix should be applied (when a reference solution is available).

**Example:** A bug in `src/auth/validator.py` requires understanding `src/auth/models.py`. The agent edits `validator.py` without ever reading `models.py`, leading to an incorrect fix.

**Improvement signal:** The agent needs better context-gathering behavior — either more aggressive file exploration at the start, or better ability to follow import chains.

---

### `wrong_diagnosis`

**Description:** The agent correctly read the relevant files but misidentified the root cause, and edited files that are unrelated to the fix.

**Detection:** When a reference solution is available, the files in the agent's diff don't overlap with the files changed in the solution. The agent targeted the wrong location.

**Example:** A bug in `database.py` causes a `KeyError` that surfaces in `api.py`. The agent sees the traceback pointing to `api.py` and adds error handling there instead of fixing the root cause in `database.py`.

**Improvement signal:** The agent needs better root-cause analysis skills — following tracebacks to their origin, distinguishing symptom files from cause files.

---

### `correct_plan_bad_execution`

**Description:** The agent identified the right files and the right general approach, but the implementation has bugs — tests still fail after the edit.

**Detection:** The agent's diff touches the files where the fix should be (matching the reference solution location), but the primary eval still fails.

**Example:** The fix requires changing `if x = None` to `if x is None`. The agent correctly identifies `utils.py` as the file to fix and the right line, but introduces a syntax error in the process.

**Improvement signal:** The agent is close — it needs better code generation precision, or better test-driven iteration (run tests after each edit, not just at the end).

---

### `hallucinated_api`

**Description:** The agent used functions, methods, classes, or imports that don't exist in the codebase or its dependencies.

**Detection:** New imports or function calls in the agent's edits reference symbols that aren't present in the original codebase (checked via grep for the symbol name).

**Example:** The agent writes `from utils import parse_config_v2` but only `parse_config` exists. Or it calls `df.to_json_lines()` which is not a real pandas method.

**Improvement signal:** The agent needs better grounding in the actual codebase. More file reading before writing, or checking that symbols exist before using them.

---

### `incomplete_fix`

**Description:** The agent made progress — some tests pass — but didn't complete the full fix.

**Detection:** The primary eval fails, but the partial score is greater than 0 and less than 1.0 (when scoring runs multiple test files or test cases).

**Example:** A task requires fixing both `divide()` and `multiply()`. The agent only fixes `divide()`, so half the tests pass.

**Improvement signal:** The agent may be stopping too early, or may not be reading the full test file to understand all the requirements.

---

### `no_verification`

**Description:** The agent made edits but never ran the tests to check its work before declaring done.

**Detection:** No `TEST_RUN` event and no `COMMAND_EXEC` event matching a test pattern appears in the trace before `AGENT_DONE`.

**Example:** The agent reads the code, makes an edit, and immediately says "I've fixed the bug." It never ran `pytest` to verify.

**Improvement signal:** The agent needs stronger test-driven iteration — treating test runs as a required step before completion, not an optional one.

---

### `ignored_test_failure`

**Description:** The agent ran the tests, saw failures, but declared done anyway without attempting to fix the failures.

**Detection:** A `TEST_RUN` event shows a non-zero exit code, followed by `AGENT_DONE` without any intervening `FILE_WRITE` events.

**Example:** Agent runs `pytest`, sees `FAILED tests/test_calc.py::test_divide_by_zero`, then responds "I've applied the fix" without editing anything further.

**Improvement signal:** The agent needs to treat failing tests as feedback to act on, not as information to acknowledge. Stronger instruction following or a more persistent iteration loop.

---

### `timeout_or_loop`

**Description:** The agent exceeded its resource budget — max turns, max tokens, or wall-clock timeout.

**Detection:** A `CONSTRAINT_HIT` event appears at the end of the trace.

**Example:** The agent gets stuck in a loop of reading files and re-reading files without making progress. After 50 turns it hits `max_turns`.

**Improvement signal:** The agent may be in an exploration loop without a convergence strategy. Adding better "am I making progress?" checks, or reducing unnecessary re-reads.

---

### `regression`

**Description:** The agent fixed the target tests but broke other tests that were passing before.

**Detection:** The primary eval passes, but a secondary `test_suite` eval on a broader test suite fails.

**Example:** The agent fixes `test_divide_by_zero` by hardcoding `raise ValueError` unconditionally, breaking `test_normal_division`.

**Improvement signal:** The agent needs to run the full test suite, not just the specific failing test, before declaring done.

---

### `over_engineering`

**Description:** The agent produced a correct fix but the change is unnecessarily large or complex — it rewrote unrelated code or introduced abstractions not needed for the task.

**Detection:** The secondary `diff_size` eval fails (agent changed more lines than `max_lines_changed`), or the diff includes changes to files completely unrelated to the task.

**Example:** To fix a one-line bug, the agent refactors the entire module, renames variables, and adds a new helper class.

**Improvement signal:** The agent needs stronger scope-limiting — do the minimum required to make the tests pass.

---

### `unknown`

**Description:** The run failed but doesn't match any of the above patterns.

**Detection:** Fallback when no other category has sufficient evidence.

---

## How Heuristic Classification Works

The classifier (`src/agentbench/classification/classifier.py`) processes each failed run:

1. Load the trace and scoring result
2. For each category, check its detection criteria against the trace events and diff
3. Each check returns a `(matched: bool, evidence: list[str])` tuple
4. The category with the most evidence becomes the primary classification
5. All matched categories are reported as secondary classifications
6. Confidence is computed from the number and strength of evidence items

## How to Add New Rules

To add a new failure category:

1. Add the new enum value to `FailureCategory` in `src/agentbench/classification/taxonomy.py`
2. Add a detection method in `src/agentbench/classification/classifier.py` following the pattern of existing methods
3. Register the new method in the classifier's category dispatch table
4. Add test cases in `tests/test_classifier.py`

## Using Failure Data to Improve Agents

```bash
# View failure breakdown for a result set
agentbench report results/ --format failure

# Example output:
# Failure Category     Count  %
# context_miss           8   32%
# incomplete_fix         5   20%
# no_verification        4   16%
# hallucinated_api       3   12%
# wrong_diagnosis        2    8%
# other                  3   12%
```

**If `context_miss` is high:** Your agent isn't exploring the codebase enough at the start. Try adding explicit instructions to read related files, or use a more structured exploration phase.

**If `no_verification` or `ignored_test_failure` is high:** Your agent isn't running tests consistently. Add explicit test-run requirements to the system prompt or agent loop.

**If `hallucinated_api` is high:** Your agent is generating code from memory rather than from the actual codebase. Prompt it to verify symbols exist before using them.

**If `timeout_or_loop` is high:** Your agent may be over-exploring. Consider adding progress-check logic or reducing `max_turns` to force more decisive behavior.
