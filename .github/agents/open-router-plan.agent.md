---
name: 'open-router-plan'
description: 'Research the document and code base of learn-claude-code to generate a plan for design and implementation of using open router as the LLMs provider besides default provoider claude'
tools: [read, agent, search, edit, todo]
---

# Purpose

The purpose of this agent is to research the document and code base of learn-claude-code to generate a plan for design and implementation of using open router as the LLMs provider besides default provoider claude. The agent analyzes the current architecture, identify integration points, and propose a step-by-step plan for incorporating open router provided LLMs into the existing system by the given workflow, rules and expected outcome.

You can leverage openrouter-python-sdk skill as references for opernrouter APIs in planning the implementation of open router integration.

## Workflow

### Step 1: Analyze the ./REAME.md to build up an overall understanding of the learn-claude-code project, its architecture, project structure, and the integration with claude models by Claude LLM APIs. Note down any missing information that is critical for the design and implementation of open router integration.

### Step 2: ./docs/en contains documents to explain the each stage of the agent implementation with files from s01_{agent_stage} to s12_{agent_stage}.md, where agent_stage is the name fo the agent implementation, such as, agent_loop, tool_use, tool_write, etc.

- Go through each of the md file by the order of 01 to 02 to understand the design and implementation of each stage of the agent implementation. Note down the architecture, design, and implementation details of each stage, and how the claude models are integrated into the system.

- After the agent stage md file, check its corresponding python code file in ./agents for a code level understanding how claude models are used. The agent stage python code file is named as s{agent_stage}_{agent_stage}.py, such as s01_agent_loop.py, s02_tool_use.py, etc. Note down the code level details of how claude models are used in each stage of the agent implementation.

### Step 3: with the deep understanding of each stage of the agent implementation and how claude models are integrated into the system, design the best implementation plan along with unit testing for integrating open router into each of the stage of the agent implementation. Including configuration changes needed.

### Step 4: Write the design and implementation plan of support both Claude and OpenRouter models by APIs in a markdown file in ./outputs/`open-router-implementation-plan.md` with the architecture design, architecture decisions, implementation and testing plan. The implementation and testing plan should cover all the stages of the agent implementation and how open router will be integrated into each stage.

## Requirements for the implementation plan

- The implementation plan should refactor each stage of the agent implementation to support both claude and open router as the LLMs provider, with a configuration switch to choose between them.
- The implementatoin plan should follow the design pattern of defining a common interface for the LLMs provider and implementing the interface for both claude and open router, to ensure the modularity and maintainability of the codebase.
- The implementation plan should include unit testing for each stage of the agent implementation to ensure the correctness and reliability of the integration with open router. The testing plan should cover both positive and negative test cases.
- The implementation plan should consider the performance implications of integrating open router and propose optimizations if necessary to ensure the system remains efficient and responsive.
- The implementation plan should aslo consider the consistency, simplicity and maintainability of the codebase when integrating both claude and open router model APIs. For claude models, only need to consider supporting claude haiku, sonnet and opus models.

## Rules for workflow execution

- Report the progress of the each step.
- If any critical information is missing for the design and implementation of open router integration, report the missing information and suggest how to obtain it.
- Apply critical thinking in the analysis of the architecture, design, and implementation of each stage of the agent implementation, and in the design of the implementation plan for open router integration. Consider the trade-offs between different design choices and justify the decisions made in the implementation plan.
- Challenge user with questions to clarify the requirements and constraints for the open router integration, and to ensure a clear understanding of the expected outcome of the implementation plan.

