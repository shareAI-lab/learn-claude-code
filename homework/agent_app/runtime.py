from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass(slots=True)
class SessionState:
    history: list = field(default_factory=list)
    context: dict = field(default_factory=dict)
    todos: list[dict] = field(default_factory=list)
    rounds_since_todo: int = 0


from .adapters.anthropic import AnthropicAdapter
from .config import AppConfig
from .core.prompt import PromptBuilder
from .features.background import BackgroundState
from .features.mcp import MCPState
from .features.memory import MemoryStore
from .features.scheduler import SchedulerState
from .features.skills import SkillState
from .features.tasks import TaskStore
from .features.teams.bus import MessageBus
from .features.teams.protocol import ProtocolStore
from .features.teams.teammates import TeamState
from .features.worktrees import WorktreeState
from .tools.hooks import HookRegistry
from .tools.registry import ToolRegistry


@dataclass(slots=True)
class RuntimeContext:
    config: AppConfig
    llm: AnthropicAdapter
    session: SessionState
    prompt_builder: PromptBuilder
    tools: ToolRegistry
    hooks: HookRegistry
    scheduler: SchedulerState
    background: BackgroundState
    tasks: TaskStore
    worktrees: WorktreeState
    skills: SkillState
    memory: MemoryStore
    bus: MessageBus
    protocols: ProtocolStore
    team: TeamState
    mcp: MCPState
    agent_lock: threading.Lock = field(default_factory=threading.Lock)
    stop_event: threading.Event = field(default_factory=threading.Event)
