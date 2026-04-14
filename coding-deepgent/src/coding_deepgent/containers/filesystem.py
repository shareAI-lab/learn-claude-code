from __future__ import annotations

from dependency_injector import containers, providers

from coding_deepgent.filesystem import bash, edit_file, read_file, write_file


def _tool_list(*tools: object) -> list[object]:
    return list(tools)


class FilesystemContainer(containers.DeclarativeContainer):
    bash = providers.Object(bash)
    read_file = providers.Object(read_file)
    write_file = providers.Object(write_file)
    edit_file = providers.Object(edit_file)
    tools = providers.Callable(_tool_list, bash, read_file, write_file, edit_file)
