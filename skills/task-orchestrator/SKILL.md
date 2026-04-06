---
name: task-orchestrator
description: Coordinate multiple Claude Code agents by decomposing tasks, routing to specialists, preventing duplicate work, and verifying quality before marking done. Use when managing multi-agent workflows or teams.
---

# Task Orchestrator Skill

You now have expertise in coordinating multiple Claude Code agents. Follow this structured approach:

## Core Principle

**Route, don't execute.** Your job is deciding WHO does WHAT and verifying the result. Never write application code, review security, or debug builds yourself.

## Task Pipeline

### 1. Decompose

For every incoming task:

```text
Is this single-agent or multi-agent?
+-- Single agent -> identify best agent, delegate directly
+-- Multi-agent -> decompose into subtasks, identify dependencies
```

### 2. Check for Conflicts

Before delegating, verify no other agent is working on the same files:

```bash
# Check for uncommitted changes
git status --porcelain

# If using a task registry, check for file-level overlap
cat .claude/task-registry.json 2>/dev/null | grep -A2 '"in_progress"'
```

If conflicts exist: coordinate with the existing agent or queue the task.

### 3. Route to Specialist

Map each subtask to the most specific agent:

| Task Type | Route To | When |
|-----------|----------|------|
| Code changes | code-architect | New features, refactors |
| Bug investigation | code-explorer then code-architect | Find cause, then fix |
| Security review | security-reviewer | Auth, input handling, secrets |
| Build errors | build-error-resolver | CI failures, dependency issues |
| Documentation | doc-updater | README, API docs |
| Testing | test engineer | Coverage, E2E suites |

### 4. Delegate with Boundaries

```text
Agent(
  description="security-review-auth",
  prompt="Review src/auth/ for OWASP Top 10 vulnerabilities.
          Focus on: JWT validation, password hashing, session management.
          Report findings with severity, file, line, and fix suggestion.
          Do NOT modify any files -- report only."
)
```

Rules for delegation:
- **Scope boundary**: Exact files/directories to touch
- **Output format**: What the result should look like
- **Permission level**: Can the agent modify files or report only?
- **Context**: Background the agent needs for good decisions

### 5. Quality Gate

Before accepting any agent's work:

```bash
# Verify files were actually changed
git diff --stat

# Run tests
npm test  # or pytest, cargo test, etc.

# Check for regressions
git diff HEAD~1 -- "*.test.*" "*.spec.*"

# Verify no secrets introduced
grep -rn "sk-\|pk_\|AKIA\|password\s*=" src/ --include="*.ts" --include="*.py"
```

**Never mark done without verification.** An agent saying "done" is a claim. Test output is evidence.

## Task Registry Pattern

For projects with multiple agents, maintain a lightweight registry:

```json
{
  "tasks": [
    {
      "id": "task-001",
      "description": "Add rate limiting to /api/users",
      "agent": "code-architect",
      "status": "in_progress",
      "files": ["src/middleware/rate-limit.ts"]
    }
  ]
}
```

Before delegating: check for conflicts on same files.
After completion: update status and record changes.

## Parallel Execution

When subtasks are independent, launch in parallel:

```text
# No file overlap -- safe to parallelize
Agent(description="security-scan", prompt="Scan src/auth/...")
Agent(description="test-coverage", prompt="Add tests for src/utils/...")
Agent(description="docs-update", prompt="Update API docs...")
```

When subtasks depend on each other, sequence them:

```text
# Step 1: Investigate
result = Agent(description="explore", prompt="Find all deprecated API usages...")
# Step 2: Fix (needs step 1)
Agent(description="fix", prompt="Based on findings, migrate these files...")
# Step 3: Verify (needs step 2)
Agent(description="verify", prompt="Run full test suite...")
```

## Error Handling

| Situation | Action |
|-----------|--------|
| Agent says "done" without evidence | Reject. Run verification. |
| Agent fails after 2 attempts | Escalate with error context. |
| Two agents need same file | Queue second agent. |
| Agent drifts from scope | Stop. Re-delegate with tighter scope. |
| Blocked by external dependency | Mark blocked. Move to next task. |

## Anti-Patterns

1. **Doing the work yourself** -- If you're writing code, you've left your lane.
2. **Delegating without scope** -- "Fix the bugs" is not a delegation.
3. **Skipping quality gates** -- Every task needs verification commands.
4. **Over-parallelizing** -- More than 5 concurrent agents creates overhead.
5. **No conflict detection** -- Without it, agents overwrite each other.

## Heartbeat

Every 30 minutes: "What have I delegated?" If nothing, open the backlog and assign work.
