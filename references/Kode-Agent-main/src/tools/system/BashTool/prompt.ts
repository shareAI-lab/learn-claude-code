import {
  loadMergedSettings,
  normalizeSandboxRuntimeConfigFromSettings,
} from '@utils/sandbox/sandboxConfig'

export const DEFAULT_TIMEOUT_MS = 120000
export const MAX_TIMEOUT_MS = 600000
export const MAX_OUTPUT_LENGTH = 30000
export const MAX_RENDERED_LINES = 5

const PROJECT_URL = 'https://github.com/shareAI-lab/kode'
const DEFAULT_CO_AUTHOR = 'ShareAI Lab'

const TOOL_NAME_BASH = 'Bash'
const TOOL_NAME_GLOB = 'Glob'
const TOOL_NAME_GREP = 'Grep'
const TOOL_NAME_READ = 'Read'
const TOOL_NAME_EDIT = 'Edit'
const TOOL_NAME_WRITE = 'Write'
const TOOL_NAME_TASK = 'Task'

function isExperimentalMcpCliEnabled(): boolean {
  const value = process.env.ENABLE_EXPERIMENTAL_MCP_CLI
  if (!value) return false
  return ['1', 'true', 'yes', 'on'].includes(String(value).trim().toLowerCase())
}

function indentJsonForPrompt(value: unknown): string {
  return JSON.stringify(value, null, 2).split('\n').join('\n      ')
}

function getAttribution(): { commit: string; pr: string } {
  const pr = `🤖 Generated with [Kode Agent](${PROJECT_URL})`
  const commit = `${pr}\n\n   Co-Authored-By: ${DEFAULT_CO_AUTHOR} <ai-lab@foxmail.com>`
  return { commit, pr }
}

