---
name: commit
description: Create a git commit using Conventional Commits format (commitizen)
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*), Bash(git diff:*), Bash(git log:*)
metadata:
  internal: true
---

## Context

- Current git status: !`git status`
- Current git diff (staged and unstaged changes): !`git diff HEAD 2>/dev/null || git diff --cached`
- Current branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10 2>/dev/null || echo 'No commits yet'`

## Your task

Based on the above changes, create a single git commit following the Conventional Commits format used by commitizen:

```
<type>(<scope>): <subject>
```

Types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `style`, `ci`, `build`, `perf`.

Scope is optional. Subject must be lowercase, imperative, no period at the end.

Stage the relevant files and create the commit in a single message. Do NOT include "Co-Authored-By" or any trailer in the commit message. Do not send any other text or messages besides the tool calls.
