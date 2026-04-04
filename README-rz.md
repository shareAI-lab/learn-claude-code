# Enhancements from the shareAI-lab/learn-claude-code

Forked from shareAI-lab/learn-claude-code for deep learning and exploring various enhancements with the agent harness.

## Goals

Build and maintain custom instructions/prompts/agents and agent skills with gh copilot agent harness to achieve AI-native software development cross full SDLC - from feature idealization, feature requirements/specification, architecture design and decisions, implementation plan, to code changes and testing. 

Essentially build and manage agent workfoce to perform SDLC tasks and automate SDLC workflows.

## Use .cladue struture for github copilot

### Agent harness extensions: claude code vs github copilt

| Claude Code | Github Copilot | What to achieve |
|----|----|----|
| custom sub-agent | custom agent | Define task specific workflows and improve context management |
| command | custom prompt | As slash command to trigger agent task/workflow |
| agent skill | agent skill | Subject matter expertise to extand agent harness capabilities with more effective context information for more precise outputs |
| cluade.md | copilot-instructions.md | Provide global context informtion for the project repo |

### Why use .claude structure

Agent harness extensions for github copilot are natively placed under ./.gitub while in ./.claude for claude code. 

However, github copilot supports extensions placed under ./.claude directory, but not vice versa. The decision is to place those agent extensions in ./.claude for,

- they can seamlessly work with both claude code and github copilot
- leave ./.github for hosting github action workflows

## Features

### Support wide ragne of LLMs

Currently, learn-claude-code is hardwired with Anthropic APIs and tied with Anthropic LLMs.

This enhancement is to refactor the design and implementation to support wide range of LLMs.

It can leverage a python SDK which provides unified API interface to the wide range of LLMs from providers like Anthropic, OpenAI, Google, xAI, HuggingFace or LLM routers like OpenRouter to open source models.


