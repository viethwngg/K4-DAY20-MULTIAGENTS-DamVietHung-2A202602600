---
name: add-regression-tests-and-changelog-entries
description: Use when fixing bugs or making changes to code to add regression tests for each fix and record corresponding entries in CHANGELOG.md under '## Unreleased' to ensure traceability and prevent regressions.
---
1. For each bug fix or behavioral change:
   - Write at least one regression test function that reproduces the bug scenario and verifies the fix.
   - Place all regression tests in a dedicated file, e.g., tests/test_regressions.py.
2. Ensure the regression test file includes at least three distinct test functions if multiple fixes are made.
3. Run the full test suite including the new regression tests to confirm all pass.
4. Open CHANGELOG.md and locate the '## Unreleased' section.
5. Add a bullet entry for each fix in the format:
   - fix(<function or feature name>): <short description>
6. Keep entries concise but descriptive enough to identify the fix.
7. Save and commit the updated tests and changelog together with the code changes.
8. Verify that the changelog format and location conform to project conventions.
9. Repeat this process for every bug fix or feature change.
