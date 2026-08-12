from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass(slots=True)
class SessionState:
    history: list = field(default_factory=list)
    context: dict = field(default_factory=dict)
    todos: list[dict] = field(default_factory=list)
    rounds_since_todo: int = 0


from homework.agent_app.adapters.anthropic import AnthropicAdapter
from homework.agent_app.config import AppConfig
from homework.agent_app.core.prompt import PromptBuilder
from homework.agent_app.features.background import BackgroundState
from homework.agent_app.features.mcp import MCPState
from homework.agent_app.features.memory import MemoryStore
from homework.agent_app.features.scheduler import SchedulerState
from homework.agent_app.features.skills import SkillState
from homework.agent_app.features.tasks import TaskStore
from homework.agent_app.features.teams.bus import MessageBus
from homework.agent_app.features.teams.protocol import ProtocolStore
from homework.agent_app.features.teams.teammates import TeamState
from homework.agent_app.features.worktrees import WorktreeState
from homework.agent_app.tools.hooks import HookRegistry
from homework.agent_app.tools.registry import ToolRegistry


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
