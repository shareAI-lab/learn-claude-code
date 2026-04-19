export const TOOL_NAME_FOR_PROMPT = 'KillShell'
export const DESCRIPTION = 'Kill a background bash shell by ID'

export const PROMPT = `
- Kills a running background bash shell by its ID
- Takes a shell_id parameter identifying the shell to kill
- Returns a success or failure status 
- Use this tool when you need to terminate a long-running shell
- Shell IDs can be found using the /tasks command
`
