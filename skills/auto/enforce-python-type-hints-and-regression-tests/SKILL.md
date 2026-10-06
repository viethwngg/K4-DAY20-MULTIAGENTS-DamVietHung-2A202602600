---
name: enforce-python-type-hints-and-regression-tests
description: Use when writing or updating Python packages to ensure all public functions have complete type annotations, regression tests are added for each fixed bug, and changelog entries are recorded properly.
---
1. Identify all public functions in the package (functions whose names do not start with '_').
2. Verify each public function has type annotations on all parameters and the return value.
3. If any public function lacks type hints, add them following PEP 484 conventions.
4. For each bug fixed in the current task, add one test function in tests/test_regressions.py.
   - Ensure there are at least three such test functions if three or more bugs were fixed.
5. Run the full test suite to confirm all tests pass, including the new regression tests.
6. Update CHANGELOG.md under the heading '## Unreleased' by adding one bullet per fix:
   - Format: `- fix(<function name>): <short description>`
   - Include at least three bullets if three or more fixes were made.
7. Confirm no unrelated files or requirements are changed.
8. Before submission, run `pytest --maxfail=1 --disable-warnings -q workspace/tests` with PYTHONPATH set if needed to ensure import correctness.
9. Verify that all changes preserve existing docstrings and coding style.
