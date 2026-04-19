import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Box, Text, useInput } from 'ink'
import figures from 'figures'
import chalk from 'chalk'
import { join } from 'path'
import { spawn } from 'child_process'
import TextInput from '@components/TextInput'
import { Select, type OptionSubtree } from '@components/custom-select/select'
import { getTheme } from '@utils/theme'
import {
  clearAgentCache,
  getActiveAgents,
  getAllAgents,
  type AgentConfig,
  type AgentSource,
} from '@utils/agent/loader'
import { getModelManager } from '@utils/model'
import { getAvailableTools, type Tool } from './tooling'
import {
  deleteAgent,
  getPrimaryAgentFilePath,
  saveAgent,
  updateAgent,
} from './storage'
import {
  generateAgentWithClaude,
  validateAgentConfig,
  validateAgentType,
} from './generation'

type AgentSourceFilter =
  | 'all'
  | 'built-in'
  | 'userSettings'
  | 'projectSettings'
  | 'policySettings'
  | 'flagSettings'
  | 'plugin'

type AgentWithOverride = AgentConfig & { overriddenBy?: AgentSource }

const DEFAULT_AGENT_MODEL = 'sonnet'
const COLOR_OPTIONS = [
  'automatic',
  'red',
  'blue',
  'green',
  'yellow',
  'purple',
  'orange',
  'pink',
  'cyan',
] as const
type AgentColor = (typeof COLOR_OPTIONS)[number]

function openInEditor(filePath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const platform = process.platform
    let command: string
    let args: string[]

    switch (platform) {
      case 'darwin':
        command = 'open'
        args = [filePath]
        break
      case 'win32':
        command = 'cmd'
        args = ['/c', 'start', '', filePath]
        break
      default:
        command = 'xdg-open'
        args = [filePath]
        break
    }

    const child = spawn(command, args, { detached: true, stdio: 'ignore' })
    child.unref()
    child.on('error', err => reject(err))
    child.on('exit', code =>
      code === 0 ? resolve() : reject(new Error(`Editor exited with ${code}`)),
    )
  })
}

function titleForSource(source: AgentSourceFilter): string {
  switch (source) {
    case 'all':
      return 'Agents'
    case 'built-in':
      return 'Built-in agents'
    case 'plugin':
      return 'Plugin agents'
    case 'userSettings':
      return 'User agents'
    case 'projectSettings':
      return 'Project agents'
    case 'policySettings':
      return 'Managed agents'
    case 'flagSettings':
      return 'CLI arg agents'
    default:
      return 'Agents'
  }
}

function formatModelShort(model: string | undefined): string {
  const value = model || DEFAULT_AGENT_MODEL
  return value === 'inherit' ? 'inherit' : value
}

function formatModelLong(model: string | undefined): string {
  if (!model) return 'Sonnet (default)'
  if (model === 'inherit') return 'Inherit from parent'
  if (model === 'sonnet' || model === 'opus' || model === 'haiku') {
    return model.charAt(0).toUpperCase() + model.slice(1)
  }
  return model
}

function getToolNameFromSpec(spec: string): string {
  const trimmed = spec.trim()
  if (!trimmed) return trimmed
  const match = trimmed.match(/^([^(]+)\(([^)]+)\)$/)
  if (!match) return trimmed
  const toolName = match[1]?.trim()
  return toolName || trimmed
}

function parseMcpToolName(
  name: string,
): { serverName: string; toolName: string } | null {
  if (!name.startsWith('mcp__')) return null
  const parts = name.split('__')
  if (parts.length < 3) return null
  return { serverName: parts[1] || 'unknown', toolName: parts.slice(2).join('__') }
}

function toSelectableToolNames(toolSpecs: string[] | '*'): string[] | undefined {
  if (toolSpecs === '*') return undefined
  const names = toolSpecs.map(getToolNameFromSpec).filter(Boolean)
  if (names.includes('*')) return undefined
  return names
}

function panelBorderColor(kind: 'suggestion' | 'error'): string {
  const theme = getTheme()
  return kind === 'error' ? theme.error : theme.suggestion
}

function Panel(props: {
  title: string
  subtitle?: string
  borderColor?: string
  titleColor?: string
  children?: React.ReactNode
}) {
  const theme = getTheme()
  return (
    <Box
      borderStyle="round"
      borderColor={props.borderColor ?? theme.suggestion}
      flexDirection="column"
    >
      <Box flexDirection="column" paddingX={1}>
        <Text bold color={props.titleColor ?? theme.text}>
          {props.title}
        </Text>
        {props.subtitle ? <Text dimColor>{props.subtitle}</Text> : null}
      </Box>
      <Box paddingX={1} flexDirection="column">
        {props.children}
      </Box>
    </Box>
  )
}

function Instructions({
  instructions = 'Press ↑↓ to navigate · Enter to select · Esc to go back',
}: {
  instructions?: string
}) {
  return (
    <Box marginLeft={3}>
      <Text dimColor>{instructions}</Text>
    </Box>
  )
}

function computeOverrides(args: {
  allAgents: AgentConfig[]
  activeAgents: AgentConfig[]
}): AgentWithOverride[] {
  const activeByType = new Map<string, AgentConfig>()
  for (const agent of args.activeAgents) activeByType.set(agent.agentType, agent)
  return args.allAgents.map(agent => {
    const active = activeByType.get(agent.agentType)
    const overriddenBy =
      active && active.source !== agent.source ? active.source : undefined
    return { ...agent, ...(overriddenBy ? { overriddenBy } : {}) }
  })
}

