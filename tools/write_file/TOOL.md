---
name: write_file
description: Write content to file.
parameters:
  path:
    type: string
    description: Relative path for the file
  content:
    type: string
    description: Content to write
required:
  - path
  - content
---

# Write File Tool

Write content to a file, creating parent directories if needed.

## Safety Features

- Path traversal protection (cannot escape workspace)
- Creates parent directories automatically

## Usage Examples

```
# Create new file
path: "src/utils.py"
content: "def hello():\n    print('Hello')"

# Overwrite existing file
path: "config.json"
content: '{"debug": true}'
```

## Implementation Notes

Uses `safe_path()` to prevent directory traversal attacks.
Creates parent directories with `mkdir(parents=True)`.
Returns confirmation with byte count.
