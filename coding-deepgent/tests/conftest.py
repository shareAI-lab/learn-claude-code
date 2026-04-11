from __future__ import annotations

import os
import socket
import sys
from pathlib import Path
from typing import Any

PROVIDER_ENV_VARS = (
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
)
NETWORK_BLOCK_MESSAGE = (
    "Network access is disabled during automated tests. "
    "Stub the provider client instead of making live calls."
)
ORIGINAL_SOCKET_FUNCS: dict[str, Any] = {}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def _block_network(*args: Any, **kwargs: Any) -> None:
    raise AssertionError(NETWORK_BLOCK_MESSAGE)


def _block_socket_connect(self: socket.socket, *args: Any, **kwargs: Any) -> None:
    raise AssertionError(NETWORK_BLOCK_MESSAGE)


def pytest_configure(config: Any) -> None:
    del config

    for env_name in PROVIDER_ENV_VARS:
        os.environ.pop(env_name, None)

    ORIGINAL_SOCKET_FUNCS["create_connection"] = socket.create_connection
    ORIGINAL_SOCKET_FUNCS["getaddrinfo"] = socket.getaddrinfo
    ORIGINAL_SOCKET_FUNCS["connect"] = socket.socket.connect
    ORIGINAL_SOCKET_FUNCS["connect_ex"] = socket.socket.connect_ex

    socket.create_connection = _block_network
    socket.getaddrinfo = _block_network
    socket.socket.connect = _block_socket_connect
    socket.socket.connect_ex = _block_socket_connect


def pytest_unconfigure(config: Any) -> None:
    del config

    create_connection = ORIGINAL_SOCKET_FUNCS.get("create_connection")
    getaddrinfo = ORIGINAL_SOCKET_FUNCS.get("getaddrinfo")
    connect = ORIGINAL_SOCKET_FUNCS.get("connect")
    connect_ex = ORIGINAL_SOCKET_FUNCS.get("connect_ex")

    if create_connection is not None:
        socket.create_connection = create_connection
    if getaddrinfo is not None:
        socket.getaddrinfo = getaddrinfo
    if connect is not None:
        socket.socket.connect = connect
    if connect_ex is not None:
        socket.socket.connect_ex = connect_ex
