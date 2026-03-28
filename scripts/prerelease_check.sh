#!/bin/bash
set -e
echo "=== Pre-release checklist ==="

echo "1. Lint..."
ruff check src/ tests/
ruff format --check src/ tests/

echo "2. Type check..."
mypy src/agentbench/ --ignore-missing-imports

echo "3. Unit tests..."
pytest tests/ -v -m "not docker" --tb=short

echo "4. Task validation..."
python scripts/validate_tasks.py

echo "5. Build package..."
python -m build

echo "6. Check package..."
twine check dist/*

echo "=== All checks passed ==="
