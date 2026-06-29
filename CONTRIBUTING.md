# Contributing to LectureLens 🚀

We implement a rigorous, **Spec-Driven Development** architecture loop. Please adhere to these development patterns:

## 🛠️ Step-by-Step Commit Rules
1. All core changes must begin with a Feature Spec file added to the `specs/` directory layout.
2. We follow **Conventional Commits**:
   - `feat: language model schema validation execution layer`
   - `fix: resolved circular package imports inside runtime matrix`
3. Before submitting a PR, verify local lint tracking executes accurately:
   ```bash
   ruff check .
   mypy app/