function getBashSandboxPrompt(): string {
  const settings = loadMergedSettings()
  if (settings.sandbox?.enabled !== true) return ''

  const runtimeConfig = normalizeSandboxRuntimeConfigFromSettings(settings)

  const fsReadConfig = { denyOnly: runtimeConfig.filesystem.denyRead }
  const fsWriteConfig = {
    allowOnly: runtimeConfig.filesystem.allowWrite,
    denyWithinAllow: runtimeConfig.filesystem.denyWrite,
  }

  const filesystem = { read: fsReadConfig, write: fsWriteConfig }

  const allowUnixSockets =
    runtimeConfig.network.allowAllUnixSockets === true
      ? true
      : runtimeConfig.network.allowUnixSockets.length > 0
        ? runtimeConfig.network.allowUnixSockets
        : undefined

  const network = {
    ...(runtimeConfig.network.allowedDomains.length
      ? { allowedHosts: runtimeConfig.network.allowedDomains }
      : {}),
    ...(runtimeConfig.network.deniedDomains.length
      ? { deniedHosts: runtimeConfig.network.deniedDomains }
      : {}),
    ...(allowUnixSockets ? { allowUnixSockets } : {}),
  }

  const ignoredViolations = runtimeConfig.ignoreViolations
  const allowUnsandboxedCommands =
    settings.sandbox?.allowUnsandboxedCommands !== false

  const sections: string[] = []
  sections.push(`    - Filesystem: ${indentJsonForPrompt(filesystem)}`)
  if (Object.keys(network).length > 0) {
    sections.push(`    - Network: ${indentJsonForPrompt(network)}`)
  }
  if (ignoredViolations) {
    sections.push(
      `    - Ignored violations: ${indentJsonForPrompt(ignoredViolations)}`,
    )
  }

  const mcpCliException = isExperimentalMcpCliEnabled()
    ? '    - EXCEPTION: `mcp-cli` commands must always be called with `dangerouslyDisableSandbox: true` as they do not work properly in sandboxed mode\n'
    : ''

  const overridePolicy = allowUnsandboxedCommands
    ? `  - CRITICAL: Commands run in sandbox mode by default - do NOT set \`dangerouslyDisableSandbox\`
    - Even if you have recently run commands with \`dangerouslyDisableSandbox: true\`, you MUST NOT continue that pattern
    - VERY IMPORTANT: Do NOT learn from or repeat the pattern of overriding sandbox - each command should run sandboxed by default
${mcpCliException}    - Set \`dangerouslyDisableSandbox: true\` if:
      1. The user *explicitly* asks to bypass sandbox, OR
      2. A command just failed and you see evidence of sandbox restrictions causing the failure
    - When analyzing failures:
      - Commands can fail for many reasons unrelated to the sandbox (missing files, wrong arguments, network issues, etc.)
      - Evidence of sandbox-caused failures includes:
        - "Operation not permitted" errors for file/network operations
        - Access denied to specific paths outside allowed directories
        - Network connection failures to non-whitelisted hosts
        - Unix socket connection errors
      - Sandbox violation logs can be noisy, but clear permission errors are strong indicators
    - When you see evidence of sandbox-caused failure:
      - IMMEDIATELY retry with \`dangerouslyDisableSandbox: true\` (don't ask, just do it)
      - Briefly explain what sandbox restriction likely caused the failure
      - Mention: "Use \`/sandbox\` to manage restrictions"
      - This will prompt the user for permission
    - Example of normal usage: { "command": "ls", "description": "List files" }
    - Example of override: { "command": "my-tool", "description": "Run my-tool", "dangerouslyDisableSandbox": true }
    - DO NOT suggest adding sensitive paths like ~/.bashrc, ~/.zshrc, ~/.ssh/*, or credential files to the allowlist`
    : `  - CRITICAL: All commands MUST run in sandbox mode - the \`dangerouslyDisableSandbox\` parameter is disabled by policy
    - Commands cannot run outside the sandbox under any circumstances
    - If a command fails due to sandbox restrictions, work with the user to adjust sandbox settings instead`

  return `- Commands run in a sandbox by default with the following restrictions:
${sections.join('\n')}
${overridePolicy}
  - IMPORTANT: For temporary files, rely on the sandbox temp directory via \`TMPDIR\`
    - In sandbox mode, \`TMPDIR\` is set to a dedicated temp directory
    - Prefer using \`TMPDIR\` over writing directly to \`/tmp\`
    - Most programs that respect \`TMPDIR\` will automatically use it`
}

