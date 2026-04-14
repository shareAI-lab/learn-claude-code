from __future__ import annotations

from langchain.tools import ToolRuntime, tool

from .service import (
    edit_workspace_file,
    read_workspace_file,
    runtime_from_context,
    run_bash,
    write_workspace_file,
)
from .schemas import BashInput, EditFileInput, ReadFileInput, WriteFileInput


@tool("bash", args_schema=BashInput)
def bash(command: str, runtime: ToolRuntime) -> str:
    """Run a shell command inside the current workspace."""

    return run_bash(runtime_from_context(runtime.context), command)


@tool("read_file", args_schema=ReadFileInput)
def read_file(path: str, runtime: ToolRuntime, limit: int | None = None) -> str:
    """Read a workspace file, optionally limiting returned lines."""

    return read_workspace_file(runtime_from_context(runtime.context), path, limit)


@tool("write_file", args_schema=WriteFileInput)
def write_file(path: str, content: str, runtime: ToolRuntime) -> str:
    """Write content to a workspace file."""

    return write_workspace_file(runtime_from_context(runtime.context), path, content)


@tool("edit_file", args_schema=EditFileInput)
def edit_file(path: str, old_text: str, new_text: str, runtime: ToolRuntime) -> str:
    """Replace one exact text fragment in a workspace file."""

    return edit_workspace_file(
        runtime_from_context(runtime.context),
        path,
        old_text,
        new_text,
    )
