---
name: edit_file
description: Replace text in file.
parameters:
  path:
    type: string
    description: Relative path to the file
  old_text:
    type: string
    description: Exact text to find (must match precisely)
  new_text:
    type: string
    description: Replacement text
required:
  - path
  - old_text
  - new_text
---

# Edit File Tool

Replace exact text in a file (surgical edit).

## Safety Features

- Path traversal protection
- Only replaces first occurrence (predictable behavior)
- Clear error if text not found

## Usage Examples

```
# Fix a typo
path: "README.md"
old_text: "teh"
new_text: "the"

# Update version
path: "package.json"
old_text: '"version": "1.0.0"'
new_text: '"version": "1.0.1"'
```

## Implementation Notes

Uses exact string matching (not regex).
Only replaces the first occurrence for safety.
Returns error if `old_text` is not found in file.
