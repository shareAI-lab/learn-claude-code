description = "Capture knowledge into spec documents after learning something valuable"

prompt = """
# Update Spec - Capture Knowledge into Specifications

When you learn something valuable (from debugging, implementing, or discussion), use this command to update the relevant spec documents.

**Timing**: After completing a task, fixing a bug, or discovering a new pattern

---

## When to Update Specs

| Trigger | Example | Target Spec |
|---------|---------|-------------|
| **Implemented a feature** | Added template download with giget | Relevant `backend/` or `frontend/` file |
| **Made a design decision** | Used type field + mapping table for extensibility | Relevant spec + "Design Decisions" section |
| **Fixed a bug** | Found a subtle issue with error handling | `backend/error-handling.md` |
| **Discovered a pattern** | Found a better way to structure code | Relevant `backend/` or `frontend/` file |
| **Hit a gotcha** | Learned that X must be done before Y | Relevant spec + "Common Mistakes" section |
| **Established a convention** | Team agreed on naming pattern | `quality-guidelines.md` |
| **New thinking trigger** | "Don't forget to check X before doing Y" | `guides/*.md` (as a checklist item, not detailed rules) |

---

## Spec Structure Overview

```
.trellis/spec/
+-- backend/           # Backend coding standards
|   +-- index.md       # Overview and links
|   +-- *.md           # Topic-specific guidelines
+-- frontend/          # Frontend coding standards
|   +-- index.md       # Overview and links
|   +-- *.md           # Topic-specific guidelines
+-- guides/            # Thinking checklists (NOT coding specs!)
    +-- index.md       # Guide index
    +-- *.md           # Topic-specific guides
```

### CRITICAL: Spec vs Guide - Know the Difference

| Type | Location | Purpose | Content Style |
|------|----------|---------|---------------|
| **Spec** | `backend/*.md`, `frontend/*.md` | Tell AI "how to write code" | Detailed rules, code examples, forbidden patterns |
| **Guide** | `guides/*.md` | Help AI "what to think about" | Checklists, questions, pointers to specs |

**Decision Rule**: Ask yourself:

- "This is **how to write** the code" -> Put in `backend/` or `frontend/`
- "This is **what to consider** before writing" -> Put in `guides/`

---

## Update Process

### Step 1: Identify What You Learned

Answer these questions:

1. **What did you learn?** (Be specific)
2. **Why is it important?** (What problem does it prevent?)
3. **Where does it belong?** (Which spec file?)

### Step 2: Classify the Update Type

| Type | Description | Action |
|------|-------------|--------|
| **Design Decision** | Why we chose approach X over Y | Add to "Design Decisions" section |
| **Project Convention** | How we do X in this project | Add to relevant section with examples |
| **New Pattern** | A reusable approach discovered | Add to "Patterns" section |
| **Forbidden Pattern** | Something that causes problems | Add to "Anti-patterns" or "Don't" section |
| **Common Mistake** | Easy-to-make error | Add to "Common Mistakes" section |
| **Convention** | Agreed-upon standard | Add to relevant section |
| **Gotcha** | Non-obvious behavior | Add warning callout |

### Step 3: Read the Target Spec

Before editing, read the current spec to:
- Understand existing structure
- Avoid duplicating content
- Find the right section for your update

```bash
cat .trellis/spec/<category>/<file>.md
```

### Step 4: Make the Update

Follow these principles:

1. **Be Specific**: Include concrete examples, not just abstract rules
2. **Explain Why**: State the problem this prevents
3. **Show Code**: Add code snippets for patterns
4. **Keep it Short**: One concept per section

### Step 5: Update the Index (if needed)

If you added a new section or the spec status changed, update the category's `index.md`.

---

## Quality Checklist

Before finishing your spec update:

- [ ] Is the content specific and actionable?
- [ ] Did you include a code example?
- [ ] Did you explain WHY, not just WHAT?
- [ ] Is it in the right spec file?
- [ ] Does it duplicate existing content?
- [ ] Would a new team member understand it?

---

## Relationship to Other Commands

- `/trellis:break-loop` - Analyzes bugs deeply, often reveals spec updates needed
- `/trellis:update-spec` - Actually makes the updates (this command)
- `/trellis:finish-work` - Reminds you to check if specs need updates

---

## Core Philosophy

> **Specs are living documents. Every debugging session, every "aha moment" is an opportunity to make the spec better.**

The goal is **institutional memory**:
- What one person learns, everyone benefits from
- What AI learns in one session, persists to future sessions
- Mistakes become documented guardrails
"""
