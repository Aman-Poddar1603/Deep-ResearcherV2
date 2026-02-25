---
trigger: always_on
---

# =====================================================
# DEEP RESEARCHER — DOCUMENTATION RULES (MANDATORY)
# =====================================================

When generating or modifying code, documentation MUST follow
proper Markdown formatting standards similar to professional
Python library documentation.

Only documentation rules are defined here.

--------------------------------------------------------
DOs (REQUIRED)
--------------------------------------------------------

## 1. Docstring Requirement

ALWAYS add a docstring to:

- Every public function
- Every class
- Every module
- Any non-trivial private function

Docstrings MUST be formatted using structured Markdown.

---

## 2. Markdown Structure (STRICT FORMAT)

Documentation MUST follow this order:

```python
def example_function(param1: str, param2: int) -> dict:
    """
    ## Description

    Short, precise explanation of what this function does.
    Focus on outcome and purpose, not implementation details.

    ## Parameters

    - `param1` (`str`)
      - Description: Natural language query.
      - Constraints: Must be non-empty.
      - Example: "latest AI research"

    - `param2` (`int`)
      - Description: Maximum result count.
      - Constraints: Must be >= 1.

    ## Returns

    `dict`

    Structure:

    ```json
    {
        "status": "success | error",
        "results": ["string"]
    }
    ```

    ## Raises

    - `ValueError`
      - When input validation fails.

    ## Side Effects

    - Calls external research API.
    - May trigger LLM inference.

    ## Debug Notes

    - Check embedding output length.
    - Validate API response schema.

    ## Customization

    Modify ranking logic inside `_rank_results()`.
    """
```

---

## 3. Formatting Rules

- Use Markdown headings inside docstrings:

  - `## Description`
  - `## Parameters`
  - `## Returns`
  - `## Raises`
  - `## Side Effects`
  - `## Debug Notes`
  - `## Customization`

- Parameter names MUST be wrapped in backticks:

  Example:

  ```
  `query` (`str`)
  ```

- Types MUST always be specified.

- Nested structures MUST use fenced code blocks:

  - ```json for dict schemas
  - ```python for examples.

---

## 4. Parameter Documentation Rules

Each parameter MUST include:

- Name
- Type
- Description
- Constraints
- Example (when applicable)

---

## 5. Return Documentation Rules

If returning structured data:

- Provide full schema using JSON code block.
- Do NOT write vague descriptions like "returns dict".

---

## 6. LLM Output Documentation

If function processes LLM output:

- Document expected schema explicitly.
- Specify assumptions about structure.
- Describe validation expectations.

---

## 7. Consistency Rules

- Maintain identical section ordering across all functions.
- Do NOT mix documentation styles.
- Avoid inline messy formatting.

---

--------------------------------------------------------
DON'Ts (FORBIDDEN)
--------------------------------------------------------

- Do NOT write vague descriptions like:
  - "Handles data"
  - "Main logic"
  - "Helper function"

- Do NOT omit parameter constraints.

- Do NOT describe obvious code behavior.

- Do NOT include undocumented return structures.

- Do NOT mix Markdown and plain-text formats inconsistently.

- Do NOT write one-line minimal docstrings unless function is trivial.

---

--------------------------------------------------------
REJECTION RULE
--------------------------------------------------------

Any generated function without:

- Proper Markdown structured docstring
- Parameter section
- Return structure
- Code-block formatted schemas (when applicable)

is considered incomplete and must be rewritten.