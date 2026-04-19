import fs from 'fs/promises'
import { logError } from '@utils/log'
import { Tool } from '@tool'

export async function loadMessagesFromLog(
  logPath: string,
  tools: Tool[],
): Promise<any[]> {
  try {
    const content = await fs.readFile(logPath, 'utf-8')
    const messages = JSON.parse(content)
    return deserializeMessages(messages, tools)
  } catch (error) {
    logError(`Failed to load messages from ${logPath}: ${error}`)
    throw new Error(`Failed to load messages from log: ${error}`)
  }
}

export function deserializeMessages(messages: any[], tools: Tool[]): any[] {
  const toolMap = new Map(tools.map(tool => [tool.name, tool]))

  return messages.map(message => {
    const clonedMessage = JSON.parse(JSON.stringify(message))

    if (clonedMessage.toolCalls) {
      clonedMessage.toolCalls = clonedMessage.toolCalls.map((toolCall: any) => {
        if (toolCall.tool && typeof toolCall.tool === 'string') {
          const actualTool = toolMap.get(toolCall.tool)
          if (actualTool) {
            toolCall.tool = actualTool
          }
        }
        return toolCall
      })
    }

    return clonedMessage
  })
}
