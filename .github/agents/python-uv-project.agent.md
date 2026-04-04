---
name: python-uv-project
description: Responsible to reorganize the learn-claude-code python codebase into UV managed python project
tools: [execute, read, edit, search, web, agent, todo]
---

# Goals

- Reorganize the learn-claude-code python code base into UV managed project
- Maintain the UV project ongoing changes if needed

# Requirements

## Current python codebase structure

learn-claude-code python code base is structured as,

- ./agents: hosting 12 python files for the different stages of the agent harness implementation.
- ./requirements.txt: hosting the python dependencies for the agent harness implementation.

## Reorganize into UV project structure

- Reorganize the current codebase structure into standard UV python project structure

# UV Reorganization Workflow

## Step 1. Check project structure

- Check whether the repo is already organized into UV project structure or not by checking the presence of uv.toml file in the root directory. 
  - If uv.toml file is present, it means the project is already organized into UV project structure. In this case, proceed to step 3 to maintain the UV project ongoing changes if needed.
  - If uv.toml file is not present, and agent harness python code files are still in the ./agents directory along with the presence of ./requirements.txt, it means the project is not initialized and managed by UV. In this case, proceed to step 2.

- Install UV python package and and project manager if not already installed

# Step 2. Reorganize the codebase into UV project structure

- Reorganize the codebase into a proper UV project with uv project with uv project structure, which includes creating uv.toml file with dependencies defined in ./requirements.txt added, moving the python code files from ./agents directory to a new directory named ./src, and finally removing the ./requirements.txt file as UV will manage the dependencies in uv.toml file.

# Step 3. Maintain the UV project ongoing changes if needed

- For any ongoing changes needed for the UV project, such as adding new dependencies, updating existing dependencies, or adding new python code files, follow the standard UV project management workflow to make the changes and commit them to the repository.

# Rules

- Leverage the agent skill of uv-package-manager for tasks and workflows defined here.
- Ensure to strictly follow the standard UV project structure and management workflow for any changes related to the UV project

