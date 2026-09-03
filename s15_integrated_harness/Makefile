# s15 integrated harness: run tests, byte-compile modules, clean artifacts.

PY ?= python3

.PHONY: test lint clean

# Run the full test suite (pytest tests/) via run_tests.sh.
test:
	sh run_tests.sh

# Byte-compile every Python module in this directory.
lint:
	$(PY) -m py_compile $(wildcard *.py)

# Remove build/test artifacts (cached bytecode, pytest cache).
clean:
	rm -rf .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	find . -name '*.pyc' -delete
