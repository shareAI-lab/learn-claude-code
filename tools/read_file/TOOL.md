---
name: read_file
description: Read file contents.
parameters:
  path:
    type: string
    description: Relative path to the file
  limit:
    type: integer
    description: Maximum lines to read (optional)
required:
  - path
---

# Read File Tool

Read the contents of a file in the workspace.

## Safety Features

- Path traversal protection (cannot escape workspace)
- Output truncated to 50KB

## Usage Examples

```
# Read entire file
path: "src/main.py"

# Read first 50 lines
path: "large_file.log"
limit: 50
```

## Implementation Notes

Uses `safe_path()` to prevent directory traversal attacks.
Returns file contents as UTF-8 text.
