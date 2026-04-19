import { getModelManager } from '@utils/model'
import { generateKodeContext } from '@services/kodeContext'
import { generateSystemReminders } from '@services/systemReminder'

function isGPT5Model(modelName: string): boolean {
  return modelName.startsWith('gpt-5')
}

export function formatSystemPromptWithContext(
  systemPrompt: string[],
  context: { [k: string]: string },
  agentId?: string,
  skipContextReminders = false,
): { systemPrompt: string[]; reminders: string } {
  const enhancedPrompt = [...systemPrompt]
  let reminders = ''

  const modelManager = getModelManager()
  const modelProfile = modelManager.getModel('main')
  if (modelProfile && isGPT5Model(modelProfile.modelName)) {
    const persistencePrompts = [
      '\n# Agent Persistence for Long-Running Coding Tasks',
      'You are working on a coding project that may involve multiple steps and iterations. Please maintain context and continuity throughout the session:',
      '- Remember architectural decisions and design patterns established earlier',
      '- Keep track of file modifications and their relationships',
      '- Maintain awareness of the overall project structure and goals',
      '- Reference previous implementations when making related changes',
      '- Ensure consistency with existing code style and conventions',
      '- Build incrementally on previous work rather than starting from scratch',
    ]
    enhancedPrompt.push(...persistencePrompts)
  }

  const hasContext = Object.entries(context).length > 0

  if (hasContext) {
    if (!skipContextReminders) {
      const kodeContext = generateKodeContext()
      if (kodeContext) {
        enhancedPrompt.push('\n---\n# 项目上下文\n')
        enhancedPrompt.push(kodeContext)
        enhancedPrompt.push('\n---\n')
      }
    }

    const reminderMessages = generateSystemReminders(hasContext, agentId)
    if (reminderMessages.length > 0) {
      reminders = reminderMessages.map(r => r.content).join('\n') + '\n'
    }

    enhancedPrompt.push(
      `\nAs you answer the user's questions, you can use the following context:\n`,
    )

    const filteredContext = Object.fromEntries(
      Object.entries(context).filter(
        ([key]) => key !== 'projectDocs' && key !== 'userDocs',
      ),
    )

    enhancedPrompt.push(
      ...Object.entries(filteredContext).map(
        ([key, value]) => `<context name="${key}">${value}</context>`,
      ),
    )
  }

  return { systemPrompt: enhancedPrompt, reminders }
}