function AgentsListView(props: {
  source: AgentSourceFilter
  agents: AgentWithOverride[]
  changes: string[]
  onCreateNew?: () => void
  onSelect: (agent: AgentWithOverride) => void
  onBack: () => void
}) {
  const theme = getTheme()

  const selectableAgents = useMemo(() => {
    const nonBuiltIn = props.agents.filter(a => a.source !== 'built-in')
    if (props.source === 'all') {
      return [
        ...nonBuiltIn.filter(a => a.source === 'userSettings'),
        ...nonBuiltIn.filter(a => a.source === 'projectSettings'),
        ...nonBuiltIn.filter(a => a.source === 'policySettings'),
      ]
    }
    return nonBuiltIn
  }, [props.agents, props.source])

  const [selectedAgent, setSelectedAgent] = useState<AgentWithOverride | null>(
    null,
  )
  const [onCreateOption, setOnCreateOption] = useState(true)

  useEffect(() => {
    if (props.onCreateNew) {
      setOnCreateOption(true)
      setSelectedAgent(null)
      return
    }
    if (!selectedAgent && selectableAgents.length > 0) {
      setSelectedAgent(selectableAgents[0] ?? null)
    }
  }, [props.onCreateNew, selectableAgents, selectedAgent])

  useInput((_input, key) => {
    if (key.escape) {
      props.onBack()
      return
    }

    if (key.return) {
      if (onCreateOption && props.onCreateNew) {
        props.onCreateNew()
        return
      }
      if (selectedAgent) props.onSelect(selectedAgent)
      return
    }

    if (!key.upArrow && !key.downArrow) return

    const hasCreate = Boolean(props.onCreateNew)
    const navigableCount = selectableAgents.length + (hasCreate ? 1 : 0)
    if (navigableCount === 0) return

    const currentIndex = (() => {
      if (hasCreate && onCreateOption) return 0
      if (!selectedAgent) return hasCreate ? 0 : 0
      const idx = selectableAgents.findIndex(
        a => a.agentType === selectedAgent.agentType && a.source === selectedAgent.source,
      )
      if (idx < 0) return hasCreate ? 0 : 0
      return hasCreate ? idx + 1 : idx
    })()

    const nextIndex = key.upArrow
      ? currentIndex === 0
        ? navigableCount - 1
        : currentIndex - 1
      : currentIndex === navigableCount - 1
        ? 0
        : currentIndex + 1

    if (hasCreate && nextIndex === 0) {
      setOnCreateOption(true)
      setSelectedAgent(null)
      return
    }

    const agentIndex = hasCreate ? nextIndex - 1 : nextIndex
    const nextAgent = selectableAgents[agentIndex]
    if (nextAgent) {
      setOnCreateOption(false)
      setSelectedAgent(nextAgent)
    }
  })

  const renderCreateNew = () => (
    <Box>
      <Text color={onCreateOption ? theme.suggestion : undefined}>
        {onCreateOption ? `${figures.pointer} ` : '  '}
      </Text>
      <Text color={onCreateOption ? theme.suggestion : undefined}>
        Create new agent
      </Text>
    </Box>
  )

  const renderAgentRow = (agent: AgentWithOverride) => {
    const isBuiltIn = agent.source === 'built-in'
    const isSelected =
      !isBuiltIn &&
      !onCreateOption &&
      selectedAgent?.agentType === agent.agentType &&
      selectedAgent?.source === agent.source

    const dimmed = Boolean(isBuiltIn || agent.overriddenBy)
    const rowColor = isSelected ? theme.suggestion : undefined
    const pointer = isBuiltIn ? '' : isSelected ? `${figures.pointer} ` : '  '

    return (
      <Box key={`${agent.agentType}-${agent.source}`} flexDirection="row">
        <Text dimColor={dimmed && !isSelected} color={rowColor}>
          {pointer}
        </Text>
        <Text dimColor={dimmed && !isSelected} color={rowColor}>
          {agent.agentType}
        </Text>
        <Text dimColor color={rowColor}>
          {' · '}
          {formatModelShort(agent.model)}
        </Text>
        {agent.overriddenBy ? (
          <Text dimColor={!isSelected} color={isSelected ? theme.warning : undefined}>
            {' '}
            {figures.warning} overridden by {agent.overriddenBy}
          </Text>
        ) : null}
      </Box>
    )
  }

  const group = (label: string, agents: AgentWithOverride[]) => {
    if (agents.length === 0) return null
    const baseDir = agents[0]?.baseDir
    return (
      <Box flexDirection="column" marginBottom={1}>
        <Box paddingLeft={2}>
          <Text bold dimColor>
            {label}
          </Text>
          {baseDir ? (
            <Text dimColor>
              {' '}
              ({baseDir})
            </Text>
          ) : null}
        </Box>
        {agents.map(renderAgentRow)}
      </Box>
    )
  }

  const builtInSection = (label = 'Built-in (always available):') => {
    const builtIn = props.agents.filter(a => a.source === 'built-in')
    if (builtIn.length === 0) return null
    return (
      <Box flexDirection="column" marginBottom={1} paddingLeft={2}>
        <Text bold dimColor>
          {label}
        </Text>
        {builtIn.map(renderAgentRow)}
      </Box>
    )
  }

  const notOverriddenCount = props.agents.filter(a => !a.overriddenBy).length
  const title = titleForSource(props.source)

  if (
    props.agents.length === 0 ||
    (props.source !== 'built-in' && !props.agents.some(a => a.source !== 'built-in'))
  ) {
    return (
      <>
        <Panel title={title} subtitle="No agents found">
          {props.onCreateNew ? <Box marginY={1}>{renderCreateNew()}</Box> : null}
          <Text dimColor>
            No agents found. Create specialized subagents that Claude can delegate to.
          </Text>
          <Text dimColor>
            Each subagent has its own context window, custom system prompt, and specific tools.
          </Text>
          <Text dimColor>
            Try creating: Code Reviewer, Code Simplifier, Security Reviewer, Tech Lead, or UX Reviewer.
          </Text>
          {props.source !== 'built-in' && props.agents.some(a => a.source === 'built-in') ? (
            <>
              <Box marginTop={1}>
                <Text dimColor>{'─'.repeat(40)}</Text>
              </Box>
              {builtInSection()}
            </>
          ) : null}
        </Panel>
        <Instructions />
      </>
    )
  }

  return (
    <>
      <Panel
        title={title}
        subtitle={`${notOverriddenCount} agents`}
      >
        {props.changes.length > 0 ? (
          <Box marginTop={1}>
            <Text dimColor>{props.changes[props.changes.length - 1]}</Text>
          </Box>
        ) : null}

        <Box flexDirection="column" marginTop={1}>
          {props.onCreateNew ? (
            <Box marginBottom={1}>{renderCreateNew()}</Box>
          ) : null}

          {props.source === 'all' ? (
            <>
              {group(
                'User agents',
                props.agents.filter(a => a.source === 'userSettings'),
              )}
              {group(
                'Project agents',
                props.agents.filter(a => a.source === 'projectSettings'),
              )}
              {group(
                'Managed agents',
                props.agents.filter(a => a.source === 'policySettings'),
              )}
              {group(
                'Plugin agents',
                props.agents.filter(a => a.source === 'plugin'),
              )}
              {group(
                'CLI arg agents',
                props.agents.filter(a => a.source === 'flagSettings'),
              )}
              {builtInSection('Built-in agents (always available)')}
            </>
          ) : props.source === 'built-in' ? (
            <>
              <Text dimColor italic>
                Built-in agents are provided by default and cannot be modified.
              </Text>
              <Box marginTop={1} flexDirection="column">
                {props.agents.map(renderAgentRow)}
              </Box>
            </>
          ) : (
            <Box flexDirection="column">
              {props.agents.filter(a => a.source !== 'built-in').map(renderAgentRow)}
            </Box>
          )}
        </Box>
      </Panel>
      <Instructions />
    </>
  )
}

type WizardLocation = 'projectSettings' | 'userSettings'
type WizardMethod = 'generate' | 'manual'

type WizardFinalAgent = {
  agentType: string
  whenToUse: string
  systemPrompt: string
  tools: string[] | undefined
  model: string
  color?: string
  source: WizardLocation
}

type WizardData = {
  location?: WizardLocation
  method?: WizardMethod
  generationPrompt?: string
  agentType?: string
  whenToUse?: string
  systemPrompt?: string
  selectedTools?: string[] | undefined
  selectedModel?: string
  selectedColor?: string
  wasGenerated?: boolean
  isGenerating?: boolean
  finalAgent?: WizardFinalAgent
}

function wizardLocationToStorageLocation(location: WizardLocation): 'project' | 'user' {
  return location === 'projectSettings' ? 'project' : 'user'
}

function modelOptions(): (OptionSubtree | { label: string; value: string })[] {
  const profiles = (() => {
    try {
      return getModelManager().getActiveModelProfiles() as Array<{
        name: string
        modelName: string
        provider?: string
      }>
    } catch {
      return []
    }
  })()

  const base: Array<{ label: string; value: string }> = [
    { value: 'sonnet', label: 'Task (alias: sonnet)' },
    { value: 'opus', label: 'Main (alias: opus)' },
    { value: 'haiku', label: 'Quick (alias: haiku)' },
    { value: 'inherit', label: 'Inherit from parent' },
  ]

  const extras: Array<{ label: string; value: string }> = []
  for (const profile of profiles) {
    if (!profile?.name) continue
    const value = profile.name
    if (base.some(o => o.value === value)) continue
    extras.push({
      value,
      label:
        profile.provider && profile.modelName
          ? `${profile.name} (${profile.provider}:${profile.modelName})`
          : profile.name,
    })
  }

  if (extras.length === 0) return base

  return [
    { header: 'Compatibility aliases', options: base },
    { header: 'Model profiles', options: extras.sort((a, b) => a.label.localeCompare(b.label)) },
  ]
}

