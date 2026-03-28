"""Verify that the string guard is extracted into a shared helper."""

import ast
import sys

with open("validators.py") as f:
    source = f.read()

tree = ast.parse(source)

guard_pattern = "not value or not isinstance(value, str)"
occurrences = source.count(guard_pattern)

if occurrences > 1:
    print(f"FAIL: guard pattern appears {occurrences} times — extract it into a helper function")
    sys.exit(1)
elif occurrences == 0:
    # Check that a helper-like function exists
    func_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if not any(
        n.startswith("_require") or n.startswith("_check") or n.startswith("_validate_str")
        for n in func_names
    ):
        print("FAIL: guard removed but no helper function found")
        sys.exit(1)

print("OK: duplication check passed")
