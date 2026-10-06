---
name: enforce-public-function-type-hints
description: Use when writing or reviewing code to ensure every public function has complete type annotations on all parameters and the return value, preventing missing or partial type hints.
---
1. Identify all functions in the codebase or new code.
2. For each function, check if its name starts with an underscore (_); if yes, skip it (considered private).
3. For each public function:
   - Verify that every parameter has an explicit type annotation.
   - Verify that the return type is explicitly annotated.
4. If any parameter or return type is missing annotation:
   - Add appropriate type hints based on the function’s logic and usage.
   - Use standard typing constructs (e.g., Optional, Union) as needed.
5. After adding annotations, run a static type checker (e.g., mypy) to confirm no type errors.
6. Commit changes only if all public functions have complete type annotations.
7. Document any assumptions or complex types in docstrings if necessary.
8. Repeat this check for all new or modified code before finalizing.
