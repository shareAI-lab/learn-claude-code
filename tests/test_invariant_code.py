import pytest
import subprocess
import sys
import os

# Add the parent directory to sys.path to import the actual module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from s02_tool_use.code import run_bash


@pytest.mark.parametrize("payload", [
    # Exact exploit case: bypass deny list with shell metacharacters
    "rm -rf /tmp/test; echo 'exploited'",
    # Boundary case: command substitution to hide dangerous command
    "$(echo 'sudo') id",
    # Valid input: should pass through
    "echo 'safe command'",
    # Encoding trick: using backticks instead of $()
    "`echo 'rm -rf /'`",
    # Command variant: using dangerous command with spaces
    "rm   -rf   /tmp/test",
])
def test_run_bash_blocks_dangerous_commands_under_adversarial_input(payload):
    """Invariant: The run_bash function must never execute dangerous shell commands,
       regardless of shell metacharacters, encoding tricks, or command variants."""
    
    result = run_bash(payload)
    
    # The security property: if the command contains dangerous patterns,
    # the function must return the error message or otherwise prevent execution
    dangerous_patterns = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    
    # Check if any dangerous pattern appears in the payload (basic detection)
    has_dangerous = any(pattern in payload.replace(" ", "") for pattern in dangerous_patterns)
    
    if has_dangerous:
        # For dangerous commands, we expect either an error message or safe output
        # We don't require exact match, but we must ensure no dangerous execution occurred
        assert "exploited" not in result, f"Dangerous command executed: {payload}"
        assert "uid=" not in result, f"Privilege escalation occurred: {payload}"
    else:
        # For safe commands, we expect normal execution
        assert "Error: Dangerous command blocked" not in result, f"Safe command blocked: {payload}"