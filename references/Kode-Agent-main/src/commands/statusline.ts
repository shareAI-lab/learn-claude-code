import type { Command } from '@commands'

export default {
  type: 'prompt',
  name: 'statusline',
  description: "Set up Kode's status line UI",
  isEnabled: true,
  isHidden: false,
  progressMessage: 'setting up statusLine',
  disableNonInteractive: true,
  allowedTools: ['Task', 'Read(~/**)', 'Edit(~/.kode/settings.json)'],
  userFacingName() {
    return 'statusline'
  },
  async getPromptForCommand(args) {
    const prompt =
      args.trim() || 'Configure my statusLine from my shell PS1 configuration'
    return [
      {
        role: 'user',
        content: [
          {
            type: 'text',
            text: `Create a Task with subagent_type "statusline-setup" and the prompt ${JSON.stringify(
              prompt,
            )}`,
          },
        ],
      },
    ]
  },
} satisfies Command
