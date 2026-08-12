import ast
import json
from collections.abc import Mapping

from homework.agent_app.runtime import SessionState


TODO_TOOL_SCHEMA = {
    "name": "todo_write",
    "description": "Create and manage a task list for your current coding session.",
    "input_schema": {"type": "object", "properties": {"todos": {"type": "array", "items": {"type": "object", "properties": {"content": {"type": "string"}, "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}}, "required": ["content", "status"]}}}, "required": ["todos"]},
}


def register_todo_tools(registry, session) -> None:
    """Register the session todo tool."""
    if isinstance(session, Mapping):
        handler = session["todo_write"]
    else:
        handler = lambda todos: run_todo_write(session, todos)
    registry.register(TODO_TOOL_SCHEMA, handler)


def _normalize_todos(todos):
    if isinstance(todos, str):
        try:
            todos = json.loads(todos)
        except json.JSONDecodeError:
            try:
                todos = ast.literal_eval(todos)
            except (SyntaxError, ValueError):
                return None, "Error: todos must be a list or JSON array string"
    if not isinstance(todos, list):
        return None, "Error: todos must be a list"
    for index, todo in enumerate(todos):
        if not isinstance(todo, dict):
            return None, f"Error: todos[{index}] must be an object"
        if "content" not in todo or "status" not in todo:
            return None, f"Error: todos[{index}] missing 'content' or 'status'"
        if todo["status"] not in ("pending", "in_progress", "completed"):
            return None, (
                f"Error: todos[{index}] has invalid status '{todo['status']}'"
            )
    return todos, None


def format_current_todos(session: SessionState) -> str:
    if not session.todos:
        return ""
    return "\n".join(
        f"- [{todo['status']}] {todo['content']}" for todo in session.todos
    )


def run_todo_write(session: SessionState, todos: list) -> str:
    todos, error = _normalize_todos(todos)
    if error:
        return error
    session.todos = todos
    lines = ["\n\033[33m## Current Tasks\033[0m"]
    for todo in session.todos:
        icon = {
            "pending": " ",
            "in_progress": "\033[36m▸\033[0m",
            "completed": "\033[32m✓\033[0m",
        }[todo["status"]]
        lines.append(f"  [{icon}] {todo['content']}")
    print("\n".join(lines))
    return f"Updated {len(session.todos)} tasks"