function Wizard(props: {
  steps: Array<(ctx: WizardContextValue) => React.ReactNode>
  initialData?: WizardData
  onCancel: () => void
  onDone: (data: WizardData) => void
}) {
  const [stepIndex, setStepIndex] = useState(0)
  const [data, setData] = useState<WizardData>(props.initialData ?? {})
  const [history, setHistory] = useState<number[]>([])

  const goNext = useCallback(() => {
    setHistory(prev => [...prev, stepIndex])
    setStepIndex(prev => Math.min(prev + 1, props.steps.length - 1))
  }, [props.steps.length, stepIndex])

  const goBack = useCallback(() => {
    setHistory(prev => {
      if (prev.length === 0) {
        props.onCancel()
        return prev
      }
      const next = [...prev]
      const last = next.pop()
      if (typeof last === 'number') setStepIndex(last)
      return next
    })
  }, [props.onCancel])

  const goToStep = useCallback(
    (index: number) => {
      setHistory(prev => [...prev, stepIndex])
      setStepIndex(() => Math.max(0, Math.min(index, props.steps.length - 1)))
    },
    [props.steps.length, stepIndex],
  )

  const updateWizardData = useCallback((patch: Partial<WizardData>) => {
    setData(prev => ({ ...prev, ...patch }))
  }, [])

  const cancel = useCallback(() => props.onCancel(), [props.onCancel])
  const done = useCallback(() => props.onDone(data), [props, data])

  const ctx: WizardContextValue = useMemo(
    () => ({
      stepIndex,
      totalSteps: props.steps.length,
      wizardData: data,
      updateWizardData,
      goNext,
      goBack,
      goToStep,
      cancel,
      done,
    }),
    [
      data,
      done,
      goBack,
      goNext,
      goToStep,
      props.steps.length,
      stepIndex,
      updateWizardData,
      cancel,
    ],
  )

  return <>{props.steps[stepIndex]?.(ctx) ?? null}</>
}

type WizardContextValue = {
  stepIndex: number
  totalSteps: number
  wizardData: WizardData
  updateWizardData: (patch: Partial<WizardData>) => void
  goNext: () => void
  goBack: () => void
  goToStep: (index: number) => void
  cancel: () => void
  done: () => void
}

function WizardPanel(props: {
  subtitle: string
  footerText?: string
  children?: React.ReactNode
}) {
  return (
    <>
      <Panel title="Create new agent" subtitle={props.subtitle}>
        {props.children}
      </Panel>
      <Instructions instructions={props.footerText} />
    </>
  )
}

function StepChooseLocation({ ctx }: { ctx: WizardContextValue }) {
  useInput((_input, key) => {
    if (key.escape) ctx.cancel()
  })

  return (
    <WizardPanel subtitle="Choose location" footerText="Press ↑↓ to navigate · Enter to select · Esc to cancel">
      <Box marginTop={1}>
        <Select
          options={[
            { label: 'Project (.claude/agents/)', value: 'projectSettings' },
            { label: 'Personal (~/.claude/agents/)', value: 'userSettings' },
          ]}
          onChange={value => {
            const location =
              value === 'projectSettings' ? 'projectSettings' : 'userSettings'
            ctx.updateWizardData({ location })
            ctx.goNext()
          }}
        />
      </Box>
    </WizardPanel>
  )
}

function StepChooseMethod({ ctx }: { ctx: WizardContextValue }) {
  useInput((_input, key) => {
    if (key.escape) ctx.goBack()
  })

  return (
    <WizardPanel subtitle="Creation method">
      <Box marginTop={1}>
        <Select
          options={[
            { label: 'Generate with Claude (recommended)', value: 'generate' },
            { label: 'Manual configuration', value: 'manual' },
          ]}
          onChange={value => {
            const method: WizardMethod =
              value === 'manual' ? 'manual' : 'generate'
            ctx.updateWizardData({ method, wasGenerated: method === 'generate' })
            if (method === 'generate') ctx.goNext()
            else ctx.goToStep(3)
          }}
        />
      </Box>
    </WizardPanel>
  )
}

function StepGenerationPrompt(props: {
  ctx: WizardContextValue
  existingAgents: AgentConfig[]
}) {
  const { ctx } = props
  const [value, setValue] = useState(ctx.wizardData.generationPrompt ?? '')
  const [cursorOffset, setCursorOffset] = useState(value.length)
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const columns = Math.min(80, process.stdout.columns ?? 80)

  useInput((_input, key) => {
    if (!key.escape) return
    if (isGenerating && abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
      setIsGenerating(false)
      setError('Generation cancelled')
      return
    }
    if (!isGenerating) {
      ctx.updateWizardData({
        generationPrompt: '',
        agentType: '',
        systemPrompt: '',
        whenToUse: '',
        wasGenerated: false,
      })
      setValue('')
      setCursorOffset(0)
      setError(null)
      ctx.goBack()
    }
  })

  const onSubmit = async () => {
    const trimmed = value.trim()
    if (!trimmed) {
      setError('Please describe what the agent should do')
      return
    }

    setError(null)
    setIsGenerating(true)
    ctx.updateWizardData({ generationPrompt: trimmed, isGenerating: true })

    const abort = new AbortController()
    abortRef.current = abort

    try {
      const existing = props.existingAgents.map(a => a.agentType)
      const generated = await generateAgentWithClaude(trimmed)
      if (existing.includes(generated.identifier)) {
        throw new Error(
          `Agent identifier already exists: ${generated.identifier}. Please try again.`,
        )
      }

      ctx.updateWizardData({
        agentType: generated.identifier,
        whenToUse: generated.whenToUse,
        systemPrompt: generated.systemPrompt,
        wasGenerated: true,
        isGenerating: false,
      })
      setIsGenerating(false)
      abortRef.current = null
      ctx.goToStep(6)
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setError(message || 'Failed to generate agent')
      setIsGenerating(false)
      ctx.updateWizardData({ isGenerating: false })
      abortRef.current = null
    }
  }

  return (
    <WizardPanel subtitle="Describe the agent you want">
      <Box flexDirection="column" marginTop={1} gap={1}>
        <Text>What should this agent do?</Text>
        <Text dimColor>
          Describe a role like “code reviewer”, “security auditor”, or “tech lead”.
        </Text>
        <TextInput
          value={value}
          onChange={setValue}
          columns={columns}
          multiline
          onSubmit={onSubmit}
          cursorOffset={cursorOffset}
          onChangeCursorOffset={setCursorOffset}
        />
        {error ? <Text color={themeColor('error')}>{error}</Text> : null}
        {isGenerating ? <Text dimColor>Generating…</Text> : null}
      </Box>
    </WizardPanel>
  )
}

function themeColor(kind: 'error' | 'warning' | 'success' | 'suggestion'): string {
  const theme = getTheme()
  switch (kind) {
    case 'error':
      return theme.error
    case 'warning':
      return theme.warning
    case 'success':
      return theme.success
    case 'suggestion':
    default:
      return theme.suggestion
  }
}

function StepAgentType(props: { ctx: WizardContextValue; existingAgents: AgentConfig[] }) {
  const { ctx } = props
  const [value, setValue] = useState(ctx.wizardData.agentType ?? '')
  const [cursorOffset, setCursorOffset] = useState(value.length)
  const [error, setError] = useState<string | null>(null)
  const columns = 60

  useInput((_input, key) => {
    if (key.escape) ctx.goBack()
  })

  const onSubmit = (next: string) => {
    const trimmed = next.trim()
    const validation = validateAgentType(trimmed, props.existingAgents)
    if (!validation.isValid) {
      setError(validation.errors[0] ?? 'Invalid agent type')
      return
    }
    setError(null)
    ctx.updateWizardData({ agentType: trimmed })
    ctx.goNext()
  }

  return (
    <WizardPanel
      subtitle="Agent type (identifier)"
      footerText="Press Enter to continue · Esc to go back"
    >
      <Box flexDirection="column" marginTop={1} gap={1}>
        <Text>Enter a unique identifier for your agent:</Text>
        <TextInput
          value={value}
          onChange={setValue}
          columns={columns}
          onSubmit={onSubmit}
          cursorOffset={cursorOffset}
          onChangeCursorOffset={setCursorOffset}
        />
        <Text dimColor>e.g., code-reviewer, tech-lead, etc</Text>
        {error ? <Text color={themeColor('error')}>{error}</Text> : null}
      </Box>
    </WizardPanel>
  )
}

