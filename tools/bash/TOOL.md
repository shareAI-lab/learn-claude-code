---
name: bash
description: Run shell command.
parameters:
  command:
    type: string
    description: The shell command to execute
required:
  - command
---

# Bash Tool

Execute shell commands in the workspace directory.

## Safety Features

- Blocks dangerous commands: `rm -rf /`, `sudo`, `shutdown`
- 60 second timeout
- Output truncated to 50KB

## Usage Examples

```
# List files
ls -la

# Search for patterns
grep -r "TODO" .

# Run tests
python -m pytest
```

## Implementation Notes

Commands run with `shell=True` in the workspace directory.
Both stdout and stderr are captured and returned.
