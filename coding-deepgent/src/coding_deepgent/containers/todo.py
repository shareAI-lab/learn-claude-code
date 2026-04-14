from __future__ import annotations

from dependency_injector import containers, providers

from coding_deepgent.middleware import PlanContextMiddleware
from coding_deepgent.todo.tools import todo_write


def _singleton_list(item: object) -> list[object]:
    return [item]


class TodoContainer(containers.DeclarativeContainer):
    tool = providers.Object(todo_write)
    tools = providers.Callable(_singleton_list, tool)
    middleware = providers.Factory(PlanContextMiddleware)
    middleware_list = providers.Callable(_singleton_list, middleware)
