import { randomUUID } from 'crypto'
import type { AgentConfig } from '@utils/agent/loader'
import { debug as debugLogger } from '@utils/log/debugLogger'
import { logError } from '@utils/log'

export type GeneratedAgent = {
  identifier: string
  whenToUse: string
  systemPrompt: string
}

export async function generateAgentWithClaude(
  prompt: string,
): Promise<GeneratedAgent> {
  const { queryModel } = await import('@services/llm')

  const systemPrompt = `You are an expert at creating AI agent configurations. Based on the user's description, generate a specialized agent configuration.

Return your response as a JSON object with exactly these fields:
- identifier: A short, kebab-case identifier for the agent (e.g., "code-reviewer", "security-auditor")
- whenToUse: A clear description of when this agent should be used (50-200 words)
- systemPrompt: A comprehensive system prompt that defines the agent's role, capabilities, and behavior (200-500 words)

Make the agent highly specialized and effective for the described use case.`

  try {
    const messages = [
      {
        type: 'user',
        uuid: randomUUID(),
        message: { role: 'user', content: prompt },
      },
    ] as any
    const response = await queryModel('main', messages, [systemPrompt])

    let responseText = ''
    if (typeof response.message?.content === 'string') {
      responseText = response.message.content
    } else if (Array.isArray(response.message?.content)) {
      const textContent = response.message.content.find(
        (c: any) => c.type === 'text',
      )
      responseText = textContent?.text || ''
    } else if (response.message?.content?.[0]?.text) {
      responseText = response.message.content[0].text
    }

    if (!responseText) {
      throw new Error('No text content in model response')
    }

    const MAX_JSON_SIZE = 100_000
    const MAX_FIELD_LENGTH = 10_000

    if (responseText.length > MAX_JSON_SIZE) {
      throw new Error('Response too large')
    }

    let parsed: any
    try {
      parsed = JSON.parse(responseText.trim())
    } catch {
      const startIdx = responseText.indexOf('{')
      const endIdx = responseText.lastIndexOf('}')

      if (startIdx === -1 || endIdx === -1 || startIdx >= endIdx) {
        throw new Error('No valid JSON found in model response')
      }

      const jsonStr = responseText.substring(startIdx, endIdx + 1)
      if (jsonStr.length > MAX_JSON_SIZE) {
        throw new Error('JSON content too large')
      }

      try {
        parsed = JSON.parse(jsonStr)
      } catch (parseError) {
        throw new Error(
          `Invalid JSON format: ${parseError instanceof Error ? parseError.message : 'Unknown error'}`,
        )
      }
    }

    const identifier = String(parsed.identifier || '')
      .slice(0, 100)
      .trim()
    const whenToUse = String(parsed.whenToUse || '')
      .slice(0, MAX_FIELD_LENGTH)
      .trim()
    const agentSystemPrompt = String(parsed.systemPrompt || '')
      .slice(0, MAX_FIELD_LENGTH)
      .trim()

    if (!identifier || !whenToUse || !agentSystemPrompt) {
      throw new Error(
        'Invalid response structure: missing required fields (identifier, whenToUse, systemPrompt)',
      )
    }

    const sanitize = (str: string) => str.replace(/[\x00-\x1F\x7F-\x9F]/g, '')

    const cleanIdentifier = sanitize(identifier)
    if (!/^[a-zA-Z0-9-]+$/.test(cleanIdentifier)) {
      throw new Error(
        'Invalid identifier format: only letters, numbers, and hyphens allowed',
      )
    }

    return {
      identifier: cleanIdentifier,
      whenToUse: sanitize(whenToUse),
      systemPrompt: sanitize(agentSystemPrompt),
    }
  } catch (error) {
    logError(error)
    debugLogger.warn('AGENT_GENERATION_FAILED', {
      error: error instanceof Error ? error.message : String(error),
    })

    const fallbackId = prompt
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .slice(0, 30)

    return {
      identifier: fallbackId || 'custom-agent',
      whenToUse: `Use this agent when you need assistance with: ${prompt}`,
      systemPrompt: `You are a specialized assistant focused on helping with ${prompt}. Provide expert-level assistance in this domain.`,
    }
  }
}

export function validateAgentType(
  agentType: string,
  existingAgents: AgentConfig[] = [],
): {
  isValid: boolean
  errors: string[]
  warnings: string[]
} {
  const errors: string[] = []
  const warnings: string[] = []

  if (!agentType) {
    errors.push('Agent type is required')
    return { isValid: false, errors, warnings }
  }

  if (!/^[a-zA-Z]/.test(agentType)) {
    errors.push('Agent type must start with a letter')
  }

  if (!/^[a-zA-Z0-9-]+$/.test(agentType)) {
    errors.push('Agent type can only contain letters, numbers, and hyphens')
  }

  if (agentType.length < 3) {
    errors.push('Agent type must be at least 3 characters long')
  }

  if (agentType.length > 50) {
    errors.push('Agent type must be less than 50 characters')
  }

  const reserved = ['help', 'exit', 'quit', 'agents', 'task']
  if (reserved.includes(agentType.toLowerCase())) {
    errors.push('This name is reserved')
  }

  const duplicate = existingAgents.find(a => a.agentType === agentType)
  if (duplicate) {
    errors.push(
      `An agent with this name already exists in ${duplicate.location}`,
    )
  }

  if (agentType.includes('--')) {
    warnings.push('Consider avoiding consecutive hyphens')
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  }
}

export type AgentDraftForValidation = {
  agentType?: string
  whenToUse?: string
  systemPrompt?: string
  selectedTools?: string[]
}

export function validateAgentConfig(
  config: AgentDraftForValidation,
  existingAgents: AgentConfig[] = [],
): {
  isValid: boolean
  errors: string[]
  warnings: string[]
} {
  const errors: string[] = []
  const warnings: string[] = []

  if (config.agentType) {
    const typeValidation = validateAgentType(config.agentType, existingAgents)
    errors.push(...typeValidation.errors)
    warnings.push(...typeValidation.warnings)
  }

  if (!config.whenToUse) {
    errors.push('Description is required')
  } else if (config.whenToUse.length < 10) {
    warnings.push(
      'Description should be more descriptive (at least 10 characters)',
    )
  }

  if (!config.systemPrompt) {
    errors.push('System prompt is required')
  } else if (config.systemPrompt.length < 20) {
    warnings.push(
      'System prompt might be too short for effective agent behavior',
    )
  }

  if (!config.selectedTools || config.selectedTools.length === 0) {
    warnings.push('No tools selected - agent will have limited capabilities')
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  }
}

export function generateAgentFileContent(
  agentType: string,
  description: string,
  tools: string[] | '*',
  systemPrompt: string,
  model?: string,
  color?: string,
): string {
  const desc = description.replace(/\n/g, '\\n')

  const toolsList =
    tools === '*'
      ? undefined
      : Array.isArray(tools) && tools.length === 1 && tools[0] === '*'
        ? undefined
        : Array.isArray(tools)
          ? tools
          : undefined

  const toolsLine =
    toolsList === undefined ? '' : `\ntools: ${toolsList.join(', ')}`
  const modelLine = model ? `\nmodel: ${model}` : ''
  const colorLine = color ? `\ncolor: ${color}` : ''

  return `---\nname: ${agentType}\ndescription: ${desc}${toolsLine}${modelLine}${colorLine}\n---\n\n${systemPrompt}\n`
}
