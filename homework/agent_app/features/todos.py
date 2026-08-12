import ast
import json

from homework.agent_app.runtime import SessionState


def register_todo_tools(registry, schemas: dict, handlers: dict) -> None:
    """Register the session todo tool."""
    registry.register(schemas["todo_write"], handlers.get("todo_write"))


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
