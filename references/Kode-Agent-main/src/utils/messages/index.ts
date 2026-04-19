export * from './core'

import type { SetToolJSXFn, ToolUseContext } from '@tool'
import type { Message } from '@query'

export async function processUserInput(
  input: string,
  mode: 'bash' | 'prompt' | 'koding',
  setToolJSX: SetToolJSXFn,
  context: ToolUseContext & {
    setForkConvoWithMessagesOnTheNextRender: (
      forkConvoWithMessages: Message[],
    ) => void
    options?: {
      isKodingRequest?: boolean
      kodingContext?: string
    }
  },
  pastedImages: Array<{
    placeholder: string
    data: string
    mediaType: string
  }> | null,
): Promise<Message[]> {
  const impl = await import('./userInput')
  return impl.processUserInput(input, mode, setToolJSX, context, pastedImages)
}

