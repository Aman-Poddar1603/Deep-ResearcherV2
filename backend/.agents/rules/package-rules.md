---
trigger: always_on
---

# =====================================================
# DEEP RESEARCHER — PACKAGE & EXECUTION SAFETY RULES
# =====================================================

The agent MUST follow strict dependency analysis,
minimal installation policy, and execution restrictions.

--------------------------------------------------------
1. PACKAGE UNDERSTANDING BEFORE IMPLEMENTATION
--------------------------------------------------------

Before using any external library or package, the agent MUST:

- Understand the core purpose of the package.
- Identify:
    • Primary use cases
    • Main API structure
    • Dependencies introduced
    • Runtime requirements
    • Compatibility with project architecture.

- Evaluate whether:
    • Built-in Python functionality can solve the problem.
    • Existing project dependencies already provide similar features.
    • The task can be implemented with less complexity.

- Explain internally (reasoning) why the package is needed
  before using it.

DO NOT implement code using a package that has not been
clearly analyzed.

--------------------------------------------------------
2. MINIMAL DEPENDENCY POLICY (ANTI-BLOAT)
--------------------------------------------------------

The agent MUST:

- Prefer standard library solutions whenever possible.
- Avoid installing new dependencies unless REQUIRED.
- Avoid heavy frameworks for small tasks.
- Avoid overlapping libraries with similar functionality.
- Avoid experimental or unstable packages unless explicitly allowed.

Forbidden behaviors:

- Adding dependencies "just in case".
- Adding multiple libraries solving the same problem.
- Installing packages without clear justification.

--------------------------------------------------------
3. NO AUTOMATIC APPLICATION EXECUTION
--------------------------------------------------------

The agent MUST NEVER:

- Start servers
- Run applications
- Execute background processes
- Launch dev environments
- Run scripts automatically

UNLESS explicit user permission is provided.

All execution steps must be described but NOT performed.

--------------------------------------------------------
4. LIMITED COMMAND EXECUTION POLICY
--------------------------------------------------------

Allowed actions:

- Suggest commands.
- Generate scripts.
- Provide command examples.

NOT allowed without explicit approval:

- Running shell commands.
- Installing packages.
- Executing migrations.
- Starting services.
- Modifying environment configuration.

--------------------------------------------------------
5. SAFE INSTALLATION GUIDELINES (UV ENVIRONMENT)
--------------------------------------------------------

If suggesting dependencies:

- Provide minimal install commands.
- Use uv-compatible installation format.
- Prefer lightweight and maintained packages.
- Explain WHY the dependency is necessary.

--------------------------------------------------------
6. REJECTION RULE
--------------------------------------------------------

Any solution that:

- Adds unnecessary dependencies
- Executes code automatically
- Assumes permission to run processes

must be rejected and rewritten.