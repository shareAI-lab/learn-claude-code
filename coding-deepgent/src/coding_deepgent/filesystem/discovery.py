from __future__ import annotations

from langchain.tools import ToolRuntime, tool

from .schemas import GlobInput, GrepInput
from .service import glob_workspace_paths, grep_workspace_files, runtime_from_context


@tool("glob", args_schema=GlobInput)
def glob_search(pattern: str, runtime: ToolRuntime, limit: int = 200) -> str:
    """List workspace paths that match a glob pattern."""

    return glob_workspace_paths(runtime_from_context(runtime.context), pattern, limit=limit)


@tool("grep", args_schema=GrepInput)
def grep_search(
    pattern: str,
    runtime: ToolRuntime,
    include: str = "**/*",
    limit: int = 200,
) -> str:
    """Search workspace text files using a regular expression."""

    return grep_workspace_files(
        runtime_from_context(runtime.context),
        pattern,
        include=include,
        limit=limit,
    )
