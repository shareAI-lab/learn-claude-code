# Start Session

Initialize your AI development session and begin working on tasks.

---

## Operation Types

Operations in this document are categorized as:

| Marker | Meaning | Executor |
|--------|---------|----------|
| `[AI]` | Bash scripts or file reads executed by AI | You (AI) |
| `[USER]` | Slash commands executed by user | User |

---

## Initialization

### Step 1: Understand Trellis Workflow `[AI]`

First, read the workflow guide to understand the development process:

```bash
cat .trellis/workflow.md  # Development process, conventions, and quick start guide
```

### Step 2: Get Current Status `[AI]`

```bash
python3 ./.trellis/scripts/get_context.py
```

This returns:
- Developer identity
- Git status (branch, uncommitted changes)
- Recent commits
- Active tasks
- Journal file status

### Step 3: Read Project Code-Spec Index `[AI]`

Based on the upcoming task, read appropriate code-spec docs:

**For Frontend Work**:
```bash
cat .trellis/spec/frontend/index.md
```

**For Backend Work**:
```bash
cat .trellis/spec/backend/index.md
```

**For Cross-Layer Features**:
```bash
cat .trellis/spec/guides/index.md
cat .trellis/spec/guides/cross-layer-thinking-guide.md
```

> **Important**: The index files are navigation — they list the actual guideline files (e.g., `error-handling.md`, `conventions.md`, `mock-strategies.md`).
> At this step, just read the indexes to understand what's available.
> When you start actual development, you MUST go back and read the specific guideline files relevant to your task, as listed in the index's Pre-Development Checklist.

### Step 4: Check Active Tasks `[AI]`

```bash
python3 ./.trellis/scripts/task.py list
```

If continuing previous work, review the task file.

### Step 5: Report Ready Status and Ask for Tasks

Output a summary:

```markdown
## Session Initialized

| Item | Status |
|------|--------|
| Developer | {name} |
| Branch | {branch} |
| Uncommitted | {count} file(s) |
| Journal | {file} ({lines}/2000 lines) |
| Active Tasks | {count} |

Ready for your task. What would you like to work on?
```

---

## Task Classification

When user describes a task, classify it:

| Type | Criteria | Workflow |
|------|----------|----------|
| **Question** | User asks about code, architecture, or how something works | Answer directly |
| **Trivial Fix** | Typo fix, comment update, single-line change, < 5 minutes | Direct Edit |
| **Simple Task** | Clear goal, 1-2 files, well-defined scope | Quick confirm → Task Workflow |
| **Complex Task** | Vague goal, multiple files, architectural decisions | **Brainstorm → Task Workflow** |

### Decision Rule

> **If in doubt, use Brainstorm + Task Workflow.**
>
> Task Workflow ensures code-specs are injected to the right context, resulting in higher quality code.
> The overhead is minimal, but the benefit is significant.

> **Subtask Decomposition**: If brainstorm reveals multiple independent work items,
> consider creating subtasks using `--parent` flag or `add-subtask` command.
> See `/trellis:brainstorm` Step 8 for details.

---

## Question / Trivial Fix

For questions or trivial fixes, work directly:

1. Answer question or make the fix
2. If code was changed, remind user to run `/trellis-finish-work`

---

## Simple Task

For simple, well-defined tasks:

1. Quick confirm: "I understand you want to [goal]. Shall I proceed?"
2. If no, clarify and confirm again
3. **If yes: execute ALL steps below without stopping. Do NOT ask for additional confirmation between steps.**
   - Create task directory (Phase 1 Path B, Step 2)
   - Write PRD (Step 3)
   - Research codebase (Phase 2, Step 5)
   - Configure context (Step 6)
   - Activate task (Step 7)
   - Implement (Phase 3, Step 8)
   - Check quality (Step 9)
   - Complete (Step 10)

---

## Complex Task - Brainstorm First

For complex or vague tasks, **automatically start the brainstorm process** — do NOT skip directly to implementation. Use `/trellis-brainstorm`.

Summary:

1. **Acknowledge and classify** - State your understanding
2. **Create task directory** - Track evolving requirements in `prd.md`
3. **Ask questions one at a time** - Update PRD after each answer
4. **Propose approaches** - For architectural decisions
5. **Confirm final requirements** - Get explicit approval
6. **Proceed to Task Workflow** - With clear requirements in PRD

---

## Task Workflow (Development Tasks)

**Why this workflow?**
- Run a dedicated research pass before coding
- Configure specs in jsonl context files
- Implement using injected context
- Verify with a separate check pass
- Result: Code that follows project conventions automatically

### Overview: Two Entry Points

```
From Brainstorm (Complex Task):
  PRD confirmed → Research → Configure Context → Activate → Implement → Check → Complete

From Simple Task:
  Confirm → Create Task → Write PRD → Research → Configure Context → Activate → Implement → Check → Complete
```

**Key principle: Research happens AFTER requirements are clear (PRD exists).**

---

### Phase 1: Establish Requirements

#### Path A: From Brainstorm (skip to Phase 2)

PRD and task directory already exist from brainstorm. Skip directly to Phase 2.

