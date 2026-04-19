import type { Tool, ToolUseContext } from './tool'

export async function collectToolResult(
  tool: Tool,
  input: any,
  context: ToolUseContext,
): Promise<{
  data: any
  resultForAssistant?: string | any[]
  newMessages?: unknown[]
}> {
  let last: any
  for await (const item of tool.call(input as any, context)) {
    if (item.type === 'result') last = item
  }
  if (!last) {
    throw new Error(`Tool ${tool.name} produced no result`)
  }
  return {
    data: last.data,
    resultForAssistant: last.resultForAssistant,
    newMessages: last.newMessages,
  }
}