function StepSystemPrompt({ ctx }: { ctx: WizardContextValue }) {
  const [value, setValue] = useState(ctx.wizardData.systemPrompt ?? '')
  const [cursorOffset, setCursorOffset] = useState(value.length)
  const [error, setError] = useState<string | null>(null)
  const columns = Math.min(80, process.stdout.columns ?? 80)

  useInput((_input, key) => {
    if (key.escape) ctx.goBack()
  })

  const onSubmit = (next: string) => {
    const trimmed = next.trim()
    if (!trimmed) {
      setError('System prompt is required')
      return
    }
    setError(null)
    ctx.updateWizardData({ systemPrompt: trimmed })
    ctx.goNext()
  }

  return (
    <WizardPanel
      subtitle="System prompt"
      footerText="Press Enter to continue · Esc to go back"
    >
      <Box flexDirection="column" marginTop={1} gap={1}>
        <Text>Enter the system prompt for your agent:</Text>
        <Text dimColor>Be comprehensive for best results</Text>
        <TextInput
          value={value}
          onChange={setValue}
          columns={columns}
          multiline
          onSubmit={onSubmit}
          cursorOffset={cursorOffset}
          onChangeCursorOffset={setCursorOffset}
        />
        {error ? <Text color={themeColor('error')}>{error}</Text> : null}
      </Box>
    </WizardPanel>
  )
}

function StepDescription({ ctx }: { ctx: WizardContextValue }) {
  const [value, setValue] = useState(ctx.wizardData.whenToUse ?? '')
  const [cursorOffset, setCursorOffset] = useState(value.length)
  const [error, setError] = useState<string | null>(null)
  const columns = Math.min(80, process.stdout.columns ?? 80)

  useInput((_input, key) => {
    if (key.escape) ctx.goBack()
  })

  const onSubmit = (next: string) => {
    const trimmed = next.trim()
    if (!trimmed) {
      setError('Description is required')
      return
    }
    setError(null)
    ctx.updateWizardData({ whenToUse: trimmed })
    ctx.goNext()
  }

  return (
    <WizardPanel
      subtitle="Description (tell Claude when to use this agent)"
      footerText="Press Enter to continue · Esc to go back"
    >
      <Box flexDirection="column" marginTop={1} gap={1}>
        <Text>When should Claude use this agent?</Text>
        <TextInput
          value={value}
          onChange={setValue}
          columns={columns}
          multiline
          onSubmit={onSubmit}
          cursorOffset={cursorOffset}
          onChangeCursorOffset={setCursorOffset}
        />
        {error ? <Text color={themeColor('error')}>{error}</Text> : null}
      </Box>
    </WizardPanel>
  )
}

function ToolPicker(props: {
  tools: Tool[]
  initialTools: string[] | undefined
  onComplete: (tools: string[] | undefined) => void
  onCancel: () => void
}) {
  const normalizedTools = useMemo(() => {
    const unique = new Map<string, Tool>()
    for (const tool of props.tools) {
      if (!tool?.name) continue
      unique.set(tool.name, tool)
    }
    return Array.from(unique.values()).sort((a, b) => a.name.localeCompare(b.name))
  }, [props.tools])

  const allToolNames = useMemo(
    () => normalizedTools.map(t => t.name),
    [normalizedTools],
  )

  const initialSelectedNames = useMemo(() => {
    if (!props.initialTools) return allToolNames
    if (props.initialTools.includes('*')) return allToolNames
    const available = new Set(allToolNames)
    return props.initialTools.filter(t => available.has(t))
  }, [props.initialTools, allToolNames])

  const [selected, setSelected] = useState<string[]>(initialSelectedNames)
  const [cursorIndex, setCursorIndex] = useState(0)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const selectedSet = useMemo(() => new Set(selected), [selected])
  const isAllSelected = selected.length === allToolNames.length && allToolNames.length > 0

  const toggleOne = (name: string) => {
    setSelected(prev =>
      prev.includes(name) ? prev.filter(x => x !== name) : [...prev, name],
    )
  }

  const toggleMany = (names: string[], enable: boolean) => {
    setSelected(prev => {
      if (enable) {
        const missing = names.filter(n => !prev.includes(n))
        return [...prev, ...missing]
      }
      return prev.filter(n => !names.includes(n))
    })
  }

  const complete = () => {
    const next =
      selected.length === allToolNames.length &&
      allToolNames.every(n => selected.includes(n))
        ? undefined
        : selected
    props.onComplete(next)
  }

  const categorized = useMemo(() => {
    const readOnly = new Set(['Read', 'Glob', 'Grep', 'LS'])
    const edit = new Set(['Edit', 'MultiEdit', 'Write', 'NotebookEdit'])
    const execution = new Set(['Bash', 'BashOutput', 'KillBash'])

    const buckets: Record<
      'readOnly' | 'edit' | 'execution' | 'mcp' | 'other',
      string[]
    > = { readOnly: [], edit: [], execution: [], mcp: [], other: [] }

    for (const tool of normalizedTools) {
      const name = tool.name
      if (name.startsWith('mcp__')) buckets.mcp.push(name)
      else if (readOnly.has(name)) buckets.readOnly.push(name)
      else if (edit.has(name)) buckets.edit.push(name)
      else if (execution.has(name)) buckets.execution.push(name)
      else buckets.other.push(name)
    }

    return buckets
  }, [normalizedTools])

  const mcpServers = useMemo(() => {
    const byServer = new Map<string, string[]>()
    for (const name of categorized.mcp) {
      const parsed = parseMcpToolName(name)
      if (!parsed) continue
      const list = byServer.get(parsed.serverName) ?? []
      list.push(name)
      byServer.set(parsed.serverName, list)
    }
    return Array.from(byServer.entries())
      .map(([serverName, toolNames]) => ({ serverName, toolNames }))
      .sort((a, b) => a.serverName.localeCompare(b.serverName))
  }, [categorized.mcp])

  type Item = {
    id: string
    label: string
    isHeader?: boolean
    isToggle?: boolean
    action: () => void
  }

  const items: Item[] = useMemo(() => {
    const out: Item[] = []

    out.push({ id: 'continue', label: '[ Continue ]', action: complete })
    out.push({
      id: 'bucket-all',
      label: `${isAllSelected ? figures.checkboxOn : figures.checkboxOff} All tools`,
      action: () => toggleMany(allToolNames, !isAllSelected),
    })

    const bucketDefs: Array<{
      id: string
      label: string
      names: string[]
    }> = [
      { id: 'bucket-readonly', label: 'Read-only tools', names: categorized.readOnly },
      { id: 'bucket-edit', label: 'Edit tools', names: categorized.edit },
      { id: 'bucket-execution', label: 'Execution tools', names: categorized.execution },
      { id: 'bucket-mcp', label: 'MCP tools', names: categorized.mcp },
      { id: 'bucket-other', label: 'Other tools', names: categorized.other },
    ]

    for (const bucket of bucketDefs) {
      if (bucket.names.length === 0) continue
      const allInBucket = bucket.names.every(n => selectedSet.has(n))
      out.push({
        id: bucket.id,
        label: `${allInBucket ? figures.checkboxOn : figures.checkboxOff} ${bucket.label}`,
        action: () => toggleMany(bucket.names, !allInBucket),
      })
    }

    out.push({
      id: 'toggle-advanced',
      label: showAdvanced ? 'Hide advanced options' : 'Show advanced options',
      isToggle: true,
      action: () => setShowAdvanced(prev => !prev),
    })

    if (!showAdvanced) return out

    if (mcpServers.length > 0) {
      out.push({ id: 'mcp-servers-header', label: 'MCP Servers:', isHeader: true, action: () => {} })
      for (const server of mcpServers) {
        const allServer = server.toolNames.every(n => selectedSet.has(n))
        out.push({
          id: `mcp-server-${server.serverName}`,
          label: `${allServer ? figures.checkboxOn : figures.checkboxOff} ${server.serverName} (${server.toolNames.length} tool${server.toolNames.length === 1 ? '' : 's'})`,
          action: () => toggleMany(server.toolNames, !allServer),
        })
      }
    }

    out.push({ id: 'tools-header', label: 'Individual Tools:', isHeader: true, action: () => {} })
    for (const name of allToolNames) {
      let labelName = name
      const parsed = parseMcpToolName(name)
      if (parsed) labelName = `${parsed.toolName} (${parsed.serverName})`
      out.push({
        id: `tool-${name}`,
        label: `${selectedSet.has(name) ? figures.checkboxOn : figures.checkboxOff} ${labelName}`,
        action: () => toggleOne(name),
      })
    }

    return out
  }, [
    allToolNames,
    categorized,
    complete,
    isAllSelected,
    mcpServers,
    selectedSet,
    showAdvanced,
  ])

  useInput((_input, key) => {
    if (key.escape) {
      props.onCancel()
      return
    }

    if (key.return) {
      const item = items[cursorIndex]
      if (item && !item.isHeader) item.action()
      return
    }

    if (key.upArrow) {
      let next = cursorIndex - 1
      while (next > 0 && items[next]?.isHeader) next--
      setCursorIndex(Math.max(0, next))
      return
    }

    if (key.downArrow) {
      let next = cursorIndex + 1
      while (next < items.length - 1 && items[next]?.isHeader) next++
      setCursorIndex(Math.min(items.length - 1, next))
      return
    }
  })

  return (
    <Box flexDirection="column" marginTop={1}>
      <Text color={cursorIndex === 0 ? themeColor('suggestion') : undefined} bold={cursorIndex === 0}>
        {cursorIndex === 0 ? `${figures.pointer} ` : '  '}[ Continue ]
      </Text>
      <Text dimColor>{'─'.repeat(40)}</Text>
      {items.slice(1).map((item, idx) => {
        const index = idx + 1
        const focused = index === cursorIndex
        const prefix = item.isHeader ? '' : focused ? `${figures.pointer} ` : '  '
        return (
          <React.Fragment key={item.id}>
            {item.isToggle ? <Text dimColor>{'─'.repeat(40)}</Text> : null}
            <Text
              dimColor={item.isHeader}
              color={!item.isHeader && focused ? themeColor('suggestion') : undefined}
              bold={item.isToggle && focused}
            >
              {item.isToggle ? `${prefix}[ ${item.label} ]` : `${prefix}${item.label}`}
            </Text>
          </React.Fragment>
        )
      })}
      <Box marginTop={1} flexDirection="column">
        <Text dimColor>
          {isAllSelected
            ? 'All tools selected'
            : `${selectedSet.size} of ${allToolNames.length} tools selected`}
        </Text>
      </Box>
    </Box>
  )
}