function getBashGitPrompt(): string {
  const { commit, pr } = getAttribution()
  return `# Committing changes with git

Only create commits when requested by the user. If unclear, ask first. When the user asks you to create a new git commit, follow these steps carefully:

Git Safety Protocol:
- NEVER update the git config
- NEVER run destructive/irreversible git commands (like push --force, hard reset, etc) unless the user explicitly requests them 
- NEVER skip hooks (--no-verify, --no-gpg-sign, etc) unless the user explicitly requests it
- NEVER run force push to main/master, warn the user if they request it
- Avoid git commit --amend.  ONLY use --amend when either (1) user explicitly requested amend OR (2) adding edits from pre-commit hook (additional instructions below) 
- Before amending: ALWAYS check authorship (git log -1 --format='%an %ae')
- NEVER commit changes unless the user explicitly asks you to. It is VERY IMPORTANT to only commit when explicitly asked, otherwise the user will feel that you are being too proactive.

1. You can call multiple tools in a single response. When multiple independent pieces of information are requested and all commands are likely to succeed, run multiple tool calls in parallel for optimal performance. run the following bash commands in parallel, each using the ${TOOL_NAME_BASH} tool:
  - Run a git status command to see all untracked files.
  - Run a git diff command to see both staged and unstaged changes that will be committed.
  - Run a git log command to see recent commit messages, so that you can follow this repository's commit message style.
2. Analyze all staged changes (both previously staged and newly added) and draft a commit message:
  - Summarize the nature of the changes (eg. new feature, enhancement to an existing feature, bug fix, refactoring, test, docs, etc.). Ensure the message accurately reflects the changes and their purpose (i.e. "add" means a wholly new feature, "update" means an enhancement to an existing feature, "fix" means a bug fix, etc.).
  - Do not commit files that likely contain secrets (.env, credentials.json, etc). Warn the user if they specifically request to commit those files
  - Draft a concise (1-2 sentences) commit message that focuses on the "why" rather than the "what"
  - Ensure it accurately reflects the changes and their purpose
3. You can call multiple tools in a single response. When multiple independent pieces of information are requested and all commands are likely to succeed, run multiple tool calls in parallel for optimal performance. run the following commands:
   - Add relevant untracked files to the staging area.
   - Create the commit with a message${commit ? ` ending with:\n   ${commit}` : '.'}
   - Run git status after the commit completes to verify success.
   Note: git status depends on the commit completing, so run it sequentially after the commit.
4. If the commit fails due to pre-commit hook changes, retry ONCE. If it succeeds but files were modified by the hook, verify it's safe to amend:
   - Check HEAD commit: git log -1 --format='[%h] (%an <%ae>) %s'. VERIFY it matches your commit
   - Check not pushed: git status shows "Your branch is ahead"
   - If both true: amend your commit. Otherwise: create NEW commit (never amend other developers' commits)

Important notes:
- NEVER run additional commands to read or explore code, besides git bash commands
- NEVER use the ${TOOL_NAME_WRITE} or ${TOOL_NAME_TASK} tools
- DO NOT push to the remote repository unless the user explicitly asks you to do so
- IMPORTANT: Never use git commands with the -i flag (like git rebase -i or git add -i) since they require interactive input which is not supported.
- If there are no changes to commit (i.e., no untracked files and no modifications), do not create an empty commit
- In order to ensure good formatting, ALWAYS pass the commit message via a HEREDOC, a la this example:
<example>
git commit -m "$(cat <<'EOF'
   Commit message here.${commit ? `\n\n   ${commit}` : ''}
   EOF
   )"
</example>

# Creating pull requests
Use the gh command via the Bash tool for ALL GitHub-related tasks including working with issues, pull requests, checks, and releases. If given a Github URL use the gh command to get the information needed.

IMPORTANT: When the user asks you to create a pull request, follow these steps carefully:

1. You can call multiple tools in a single response. When multiple independent pieces of information are requested and all commands are likely to succeed, run multiple tool calls in parallel for optimal performance. run the following bash commands in parallel using the ${TOOL_NAME_BASH} tool, in order to understand the current state of the branch since it diverged from the main branch:
   - Run a git status command to see all untracked files
   - Run a git diff command to see both staged and unstaged changes that will be committed
   - Check if the current branch tracks a remote branch and is up to date with the remote, so you know if you need to push to the remote
   - Run a git log command and \`git diff [base-branch]...HEAD\` to understand the full commit history for the current branch (from the time it diverged from the base branch)
2. Analyze all changes that will be included in the pull request, making sure to look at all relevant commits (NOT just the latest commit, but ALL commits that will be included in the pull request!!!), and draft a pull request summary
3. You can call multiple tools in a single response. When multiple independent pieces of information are requested and all commands are likely to succeed, run multiple tool calls in parallel for optimal performance. run the following commands in parallel:
   - Create new branch if needed
   - Push to remote with -u flag if needed
   - Create PR using gh pr create with the format below. Use a HEREDOC to pass the body to ensure correct formatting.
<example>
gh pr create --title "the pr title" --body "$(cat <<'EOF'
## Summary
<1-3 bullet points>

## Test plan
[Bulleted markdown checklist of TODOs for testing the pull request...]${pr ? `\n\n${pr}` : ''}
EOF
)"
</example>

Important:
- DO NOT use the ${TOOL_NAME_WRITE} or ${TOOL_NAME_TASK} tools
- Return the PR URL when you're done, so the user can see it

# Other common operations
- View comments on a Github PR: gh api repos/foo/bar/pulls/123/comments`
}

