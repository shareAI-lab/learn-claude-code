import { Command } from '@commands'
import { BashTool } from '@tools/BashTool/BashTool'

export default {
  type: 'prompt',
  name: 'review',
  description: 'Review a pull request',
  isEnabled: true,
  isHidden: false,
  progressMessage: 'reviewing pull request',
  userFacingName() {
    return 'review'
  },
  async getPromptForCommand(args) {
    return [
      {
        role: 'user',
        content: [
          {
            type: 'text',
            text: `
      You are an expert code reviewer. Follow these steps:

      1. If no PR number is provided in the args, use ${BashTool.name}("gh pr list") to show open PRs
      2. If a PR number is provided, use ${BashTool.name}("gh pr view <number>") to get PR details
      3. Use ${BashTool.name}("gh pr diff <number>") to get the diff
      4. Analyze the changes and provide a thorough code review that includes:
         - Overview of what the PR does
         - Analysis of code quality and style
         - Specific suggestions for improvements
         - Any potential issues or risks
      
      Keep your review concise but thorough. Focus on:
      - Code correctness
      - Following project conventions
      - Performance implications
      - Test coverage
      - Security considerations

      Format your review with clear sections and bullet points.

      PR number: ${args}
    `,
          },
        ],
      },
    ]
  },
} satisfies Command