function StepSelectTools(props: {
  ctx: WizardContextValue
  tools: Tool[]
}) {
  const { ctx } = props
  const initialTools = ctx.wizardData.selectedTools
  return (
    <>
      <Panel title="Create new agent" subtitle="Select tools">
        <ToolPicker
          tools={props.tools}
          initialTools={initialTools}
          onComplete={selected => {
            ctx.updateWizardData({ selectedTools: selected })
            ctx.goNext()
          }}
          onCancel={ctx.goBack}
        />
      </Panel>
      <Instructions instructions="Press Enter to toggle selection · ↑↓ Navigate · Esc to go back" />
    </>
  )
}

function StepSelectModel({ ctx }: { ctx: WizardContextValue }) {
  useInput((_input, key) => {
    if (key.escape) ctx.goBack()
  })

  const options = modelOptions()
  const defaultValue = ctx.wizardData.selectedModel ?? DEFAULT_AGENT_MODEL

  return (
    <WizardPanel subtitle="Select model" footerText="Press ↑↓ to navigate · Enter to select · Esc to go back">
      <Box flexDirection="column" marginTop={1} gap={1}>
        <Text dimColor>
          Model determines the agent&apos;s reasoning capabilities and speed.
        </Text>
        <Select
          options={options as any}
          defaultValue={defaultValue}
          onChange={value => {
            ctx.updateWizardData({ selectedModel: value })
            ctx.goNext()
          }}
        />
      </Box>
    </WizardPanel>
  )
}

function ColorPicker(props: {
  agentName: string
  currentColor: AgentColor
  onConfirm: (color: AgentColor) => void
}) {
  const [index, setIndex] = useState(
    Math.max(0, COLOR_OPTIONS.findIndex(c => c === props.currentColor)),
  )

  useInput((_input, key) => {
    if (key.upArrow) setIndex(i => (i > 0 ? i - 1 : COLOR_OPTIONS.length - 1))
    else if (key.downArrow) setIndex(i => (i < COLOR_OPTIONS.length - 1 ? i + 1 : 0))
    else if (key.return) props.onConfirm(COLOR_OPTIONS[index] ?? 'automatic')
  })

  return (
    <Box flexDirection="column" gap={1}>
      {COLOR_OPTIONS.map((color, i) => {
        const focused = i === index
        const prefix = focused ? figures.pointer : ' '
        const label =
          color === 'automatic'
            ? 'Automatic color'
            : color.charAt(0).toUpperCase() + color.slice(1)
        return (
          <React.Fragment key={color}>
            <Text
              color={focused ? themeColor('suggestion') : undefined}
              bold={focused}
            >
              {prefix} {label}
            </Text>
          </React.Fragment>
        )
      })}
    </Box>
  )
}

function StepChooseColor({ ctx }: { ctx: WizardContextValue }) {
  useInput((_input, key) => {
    if (key.escape) ctx.goBack()
  })

  const agentType = ctx.wizardData.agentType ?? 'agent'
  const onConfirm = (color: AgentColor) => {
    const selectedColor = color === 'automatic' ? undefined : color
    const finalAgent: WizardFinalAgent = {
      agentType: ctx.wizardData.agentType ?? agentType,
      whenToUse: ctx.wizardData.whenToUse ?? '',
      systemPrompt: ctx.wizardData.systemPrompt ?? '',
      tools: ctx.wizardData.selectedTools,
      model: ctx.wizardData.selectedModel ?? DEFAULT_AGENT_MODEL,
      ...(selectedColor ? { color: selectedColor } : {}),
      source: ctx.wizardData.location ?? 'projectSettings',
    }

    ctx.updateWizardData({
      selectedColor: selectedColor,
      finalAgent,
    })
    ctx.goNext()
  }

  return (
    <WizardPanel subtitle="Choose background color" footerText="Press ↑↓ to navigate · Enter to select · Esc to go back">
      <Box marginTop={1}>
        <ColorPicker agentName={agentType} currentColor="automatic" onConfirm={onConfirm} />
      </Box>
    </WizardPanel>
  )
}

