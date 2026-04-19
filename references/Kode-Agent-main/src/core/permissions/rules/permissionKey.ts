import { BashTool } from '@tools/BashTool/BashTool'
import { SkillTool } from '@tools/ai/SkillTool/SkillTool'
import { SlashCommandTool } from '@tools/interaction/SlashCommandTool/SlashCommandTool'
import { WebFetchTool } from '@tools/network/WebFetchTool/WebFetchTool'
import { WebSearchTool } from '@tools/network/WebSearchTool/WebSearchTool'
import type { Tool } from '@tool'

export function getPermissionKey(
  tool: Tool,
  input: { [k: string]: unknown },
  prefix: string | null,
): string {
  switch (tool) {
    case BashTool:
      if (prefix) {
        return `${BashTool.name}(${prefix}:*)`
      }
      return `${BashTool.name}(${typeof (input as any).command === 'string' ? String((input as any).command).trim() : ''})`
    case WebFetchTool: {
      try {
        const schema: any = (WebFetchTool as any).inputSchema
        const parsed = schema?.safeParse
          ? schema.safeParse(input)
          : { success: false }
        if (!parsed.success) {
          return `${WebFetchTool.name}(input:${String(input)})`
        }
        const url = parsed.data.url
        return `${WebFetchTool.name}(domain:${new URL(url).hostname})`
      } catch {
        return `${WebFetchTool.name}(input:${String(input)})`
      }
    }
    case WebSearchTool: {
      const query =
        typeof (input as any).query === 'string'
          ? String((input as any).query).trim()
          : ''
      if (!query) return WebSearchTool.name
      return `${WebSearchTool.name}(${query})`
    }
    case SlashCommandTool: {
      const command =
        typeof input.command === 'string' ? input.command.trim() : ''
      if (prefix) {
        return `${SlashCommandTool.name}(${prefix}:*)`
      }
      return `${SlashCommandTool.name}(${command})`
    }
    case SkillTool: {
      const raw = typeof input.skill === 'string' ? input.skill : ''
      const skill = raw.trim().replace(/^\//, '')
      if (prefix) {
        const p = prefix.trim().replace(/^\//, '')
        return `${SkillTool.name}(${p}:*)`
      }
      return `${SkillTool.name}(${skill})`
    }
    default:
      return tool.name
  }
}
