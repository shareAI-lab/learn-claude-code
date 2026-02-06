---
name: TodoWrite
description: Update task list for planning and tracking progress.
parameters:
  items:
    type: array
    description: Complete list of tasks (replaces existing)
    items:
      type: object
      properties:
        content:
          type: string
          description: Task description
        status:
          type: string
          enum: [pending, in_progress, completed]
          description: Task status
        activeForm:
          type: string
          description: Present tense action, e.g. 'Reading files'
      required:
        - content
        - status
        - activeForm
required:
  - items
---

# TodoWrite Tool

Manage a structured task list for planning and tracking progress.

## Constraints

- Maximum 20 items (prevents infinite lists)
- Only ONE task can be `in_progress` at a time (forces focus)
- All fields required: content, status, activeForm

## Status Values

| Status | Meaning | Display |
|--------|---------|---------|
| pending | Not started | `[ ]` |
| in_progress | Currently working | `[>]` |
| completed | Done | `[x]` |

## Usage Examples

```json
{
  "items": [
    {"content": "Read config files", "status": "completed", "activeForm": "Reading config"},
    {"content": "Update database schema", "status": "in_progress", "activeForm": "Updating schema"},
    {"content": "Write tests", "status": "pending", "activeForm": "Writing tests"}
  ]
}
```

## The activeForm Field

Present tense description shown during execution:
- content: "Add unit tests" (what to do)
- activeForm: "Adding unit tests..." (what's happening now)