#### Path B: From Simple Task

**Step 1: Confirm Understanding** `[AI]`

Quick confirm:
- What is the goal?
- What type of development? (frontend / backend / fullstack)
- Any specific requirements or constraints?

If unclear, ask clarifying questions.

**Step 2: Create Task Directory** `[AI]`

```bash
TASK_DIR=$(python3 ./.trellis/scripts/task.py create "<title>" --slug <name>)
```

**Step 3: Write PRD** `[AI]`

Create `prd.md` in the task directory with:

```markdown
# <Task Title>

## Goal
<What we're trying to achieve>

## Requirements
- <Requirement 1>
- <Requirement 2>

## Acceptance Criteria
- [ ] <Criterion 1>
- [ ] <Criterion 2>

## Technical Notes
<Any technical decisions or constraints>
```

---

### Phase 2: Prepare for Implementation (shared)

> Both paths converge here. PRD and task directory must exist before proceeding.

**Step 4: Code-Spec Depth Check** `[AI]`

If the task touches infra or cross-layer contracts, do not start implementation until code-spec depth is defined.

Trigger this requirement when the change includes any of:
- New or changed command/API signatures
- Database schema or migration changes
- Infra integrations (storage, queue, cache, secrets, env contracts)
- Cross-layer payload transformations

Must-have before proceeding:
- [ ] Target code-spec files to update are identified
- [ ] Concrete contract is defined (signature, fields, env keys)
- [ ] Validation and error matrix is defined
- [ ] At least one Good/Base/Bad case is defined

**Step 5: Research the Codebase** `[AI]`

Based on the confirmed PRD, run a focused research pass and produce:

1. Relevant spec files in `.trellis/spec/`
2. Existing code patterns to follow (2-3 examples)
3. Files that will likely need modification

Use this output format:

```markdown
## Relevant Specs
- <path>: <why it's relevant>

## Code Patterns Found
- <pattern>: <example file path>

## Files to Modify
- <path>: <what change>
```

**Step 6: Configure Context** `[AI]`

Initialize default context:

```bash
python3 ./.trellis/scripts/task.py init-context "$TASK_DIR" <type>
# type: backend | frontend | fullstack
```

Add specs found in your research pass:

```bash
# For each relevant spec and code pattern:
python3 ./.trellis/scripts/task.py add-context "$TASK_DIR" implement "<path>" "<reason>"
python3 ./.trellis/scripts/task.py add-context "$TASK_DIR" check "<path>" "<reason>"
```

**Step 7: Activate Task** `[AI]`

```bash
python3 ./.trellis/scripts/task.py start "$TASK_DIR"
```

This sets `.current-task` so hooks can inject context.

---

### Phase 3: Execute (shared)

**Step 8: Implement** `[AI]`

Implement the task described in `prd.md`.

- Follow all specs injected into implement context
- Keep changes scoped to requirements
- Run lint and typecheck before finishing

**Step 9: Check Quality** `[AI]`

Run a quality pass against check context:

- Review all code changes against the specs
- Fix issues directly
- Ensure lint and typecheck pass

**Step 10: Complete** `[AI]`

1. Verify lint and typecheck pass
2. Report what was implemented
3. Remind user to:
   - Test the changes
   - Commit when ready
   - Run `/trellis-record-session` to record this session

---

## User Available Commands `[USER]`

The following slash commands are for users (not AI):

| Command | Description |
|---------|-------------|
| `/trellis-start` | Start development session (this command) |
| `/trellis-brainstorm` | Clarify vague requirements before implementation |
| `/trellis-before-frontend-dev` | Read frontend guidelines |
| `/trellis-before-backend-dev` | Read backend guidelines |
| `/trellis-check-frontend` | Check frontend code |
| `/trellis-check-backend` | Check backend code |
| `/trellis-check-cross-layer` | Cross-layer verification |
| `/trellis-finish-work` | Pre-commit checklist |
| `/trellis-record-session` | Record session progress |

---

## AI Executed Scripts `[AI]`

| Script | Purpose |
|--------|---------|
| `python3 ./.trellis/scripts/task.py create "<title>" [--slug <name>]` | Create task directory |
| `python3 ./.trellis/scripts/task.py list` | List active tasks |
| `python3 ./.trellis/scripts/task.py archive <name>` | Archive task |
| `python3 ./.trellis/scripts/get_context.py` | Get session context |

---

## Platform Detection

Trellis auto-detects your platform based on config directories. For Cursor users, ensure detection works correctly:

| Condition | Detected Platform |
|-----------|-------------------|
| Only `.cursor/` exists | `cursor` ✅ |
| Both `.cursor/` and `.claude/` exist | `claude` (default) |

If auto-detection fails, set manually:

```bash
export TRELLIS_PLATFORM=cursor
```

Or prefix commands:

```bash
TRELLIS_PLATFORM=cursor python3 ./.trellis/scripts/task.py list
```

---

## Session End Reminder

**IMPORTANT**: When a task or session is completed, remind the user:

> Before ending this session, please run `/trellis-record-session` to record what we accomplished.