function validateFinalAgent(args: {
  finalAgent: WizardFinalAgent
  tools: Tool[]
  existingAgents: AgentConfig[]
}): { errors: string[]; warnings: string[] } {
  const errors: string[] = []
  const warnings: string[] = []

  const typeValidation = validateAgentType(args.finalAgent.agentType, args.existingAgents)
  errors.push(...typeValidation.errors)
  warnings.push(...typeValidation.warnings)

  const configValidation = validateAgentConfig({
    agentType: args.finalAgent.agentType,
    whenToUse: args.finalAgent.whenToUse,
    systemPrompt: args.finalAgent.systemPrompt,
    selectedTools: args.finalAgent.tools ?? ['*'],
  })
  errors.push(...configValidation.errors)
  warnings.push(...configValidation.warnings)

  const availableToolNames = new Set(args.tools.map(t => t.name))
  const selectedTools = args.finalAgent.tools ?? undefined
  if (selectedTools && selectedTools.length > 0) {
    const unknown = selectedTools.filter(t => !availableToolNames.has(t))
    if (unknown.length > 0) warnings.push(`Unrecognized tools: ${unknown.join(', ')}`)
  }

  return { errors, warnings }
}

function StepConfirm(props: {
  ctx: WizardContextValue
  tools: Tool[]
  existingAgents: AgentConfig[]
  onSave: (finalAgent: WizardFinalAgent, openEditor: boolean) => Promise<void>
}) {
  const { ctx } = props
  const finalAgent = ctx.wizardData.finalAgent
  const [error, setError] = useState<string | null>(null)

  useInput((input, key) => {
    if (key.escape) ctx.goBack()
    else if (input === 'e') void doSave(true)
    else if (input === 's' || key.return) void doSave(false)
  })

  const toolSummary = (tools: string[] | undefined): string => {
    if (tools === undefined) return 'All tools'
    if (tools.length === 0) return 'None'
    if (tools.length === 1) return tools[0] || 'None'
    if (tools.length === 2) return tools.join(' and ')
    return `${tools.slice(0, -1).join(', ')}, and ${tools[tools.length - 1]}`
  }

  const doSave = async (openEditor: boolean) => {
    if (!finalAgent) return
    const { errors } = validateFinalAgent({
      finalAgent,
      tools: props.tools,
      existingAgents: props.existingAgents,
    })
    if (errors.length > 0) {
      setError(errors[0] ?? 'Invalid agent configuration')
      return
    }
    try {
      await props.onSave(finalAgent, openEditor)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  if (!finalAgent) return null

  const validation = validateFinalAgent({
    finalAgent,
    tools: props.tools,
    existingAgents: props.existingAgents,
  })

  const locationPath =
    finalAgent.source === 'projectSettings'
      ? getPrimaryAgentFilePath('project', finalAgent.agentType)
      : getPrimaryAgentFilePath('user', finalAgent.agentType)

  const truncate = (text: string) =>
    text.length > 240 ? `${text.slice(0, 240)}…` : text

  return (
    <WizardPanel
      subtitle="Confirm and save"
      footerText="Press s/Enter to save · e to edit in your editor · Esc to cancel"
    >
      <Box flexDirection="column" marginTop={1} gap={1}>
        <Text>
          <Text bold>Name</Text>: {finalAgent.agentType}
        </Text>
        <Text>
          <Text bold>Location</Text>: {locationPath}
        </Text>
        <Text>
          <Text bold>Tools</Text>: {toolSummary(finalAgent.tools)}
        </Text>
        <Text>
          <Text bold>Model</Text>: {formatModelLong(finalAgent.model)}
        </Text>

        <Box marginTop={1} flexDirection="column">
          <Text>
            <Text bold>Description</Text> (tells Claude when to use this agent):
          </Text>
          <Box marginLeft={2} marginTop={1}>
            <Text>{truncate(finalAgent.whenToUse)}</Text>
          </Box>
        </Box>

        <Box marginTop={1} flexDirection="column">
          <Text>
            <Text bold>System prompt</Text>:
          </Text>
          <Box marginLeft={2} marginTop={1}>
            <Text>{truncate(finalAgent.systemPrompt)}</Text>
          </Box>
        </Box>

        {validation.warnings.length > 0 ? (
          <Box marginTop={1} flexDirection="column">
            <Text color={themeColor('warning')}>Warnings:</Text>
            {validation.warnings.map((w, i) => (
              <React.Fragment key={i}>
                <Text dimColor>
                  {' '}
                  • {w}
                </Text>
              </React.Fragment>
            ))}
          </Box>
        ) : null}

        {validation.errors.length > 0 ? (
          <Box marginTop={1} flexDirection="column">
            <Text color={themeColor('error')}>Errors:</Text>
            {validation.errors.map((e, i) => (
              <React.Fragment key={i}>
                <Text color={themeColor('error')}>
                  {' '}
                  • {e}
                </Text>
              </React.Fragment>
            ))}
          </Box>
        ) : null}

        {error ? (
          <Box marginTop={1}>
            <Text color={themeColor('error')}>{error}</Text>
          </Box>
        ) : null}
      </Box>
    </WizardPanel>
  )
}

function CreateAgentWizard(props: {
  tools: Tool[]
  existingAgents: AgentConfig[]
  onComplete: (message: string) => void
  onCancel: () => void
}) {
  const steps = useMemo(() => {
    return [
      (ctx: WizardContextValue) => <StepChooseLocation ctx={ctx} />,
      (ctx: WizardContextValue) => <StepChooseMethod ctx={ctx} />,
      (ctx: WizardContextValue) => (
        <StepGenerationPrompt ctx={ctx} existingAgents={props.existingAgents} />
      ),
      (ctx: WizardContextValue) => (
        <StepAgentType ctx={ctx} existingAgents={props.existingAgents} />
      ),
      (ctx: WizardContextValue) => <StepSystemPrompt ctx={ctx} />,
      (ctx: WizardContextValue) => <StepDescription ctx={ctx} />,
      (ctx: WizardContextValue) => (
        <StepSelectTools ctx={ctx} tools={props.tools} />
      ),
      (ctx: WizardContextValue) => <StepSelectModel ctx={ctx} />,
      (ctx: WizardContextValue) => <StepChooseColor ctx={ctx} />,
      (ctx: WizardContextValue) => (
        <StepConfirm
          ctx={ctx}
          tools={props.tools}
          existingAgents={props.existingAgents}
          onSave={async (finalAgent, openEditor) => {
            const location = wizardLocationToStorageLocation(finalAgent.source)
            const tools = finalAgent.tools ?? ['*']
            await saveAgent(
              location,
              finalAgent.agentType,
              finalAgent.whenToUse,
              tools,
              finalAgent.systemPrompt,
              finalAgent.model,
              finalAgent.color,
              true,
            )

            if (openEditor) {
              const path = getPrimaryAgentFilePath(location, finalAgent.agentType)
              await openInEditor(path)
              props.onComplete(
                `Created agent: ${chalk.bold(finalAgent.agentType)} and opened in editor. If you made edits, restart to load the latest version.`,
              )
              return
            }

            props.onComplete(`Created agent: ${chalk.bold(finalAgent.agentType)}`)
          }}
        />
      ),
    ]
  }, [props])

  return (
    <Wizard
      steps={steps}
      onCancel={props.onCancel}
      onDone={() => {}}
    />
  )
}

function AgentMenu(props: {
  agent: AgentWithOverride
  onChoose: (value: 'view' | 'edit' | 'delete' | 'back') => void
  onCancel: () => void
}) {
  useInput((_input, key) => {
    if (key.escape) props.onCancel()
  })

  const isBuiltIn = props.agent.source === 'built-in'
  const options = [
    { label: 'View agent', value: 'view' },
    ...(isBuiltIn
      ? []
      : [
          { label: 'Edit agent', value: 'edit' },
          { label: 'Delete agent', value: 'delete' },
        ]),
    { label: 'Back', value: 'back' },
  ]

  return (
    <>
      <Panel title={props.agent.agentType}>
        <Box flexDirection="column" marginTop={1}>
          <Select
            options={options}
            onChange={value => props.onChoose(value as any)}
          />
        </Box>
      </Panel>
      <Instructions />
    </>
  )
}

function ViewAgent(props: {
  agent: AgentWithOverride
  tools: Tool[]
  onBack: () => void
}) {
  useInput((_input, key) => {
    if (key.escape || key.return) props.onBack()
  })

  const toolNames = new Set(props.tools.map(t => t.name))
  const parsedTools = (() => {
    const toolSpec = props.agent.tools
    if (toolSpec === '*') return { hasWildcard: true, valid: [], invalid: [] as string[] }
    if (!toolSpec || toolSpec.length === 0) return { hasWildcard: false, valid: [], invalid: [] as string[] }
    const names = toolSpec.map(getToolNameFromSpec).filter(Boolean)
    const valid: string[] = []
    const invalid: string[] = []
    for (const name of names) {
      if (name.includes('*') && Array.from(toolNames).some(t => t.startsWith(name.replace(/\*+$/, '')))) {
        valid.push(name)
        continue
      }
      if (toolNames.has(name)) valid.push(name)
      else invalid.push(name)
    }
    return { hasWildcard: false, valid, invalid }
  })()

  const sourceLine = (() => {
    if (props.agent.source === 'built-in') return 'Built-in'
    if (props.agent.source === 'plugin') return `Plugin: ${props.agent.baseDir ?? 'Unknown'}`
    const baseDir = props.agent.baseDir
    const file = `${props.agent.filename ?? props.agent.agentType}.md`
    if (props.agent.source === 'projectSettings') return join('.claude', 'agents', file)
    if (baseDir) return join(baseDir, file)
    return props.agent.source
  })()

  const toolsSummary = () => {
    if (parsedTools.hasWildcard) return 'All tools'
    if (!props.agent.tools || props.agent.tools === '*' || props.agent.tools.length === 0) return 'None'
    return (
      <>
        {parsedTools.valid.length > 0 ? parsedTools.valid.join(', ') : null}
        {parsedTools.invalid.length > 0 ? (
          <>
            <Text color={themeColor('warning')}>
              {' '}
              {figures.warning} Unrecognized: {parsedTools.invalid.join(', ')}
            </Text>
          </>
        ) : null}
      </>
    )
  }

  return (
    <>
      <Panel title={props.agent.agentType}>
        <Box flexDirection="column" gap={1}>
          <Text dimColor>{sourceLine}</Text>
          <Box flexDirection="column">
            <Text>
              <Text bold>Description</Text> (tells Claude when to use this agent):
            </Text>
            <Box marginLeft={2}>
              <Text>{props.agent.whenToUse}</Text>
            </Box>
          </Box>
          <Text>
            <Text bold>Tools</Text>: {toolsSummary()}
          </Text>
          <Text>
            <Text bold>Model</Text>: {formatModelLong(props.agent.model)}
          </Text>
          {props.agent.color ? (
            <Text>
              <Text bold>Color</Text>: {props.agent.color}
            </Text>
          ) : null}
          {props.agent.systemPrompt ? (
            <>
              <Text>
                <Text bold>System prompt</Text>:
              </Text>
              <Box marginLeft={2} marginRight={2}>
                <Text>{props.agent.systemPrompt}</Text>
              </Box>
            </>
          ) : null}
        </Box>
      </Panel>
      <Instructions instructions="Press Enter or Esc to go back" />
    </>
  )
}

function EditAgent(props: {
  agent: AgentWithOverride
  tools: Tool[]
  onSaved: (message: string) => void
  onBack: () => void
}) {
  const [mode, setMode] = useState<'menu' | 'edit-tools' | 'edit-model' | 'edit-color'>('menu')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const menuItems = useMemo(
    () => [
      { label: 'Open in editor', action: 'open' as const },
      { label: 'Edit tools', action: 'edit-tools' as const },
      { label: 'Edit model', action: 'edit-model' as const },
      { label: 'Edit color', action: 'edit-color' as const },
    ],
    [],
  )

  const doOpen = async () => {
    try {
      const location =
        props.agent.source === 'projectSettings'
          ? 'project'
          : props.agent.source === 'userSettings'
            ? 'user'
            : null
      if (!location) throw new Error(`Cannot open ${props.agent.source} agent in editor`)
      const filePath = getPrimaryAgentFilePath(location, props.agent.agentType)
      await openInEditor(filePath)
      props.onSaved(
        `Opened ${props.agent.agentType} in editor. If you made edits, restart to load the latest version.`,
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  const doUpdate = async (patch: { tools?: string[] | '*'; model?: string; color?: string }) => {
    try {
      await updateAgent(
        props.agent,
        props.agent.whenToUse,
        patch.tools ?? props.agent.tools,
        props.agent.systemPrompt,
        patch.color ?? props.agent.color,
        patch.model ?? props.agent.model,
      )
      props.onSaved(`Updated agent: ${chalk.bold(props.agent.agentType)}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  useInput((_input, key) => {
    if (key.escape) {
      setError(null)
      if (mode === 'menu') props.onBack()
      else setMode('menu')
    }

    if (mode !== 'menu') return

    if (key.upArrow) setSelectedIndex(i => Math.max(0, i - 1))
    else if (key.downArrow) setSelectedIndex(i => Math.min(menuItems.length - 1, i + 1))
    else if (key.return) {
      const item = menuItems[selectedIndex]
      if (!item) return
      if (item.action === 'open') void doOpen()
      else setMode(item.action)
    }
  })

  if (mode === 'edit-tools') {
    return (
      <>
        <Panel title={`Edit agent: ${props.agent.agentType}`}>
          <ToolPicker
            tools={props.tools}
            initialTools={toSelectableToolNames(props.agent.tools)}
            onComplete={selected => {
              const tools = selected === undefined ? '*' : selected
              void doUpdate({ tools })
              setMode('menu')
            }}
            onCancel={() => setMode('menu')}
          />
          {error ? (
            <Box marginTop={1}>
              <Text color={themeColor('error')}>{error}</Text>
            </Box>
          ) : null}
        </Panel>
        <Instructions instructions="Press Enter to toggle selection · ↑↓ Navigate · Esc to go back" />
      </>
    )
  }

  if (mode === 'edit-model') {
    useInput((_input, key) => {
      if (key.escape) setMode('menu')
    })

    return (
      <>
        <Panel title={`Edit agent: ${props.agent.agentType}`}>
          <Box flexDirection="column" gap={1} marginTop={1}>
            <Text dimColor>
              Model determines the agent&apos;s reasoning capabilities and speed.
            </Text>
            <Select
              options={modelOptions() as any}
              defaultValue={props.agent.model ?? DEFAULT_AGENT_MODEL}
              onChange={value => {
                void doUpdate({ model: value })
                setMode('menu')
              }}
            />
          </Box>
          {error ? (
            <Box marginTop={1}>
              <Text color={themeColor('error')}>{error}</Text>
            </Box>
          ) : null}
        </Panel>
        <Instructions />
      </>
    )
  }

  if (mode === 'edit-color') {
    return (
      <>
        <Panel title={`Edit agent: ${props.agent.agentType}`}>
          <Box marginTop={1}>
            <ColorPicker
              agentName={props.agent.agentType}
              currentColor={(props.agent.color as AgentColor) ?? 'automatic'}
              onConfirm={color => {
                void doUpdate({ color: color === 'automatic' ? undefined : color })
                setMode('menu')
              }}
            />
          </Box>
          {error ? (
            <Box marginTop={1}>
              <Text color={themeColor('error')}>{error}</Text>
            </Box>
          ) : null}
        </Panel>
        <Instructions />
      </>
    )
  }

  return (
    <>
      <Panel title={`Edit agent: ${props.agent.agentType}`}>
        <Box flexDirection="column">
          <Text dimColor>Source: {titleForSource(props.agent.source as any)}</Text>
          <Box marginTop={1} flexDirection="column">
            {menuItems.map((item, idx) => (
              <React.Fragment key={item.label}>
                <Text
                  color={idx === selectedIndex ? themeColor('suggestion') : undefined}
                >
                  {idx === selectedIndex ? `${figures.pointer} ` : '  '}
                  {item.label}
                </Text>
              </React.Fragment>
            ))}
          </Box>
          {error ? (
            <Box marginTop={1}>
              <Text color={themeColor('error')}>{error}</Text>
            </Box>
          ) : null}
        </Box>
      </Panel>
      <Instructions />
    </>
  )
}

function DeleteConfirm(props: {
  agent: AgentWithOverride
  onConfirm: () => void
  onCancel: () => void
}) {
  useInput((_input, key) => {
    if (key.escape) props.onCancel()
  })

  return (
    <>
      <Panel
        title="Delete agent"
        borderColor={panelBorderColor('error')}
        titleColor={themeColor('error')}
      >
        <Box flexDirection="column" gap={1}>
          <Text>
            Are you sure you want to delete the agent <Text bold>{props.agent.agentType}</Text>?
          </Text>
          <Box marginTop={1}>
            <Text dimColor>Source: {props.agent.source}</Text>
          </Box>
          <Box marginTop={1}>
            <Select
              options={[
                { label: 'Yes, delete', value: 'yes' },
                { label: 'No, cancel', value: 'no' },
              ]}
              onChange={value => {
                if (value === 'yes') props.onConfirm()
                else props.onCancel()
              }}
            />
          </Box>
        </Box>
      </Panel>
      <Instructions instructions="Press ↑↓ to navigate, Enter to select, Esc to cancel" />
    </>
  )
}

type ModeState =
  | { mode: 'list-agents'; source: AgentSourceFilter }
  | { mode: 'create-agent'; previousMode: { mode: 'list-agents'; source: AgentSourceFilter } }
  | { mode: 'agent-menu'; agent: AgentWithOverride; previousMode: { mode: 'list-agents'; source: AgentSourceFilter } }
  | { mode: 'view-agent'; agent: AgentWithOverride; previousMode: { mode: 'agent-menu'; agent: AgentWithOverride; previousMode: { mode: 'list-agents'; source: AgentSourceFilter } } }
  | { mode: 'edit-agent'; agent: AgentWithOverride; previousMode: { mode: 'agent-menu'; agent: AgentWithOverride; previousMode: { mode: 'list-agents'; source: AgentSourceFilter } } }
  | { mode: 'delete-confirm'; agent: AgentWithOverride; previousMode: { mode: 'agent-menu'; agent: AgentWithOverride; previousMode: { mode: 'list-agents'; source: AgentSourceFilter } } }

export function AgentsUI({ onExit }: { onExit: (message?: string) => void }) {
  const [mode, setMode] = useState<ModeState>({ mode: 'list-agents', source: 'all' })
  const [loading, setLoading] = useState(true)
  const [allAgents, setAllAgents] = useState<AgentConfig[]>([])
  const [activeAgents, setActiveAgents] = useState<AgentConfig[]>([])
  const [tools, setTools] = useState<Tool[]>([])
  const [changes, setChanges] = useState<string[]>([])

  const refresh = useCallback(async () => {
    clearAgentCache()
    const [all, active] = await Promise.all([getAllAgents(), getActiveAgents()])
    setAllAgents(all)
    setActiveAgents(active)
  }, [])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const [toolList] = await Promise.all([getAvailableTools(), refresh()])
        if (!mounted) return
        setTools(toolList)
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
  }, [refresh])

  const agentsWithOverride = useMemo(
    () => computeOverrides({ allAgents, activeAgents }),
    [allAgents, activeAgents],
  )

  const listAgentsForSource = useMemo(() => {
    const bySource = {
      'built-in': agentsWithOverride.filter(a => a.source === 'built-in'),
      userSettings: agentsWithOverride.filter(a => a.source === 'userSettings'),
      projectSettings: agentsWithOverride.filter(a => a.source === 'projectSettings'),
      policySettings: agentsWithOverride.filter(a => a.source === 'policySettings'),
      flagSettings: agentsWithOverride.filter(a => a.source === 'flagSettings'),
      plugin: agentsWithOverride.filter(a => a.source === 'plugin'),
    }

    if (mode.mode !== 'list-agents') return []

    if (mode.source === 'all') {
      return [
        ...bySource['built-in'],
        ...bySource.userSettings,
        ...bySource.projectSettings,
        ...bySource.policySettings,
        ...bySource.flagSettings,
        ...bySource.plugin,
      ]
    }
    if (mode.source === 'built-in') return bySource['built-in']
    if (mode.source === 'userSettings') return bySource.userSettings
    if (mode.source === 'projectSettings') return bySource.projectSettings
    if (mode.source === 'policySettings') return bySource.policySettings
    if (mode.source === 'flagSettings') return bySource.flagSettings
    if (mode.source === 'plugin') return bySource.plugin
    return []
  }, [agentsWithOverride, mode])

  const dismiss = useCallback(() => {
    if (changes.length > 0) {
      onExit(`Agent changes:\n${changes.join('\n')}`)
      return
    }
    onExit('Agents dialog dismissed')
  }, [changes, onExit])

  if (loading) {
    return (
      <>
        <Panel title="Agents" subtitle="Loading…">
          <Text dimColor>Loading agents…</Text>
        </Panel>
        <Instructions />
      </>
    )
  }

  if (mode.mode === 'list-agents') {
    return (
      <AgentsListView
        source={mode.source}
        agents={listAgentsForSource}
        changes={changes}
        onCreateNew={() => setMode({ mode: 'create-agent', previousMode: mode })}
        onSelect={agent =>
          setMode({ mode: 'agent-menu', agent, previousMode: mode })
        }
        onBack={dismiss}
      />
    )
  }

  if (mode.mode === 'create-agent') {
    return (
      <CreateAgentWizard
        tools={tools}
        existingAgents={activeAgents}
        onCancel={() => setMode(mode.previousMode)}
        onComplete={async message => {
          setChanges(prev => [...prev, message])
          await refresh()
          setMode({ mode: 'list-agents', source: 'all' })
        }}
      />
    )
  }

  if (mode.mode === 'agent-menu') {
    return (
      <AgentMenu
        agent={mode.agent}
        onCancel={() => setMode(mode.previousMode)}
        onChoose={value => {
          if (value === 'back') setMode(mode.previousMode)
          else if (value === 'view') setMode({ mode: 'view-agent', agent: mode.agent, previousMode: mode })
          else if (value === 'edit') setMode({ mode: 'edit-agent', agent: mode.agent, previousMode: mode })
          else if (value === 'delete') setMode({ mode: 'delete-confirm', agent: mode.agent, previousMode: mode })
        }}
      />
    )
  }

  if (mode.mode === 'view-agent') {
    return (
      <ViewAgent
        agent={mode.agent}
        tools={tools}
        onBack={() => setMode(mode.previousMode)}
      />
    )
  }

  if (mode.mode === 'edit-agent') {
    return (
      <EditAgent
        agent={mode.agent}
        tools={tools}
        onBack={() => setMode(mode.previousMode)}
        onSaved={async message => {
          setChanges(prev => [...prev, message])
          await refresh()
          setMode(mode.previousMode)
        }}
      />
    )
  }

  if (mode.mode === 'delete-confirm') {
    return (
      <DeleteConfirm
        agent={mode.agent}
        onCancel={() => setMode(mode.previousMode)}
        onConfirm={async () => {
          await deleteAgent(mode.agent)
          setChanges(prev => [...prev, `Deleted agent: ${chalk.bold(mode.agent.agentType)}`])
          await refresh()
          setMode({ mode: 'list-agents', source: 'all' })
        }}
      />
    )
  }

  return null
}
