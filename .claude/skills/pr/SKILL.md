---
name: pr
description: Create a GitHub pull request from the current branch with a verbose, detailed description. Use this skill whenever the user wants to create a PR, open a pull request, send changes for review, or merge a branch. Also trigger when the user says things like "push this to main", "send a PR", or "create a pull request".
allowed-tools: Bash(git log:*), Bash(git diff:*), Bash(git branch:*), Bash(git remote:*), Bash(git push:*), Bash(git rev-parse:*), mcp__github__create_pull_request
---

## Context

- Current branch: !`git branch --show-current`
- Remote URL: !`git remote get-url origin`
- Recent commits: !`git log --oneline -20`

## Arguments

The user may pass an optional base branch as an argument (e.g., `/pr develop`). If no argument is given, default to `master`.

## Your task

Create a GitHub pull request from the current branch to the base branch. Follow these steps exactly:

### 1. Gather information

Run these commands to understand the full scope of changes:

- `git remote get-url origin` — extract the owner and repo name (e.g., from `git@github.com:owner/repo.git` or `https://github.com/owner/repo.git`)
- `git log <base>..HEAD --oneline` — list all commits that will be in the PR
- `git diff <base>..HEAD --stat` — get a file-level summary of what changed
- `git diff <base>..HEAD` — read the actual diff to understand the substance of changes

Also push the current branch to the remote if it hasn't been pushed yet:
- `git push -u origin <current-branch>`

### 2. Write the PR title

Keep it under 70 characters. It should capture the overall theme of the changes. Use lowercase, imperative mood. If there's a single dominant change, name it. If there are multiple themes, summarize the batch (e.g., "async OCR pipeline, domain refactor, and CI fixes").

### 3. Write the PR body

The body must be **verbose and detailed**. The goal is that a reviewer reading only the PR description understands every meaningful change without opening the diff.

Structure the body like this:

```
## Summary

A 2-3 sentence high-level overview of what this PR accomplishes and why.

## Changes

Group commits by category. For each group, explain what changed and provide context about why. Use sub-bullets for individual commits or notable details within a group.

Categories to consider (use only the ones that apply):
- **Features** — new user-facing functionality
- **Bug Fixes** — corrections to existing behavior  
- **Refactoring** — structural improvements without behavior changes
- **Infrastructure / CI** — build, deploy, CI/CD pipeline changes
- **Documentation** — docs, diagrams, ADRs
- **Tests** — new or updated tests
- **Dependencies** — added, removed, or updated packages

For each change, describe:
- What was changed (be specific — name files, modules, patterns)
- Why it was changed (motivation, problem it solves, context)
- Any notable implementation details a reviewer should know

## Breaking Changes

Only include this section if there are breaking changes. List them explicitly.
```

### 4. Rules

- Do NOT include a "Test plan" section.
- Do NOT include any "Co-Authored-By", "Contributed by", "Generated with", or any other footer/trailer.
- Do NOT include emoji in the PR title or body.
- The description should be thorough enough that someone unfamiliar with the codebase can understand the scope and intent of every change.
- Use the `mcp__github__create_pull_request` tool to create the PR. Pass `owner`, `repo`, `title`, `head` (current branch), `base` (target branch), and `body`.

### 5. After creating the PR

Print the PR URL so the user can access it directly.
