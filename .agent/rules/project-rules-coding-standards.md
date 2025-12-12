---
trigger: always_on
---

# Project Rules & Coding Standards

You are an expert Python developer contributing to an open-source project. Your goal is to generate clean, consistent, and well-tested code that strictly adheres to the project's established standards.

**IMPORTANT:** Do not make assumptions about coding style or testing frameworks. Follow the rules below strictly.

## 1. Code Style & Formatting (Strict)
* **Formatter:** You MUST follow **Black** formatting rules.
    * Do not output code that violates Black's style (e.g., ensure strict 88-character line limits, use double quotes for strings where possible).
* **Linting:** You MUST ensure code complies with **Flake8**.
    * Avoid logic or syntax that triggers Flake8 errors.
    * If a Flake8 rule conflicts with Black, prioritize Black (Black takes precedence).
* **Imports:** Organize imports according to PEP8 (Standard library -> Third party -> Local application).

## 2. Type Hinting (Mandatory for New Code)
* Although the CI might treat type hints as "encouraged," you **MUST** add type hints to **ALL** new functions, methods, and class definitions you generate.
* Use standard `typing` module or modern Python 3.9+ syntax (e.g., `list[str]` instead of `List[str]`).
* Example:
    ```python
    # DO THIS:
    def calculate_total(items: list[float]) -> float:
        ...

    # DO NOT DO THIS:
    def calculate_total(items):
        ...
    ```

## 3. Testing Standards (Strict)
* **Framework:** Use **pytest** exclusively. Do NOT use `unittest` or other frameworks.
* **Requirement:** Every new feature or bug fix **MUST** be accompanied by a non-trivial test case.
* **Definition of "Non-trivial":** Tests must verify logic, edge cases, and expected failures. Do not write placeholder tests like `assert True`.
* **File Location:** Place tests in the standard `tests/` directory or alongside the module, matching the existing project structure.

## 4. Behavior & Workflow
* **No Hallucinations:** Do not invent library dependencies that are not already present in the project (check `requirements.txt` or `pyproject.toml` first). If a new library is needed, explicitly ask for permission to add it.
* **Context Awareness:** Before editing a file, read the existing code to match naming conventions (variables, internal functions) unless they violate the standards above.
* **Documentation:** Add docstrings to all public modules, classes, and functions following PEP 257 conventions.

## 5. Command Reference (For Context Only)
* Formatting: `black .`
* Linting: `flake8 .`
* Testing: `pytest`