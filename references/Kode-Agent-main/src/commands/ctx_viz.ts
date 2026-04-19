import type { Command } from '@commands'
import type { Tool } from '@tool'
import Table from 'cli-table3'
import { getSystemPrompt } from '@constants/prompts'
import { getContext } from '@context'
import { zodToJsonSchema } from 'zod-to-json-schema'
import { getMessagesGetter } from '@messages'
import { PROJECT_FILE } from '@constants/product'
// Quick and dirty estimate of bytes per token for rough token counts
const BYTES_PER_TOKEN = 4

interface Section {
  title: string
  content: string
}

interface ToolSummary {
  name: string
  description: string
}

function getContextSections(text: string): Section[] {
  const sections: Section[] = []

  // Find first <context> tag
  const firstContextIndex = text.indexOf('<context')

  // Everything before first tag is Core Sysprompt
  if (firstContextIndex > 0) {
    const coreSysprompt = text.slice(0, firstContextIndex).trim()
    if (coreSysprompt) {
      sections.push({
        title: 'Core Sysprompt',
        content: coreSysprompt,
      })
    }
  }

  let currentPos = firstContextIndex
  let nonContextContent = ''

  const regex = /<context\s+name="([^"]*)">([\s\S]*?)<\/context>/g
  let match: RegExpExecArray | null

  while ((match = regex.exec(text)) !== null) {
    // Collect text between context tags
    if (match.index > currentPos) {
      nonContextContent += text.slice(currentPos, match.index)
    }

    const [, name = 'Unnamed Section', content = ''] = match
    sections.push({
      title: name === 'codeStyle' ? `CodeStyle + ${PROJECT_FILE}'s` : name,
      content: content.trim(),
    })

    currentPos = match.index + match[0].length
  }

  // Collect remaining text after last tag
  if (currentPos < text.length) {
    nonContextContent += text.slice(currentPos)
  }

  // Add non-contextualized content if present
  const trimmedNonContext = nonContextContent.trim()
  if (trimmedNonContext) {
    sections.push({
      title: 'Non-contextualized Content',
      content: trimmedNonContext,
    })
  }

  return sections
}

function formatTokenCount(bytes: number): string {
  const tokens = bytes / BYTES_PER_TOKEN
  const k = tokens / 1000
  return `${Math.round(k * 10) / 10}k`
}

function formatByteCount(bytes: number): string {
  const kb = bytes / 1024
  return `${Math.round(kb * 10) / 10}kb`
}

function createSummaryTable(
  systemText: string,
  systemSections: Section[],
  tools: ToolSummary[],
  messages: unknown,
): string {
  const table = new Table({
    head: ['Component', 'Tokens', 'Size', '% Used'],
    style: { head: ['bold'] },
    chars: {
      mid: '─',
      'left-mid': '├',
      'mid-mid': '┼',
      'right-mid': '┤',
    },
  })

  const messagesStr = JSON.stringify(messages)
  const toolsStr = JSON.stringify(tools)

  // Calculate total for percentages
  const total = systemText.length + toolsStr.length + messagesStr.length
  const getPercentage = (n: number) => `${Math.round((n / total) * 100)}%`

  // System prompt and its sections
  table.push([
    'System prompt',
    formatTokenCount(systemText.length),
    formatByteCount(systemText.length),
    getPercentage(systemText.length),
  ])
  for (const section of systemSections) {
    table.push([
      `  ${section.title}`,
      formatTokenCount(section.content.length),
      formatByteCount(section.content.length),
      getPercentage(section.content.length),
    ])
  }

  // Tools
  table.push([
    'Tool definitions',
    formatTokenCount(toolsStr.length),
    formatByteCount(toolsStr.length),
    getPercentage(toolsStr.length),
  ])
  for (const tool of tools) {
    table.push([
      `  ${tool.name}`,
      formatTokenCount(tool.description.length),
      formatByteCount(tool.description.length),
      getPercentage(tool.description.length),
    ])
  }

  // Messages and total
  table.push(
    [
      'Messages',
      formatTokenCount(messagesStr.length),
      formatByteCount(messagesStr.length),
      getPercentage(messagesStr.length),
    ],
    ['Total', formatTokenCount(total), formatByteCount(total), '100%'],
  )

  return table.toString()
}

const command: Command = {
  name: 'ctx-viz',
  description:
    'Show token usage breakdown for the current conversation context',
  isEnabled: true,
  isHidden: false,
  type: 'local',

  userFacingName() {
    return this.name
  },

  async call(_args: string, cmdContext: { options: { tools: Tool[] } }) {
    // Get tools and system prompt with injected context
    const [systemPromptRaw, sysContext] = await Promise.all([
      getSystemPrompt(),
      getContext(),
    ])

    const rawTools = cmdContext.options.tools

    // Full system prompt with context sections injected
    let systemPrompt = systemPromptRaw.join('\n')
    for (const [name, content] of Object.entries(sysContext)) {
      systemPrompt += `\n<context name="${name}">${content}</context>`
    }

    // Get full tool definitions including prompts and schemas
    const tools = rawTools.map(t => {
      // Get full prompt and schema
      const fullPrompt = t.prompt({ safeMode: false })
      const schema = JSON.stringify(
        'inputJSONSchema' in t && t.inputJSONSchema
          ? t.inputJSONSchema
          : zodToJsonSchema(t.inputSchema),
      )

      return {
        name: t.name,
        description: `${fullPrompt}\n\nSchema:\n${schema}`,
      }
    })

    // Get current messages from REPL
    const messages = getMessagesGetter()()

    const sections = getContextSections(systemPrompt)
    return createSummaryTable(systemPrompt, sections, tools, messages)
  },
}

export default command
