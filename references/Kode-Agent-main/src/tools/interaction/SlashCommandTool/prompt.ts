export const TOOL_NAME_FOR_PROMPT = 'SlashCommand'
export const DESCRIPTION = `- Executes predefined project commands stored in .claude/.kode/commands/*.md
- Input: command string (e.g., "/test" or "/deploy staging")
- Only executes known commands; otherwise returns an error`