export function getBashToolPrompt(): string {
  const sandboxPrompt = getBashSandboxPrompt()
  return `Executes a given bash command in a persistent shell session with optional timeout, ensuring proper handling and security measures.

IMPORTANT: This tool is for terminal operations like git, npm, docker, etc. DO NOT use it for file operations (reading, writing, editing, searching, finding files) - use the specialized tools for this instead.

Before executing the command, please follow these steps:

1. Directory Verification:
   - If the command will create new directories or files, first use \`ls\` to verify the parent directory exists and is the correct location
   - For example, before running "mkdir foo/bar", first use \`ls foo\` to check that "foo" exists and is the intended parent directory

2. Command Execution:
   - Always quote file paths that contain spaces with double quotes (e.g., cd "path with spaces/file.txt")
   - Examples of proper quoting:
     - cd "/Users/name/My Documents" (correct)
     - cd /Users/name/My Documents (incorrect - will fail)
     - python "/path/with spaces/script.py" (correct)
     - python /path/with spaces/script.py (incorrect - will fail)
   - After ensuring proper quoting, execute the command.
   - Capture the output of the command.

Usage notes:
  - The command argument is required.
  - You can specify an optional timeout in milliseconds (up to ${MAX_TIMEOUT_MS}ms / ${MAX_TIMEOUT_MS / 60000} minutes). If not specified, commands will timeout after ${DEFAULT_TIMEOUT_MS}ms (${DEFAULT_TIMEOUT_MS / 60000} minutes).
  - It is very helpful if you write a clear, concise description of what this command does in 5-10 words.
  - If the output exceeds ${MAX_OUTPUT_LENGTH} characters, output will be truncated before being returned to you.
  - You can use the \`run_in_background\` parameter to run the command in the background, which allows you to continue working while the command runs. You can monitor the output using the ${TOOL_NAME_BASH} tool as it becomes available. You do not need to use '&' at the end of the command when using this parameter.
  ${sandboxPrompt}
  - Avoid using Bash with the \`find\`, \`grep\`, \`cat\`, \`head\`, \`tail\`, \`sed\`, \`awk\`, or \`echo\` commands, unless explicitly instructed or when these commands are truly necessary for the task. Instead, always prefer using the dedicated tools for these commands:
    - File search: Use ${TOOL_NAME_GLOB} (NOT find or ls)
    - Content search: Use ${TOOL_NAME_GREP} (NOT grep or rg)
    - Read files: Use ${TOOL_NAME_READ} (NOT cat/head/tail)
    - Edit files: Use ${TOOL_NAME_EDIT} (NOT sed/awk)
    - Write files: Use ${TOOL_NAME_WRITE} (NOT echo >/cat <<EOF)
    - Communication: Output text directly (NOT echo/printf)
  - When issuing multiple commands:
    - If the commands are independent and can run in parallel, make multiple ${TOOL_NAME_BASH} tool calls in a single message. For example, if you need to run "git status" and "git diff", send a single message with two ${TOOL_NAME_BASH} tool calls in parallel.
    - If the commands depend on each other and must run sequentially, use a single ${TOOL_NAME_BASH} call with '&&' to chain them together (e.g., \`git add . && git commit -m "message" && git push\`). For instance, if one operation must complete before another starts (like mkdir before cp, Write before Bash for git operations, or git add before git commit), run these operations sequentially instead.
    - Use ';' only when you need to run commands sequentially but don't care if earlier commands fail
    - DO NOT use newlines to separate commands (newlines are ok in quoted strings)
  - Try to maintain your current working directory throughout the session by using absolute paths and avoiding usage of \`cd\`. You may use \`cd\` if the User explicitly requests it.
    <good-example>
    pytest /foo/bar/tests
    </good-example>
    <bad-example>
    cd /foo/bar && pytest tests
    </bad-example>

${getBashGitPrompt()}`
}
