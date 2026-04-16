---
name: record-session
description: "Record work progress after validated code has been committed"
---

[!] **Prerequisite**: This skill should only be used AFTER the work has been
validated and committed. AI may now create the code/docs commit autonomously
after the required checks pass.

Commit safety:
- Do not amend commits unless explicitly requested.
- Do not use destructive git commands.
- Do not commit unrelated user changes.
- If validation failed or was not run, do not record the session as complete.
- The scripts below handle their own commits for `.trellis/` metadata after the
  code/docs commit exists.

---

## Record Work Progress

### Step 1: Get Context & Check Tasks

```bash
python3 ./.trellis/scripts/get_context.py --mode record
```

[!] Archive tasks whose work is **actually done** — judge by work status, not the `status` field in task.json:
- Code committed? → Archive it (don't wait for PR)
- All acceptance criteria met? → Archive it
- Don't skip archiving just because `status` still says `planning` or `in_progress`

```bash
python3 ./.trellis/scripts/task.py archive <task-name>
```

### Step 2: One-Click Add Session

```bash
# Method 1: Simple parameters
python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "hash1,hash2" \
  --summary "Brief summary of what was done"

# Method 2: Pass detailed content via stdin
cat << 'EOF' | python3 ./.trellis/scripts/add_session.py --title "Title" --commit "hash"
| Feature | Description |
|---------|-------------|
| New API | Added user authentication endpoint |
| Frontend | Updated login form |

**Updated Files**:
- `packages/api/modules/auth/router.ts`
- `apps/web/modules/auth/components/login-form.tsx`
EOF
```

**Auto-completes**:
- [OK] Appends session to journal-N.md
- [OK] Auto-detects line count, creates new file if >2000 lines
- [OK] Updates index.md (Total Sessions +1, Last Active, line stats, history)
- [OK] Auto-commits .trellis/workspace and .trellis/tasks changes

---

## Script Command Reference

| Command | Purpose |
|---------|---------|
| `python3 ./.trellis/scripts/get_context.py --mode record` | Get context for record-session |
| `python3 ./.trellis/scripts/add_session.py --title "..." --commit "..."` | **One-click add session (recommended)** |
| `python3 ./.trellis/scripts/task.py archive <name>` | Archive completed task (auto-commits) |
| `python3 ./.trellis/scripts/task.py list` | List active tasks |
