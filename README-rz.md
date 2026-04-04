# Enhancements from the shareAI-lab/learn-claude-code

Forked from shareAI-lab/learn-claude-code for deep learning and exploring various enhancements with the agent harness.

## Goals

Build and maintain custom instructions/prompts/agents and agent skills with gh copilot agent harness to achieve AI-native software development cross full SDLC - from feature idealization, feature requirements/specification, architecture design and decisions, implementation plan, to code changes and testing. 

Essentially build and manage agent workfoce to perform SDLC tasks and automate SDLC workflows.

## Claude Code vs Github Copilot

### Agent harness extensions

| Claude Code | Github Copilot | What to achieve |
|----|----|----|
| custom sub-agent | custom agent | Define task specific workflows and improve context management |
| command | custom prompt | As slash command to trigger agent task/workflow |
| agent skill | agent skill | Subject matter expertise to extand agent harness capabilities with more effective context information for more precise outputs |
| cluade.md | copilot-instructions.md | Provide global context informtion for the project repo |

Agent harness extensions for github copilot are natively placed under ./.gitub while in ./.claude for claude code. 

### Agent Skills

Agent skill is open sourced as the common standard cross coding agent harnesses, github copilot recognizes agent skills installed in `./.github/skills/` and in `./.claude/skills/`

In this project, all agent skills, either self built or installed from public repos, are all placed under `./.claude/skills/`, so that they can seamlessly work with both claude code and github copilot

## Features

### Organize the python codebase into a uv project

### Support wide ragne of LLMs

Currently, learn-claude-code is hardwired with Anthropic APIs and tied with Anthropic LLMs.

This enhancement is to refactor the design and implementation to support wide range of LLMs.

It can leverage a python SDK which provides unified API interface to the wide range of LLMs from providers like Anthropic, OpenAI, Google, xAI, HuggingFace or LLM routers like OpenRouter to open source models.


