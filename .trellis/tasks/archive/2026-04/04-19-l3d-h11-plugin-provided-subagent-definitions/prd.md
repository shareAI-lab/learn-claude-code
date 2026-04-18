# L3-d: H11 plugin-provided subagent definitions

## Goal

允许本地插件声明并提供子 agent definitions。

## Requirements

* `plugin.json` 允许声明 `agents`
* 插件根目录提供 `subagents.json`
* plugin agent 必须通过现有 agent-definition merge path 加载
* plugin agent 名字必须带 plugin namespace

## Acceptance Criteria

* [x] plugin manifest 可以声明 agents
* [x] plugin `subagents.json` 会被加载和校验
* [x] plugin-provided agents 可被 `resolve_agent_definition(...)` 找到

## Out of Scope

* plugin-specific execution runtime
* remote plugin agent loading
