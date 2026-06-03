# Agent Rules

## Before Pushing

- Always run checks after the final merge or rebase, not only before it.
- For backend checks, run commands from `backend/`; paths like `services/`, `api/`, `core/`, and `tests/` are relative to that directory.
- Before every push that changes backend code, run:
  - `ruff check .`
  - `mypy services/ api/ core/ --ignore-missing-imports --python-version 3.12`
  - relevant focused pytest tests for the changed area
- If the user asks for `ruff check .` on this project, treat `backend/` as the working directory unless they explicitly request the repository root.
- After resolving conflicts or amending a merge commit, repeat the same checks on the final branch state before pushing.
- Check `git status --short --branch` before staging and before pushing. Do not stage unrelated untracked files such as generated PDFs, local notes, or temporary artifacts unless the user explicitly asks for them.
- If pushing both `andrey` and `main`, first push `andrey`, verify `origin/main` is an ancestor of the final branch state, then update `main`.
