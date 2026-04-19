import { existsSync, mkdirSync, readFileSync, realpathSync } from 'fs'
import { randomBytes } from 'crypto'
import { isAbsolute, join, relative, resolve, parse } from 'path'
import type { ToolUseContext } from '@tool'
import { getKodeBaseDir } from '@utils/config/env'
import {
  PLAN_SLUG_ADJECTIVES,
  PLAN_SLUG_NOUNS,
  PLAN_SLUG_VERBS,
} from './planSlugWords'

const DEFAULT_CONVERSATION_KEY = 'default'
const MAX_SLUG_ATTEMPTS = 10
const TURNS_BETWEEN_ATTACHMENTS = 5

type PlanModeFlags = {
  hasExitedPlanMode: boolean
  needsPlanModeExitAttachment: boolean
}

type PlanModeAttachmentState = {
  hasInjected: boolean
  lastInjectedAssistantTurn: number
}

const planModeEnabledByConversationKey = new Map<string, boolean>()
const planSlugCache = new Map<string, string>()
const planModeFlagsByConversationKey = new Map<string, PlanModeFlags>()
const planModeAttachmentStateByAgentKey = new Map<
  string,
  PlanModeAttachmentState
>()
let activePlanConversationKey: string | null = null

function getConversationKey(context?: Pick<ToolUseContext, 'options'>): string {
  const messageLogName =
    context?.options?.messageLogName ?? DEFAULT_CONVERSATION_KEY
  const forkNumber = context?.options?.forkNumber ?? 0
  return `${messageLogName}:${forkNumber}`
}

export function getPlanConversationKey(
  context?: Pick<ToolUseContext, 'options'>,
): string {
  return getConversationKey(context)
}

export function setActivePlanConversationKey(conversationKey: string): void {
  activePlanConversationKey = conversationKey
}

export function getActivePlanConversationKey(): string | null {
  return activePlanConversationKey
}

function getAgentKey(
  context?: Pick<ToolUseContext, 'options' | 'agentId'>,
): string {
  const conversationKey = getConversationKey(context)
  const agentId = context?.agentId ?? 'main'
  return `${conversationKey}:${agentId}`
}

function pickIndex(length: number): number {
  return randomBytes(4).readUInt32BE(0) % length
}

function pickWord(words: readonly string[]): string {
  return words[pickIndex(words.length)]!
}

function generateSlug(): string {
  const adjective = pickWord(PLAN_SLUG_ADJECTIVES)
  const verb = pickWord(PLAN_SLUG_VERBS)
  const noun = pickWord(PLAN_SLUG_NOUNS)
  return `${adjective}-${verb}-${noun}`
}

function getOrCreatePlanSlug(conversationKey: string): string {
  const existing = planSlugCache.get(conversationKey)
  if (existing) return existing

  const dir = getPlanDirectory()

  let slug: string | null = null
  for (let attempt = 0; attempt < MAX_SLUG_ATTEMPTS; attempt++) {
    slug = generateSlug()
    const path = join(dir, `${slug}.md`)
    if (!existsSync(path)) break
  }

  if (!slug) slug = generateSlug()

  planSlugCache.set(conversationKey, slug)
  return slug
}

function extractSlugFromPlanFilePath(planFilePath: string): string | null {
  if (!planFilePath) return null
  const baseName = parse(planFilePath).name
  if (!baseName) return null

  const agentMarker = '-agent-'
  const idx = baseName.lastIndexOf(agentMarker)
  if (idx === -1) return baseName
  if (idx === 0) return null
  return baseName.slice(0, idx)
}

function getOrCreatePlanModeFlags(conversationKey: string): PlanModeFlags {
  const existing = planModeFlagsByConversationKey.get(conversationKey)
  if (existing) return existing
  const created: PlanModeFlags = {
    hasExitedPlanMode: false,
    needsPlanModeExitAttachment: false,
  }
  planModeFlagsByConversationKey.set(conversationKey, created)
  return created
}

function getMaxParallelExploreAgents(): number {
  const raw =
    process.env.KODE_PLAN_V2_EXPLORE_AGENT_COUNT ??
    process.env.CLAUDE_CODE_PLAN_V2_EXPLORE_AGENT_COUNT
  if (raw) {
    const parsed = Number.parseInt(raw, 10)
    if (Number.isFinite(parsed) && parsed > 0 && parsed <= 10) return parsed
  }
  return 3
}

function getMaxParallelPlanAgents(): number {
  const raw =
    process.env.KODE_PLAN_V2_AGENT_COUNT ??
    process.env.CLAUDE_CODE_PLAN_V2_AGENT_COUNT
  if (raw) {
    const parsed = Number.parseInt(raw, 10)
    if (Number.isFinite(parsed) && parsed > 0 && parsed <= 10) return parsed
  }
  return 1
}

function buildPlanModeMainReminder(args: {
  planExists: boolean
  planFilePath: string
  maxParallelExploreAgents: number
  maxParallelPlanAgents: number
}): string {
  const {
    planExists,
    planFilePath,
    maxParallelExploreAgents,
    maxParallelPlanAgents,
  } = args

  const writeToolName = 'Write'
  const editToolName = 'Edit'
  const askUserToolName = 'AskUserQuestion'
  const exploreAgentType = 'Explore'
  const planAgentType = 'Plan'
  const exitPlanModeToolName = 'ExitPlanMode'

  return `Plan mode is active. The user indicated that they do not want you to execute yet -- you MUST NOT make any edits (with the exception of the plan file mentioned below), run any non-readonly tools (including changing configs or making commits), or otherwise make any changes to the system. This supercedes any other instructions you have received.

## Plan File Info:
${planExists ? `A plan file already exists at ${planFilePath}. You can read it and make incremental edits using the ${editToolName} tool.` : `No plan file exists yet. You should create your plan at ${planFilePath} using the ${writeToolName} tool.`}
You should build your plan incrementally by writing to or editing this file. NOTE that this is the only file you are allowed to edit - other than this you are only allowed to take READ-ONLY actions.

## Plan Workflow

### Phase 1: Initial Understanding
Goal: Gain a comprehensive understanding of the user's request by reading through code and asking them questions. Critical: In this phase you should only use the ${exploreAgentType} subagent type.

1. Focus on understanding the user's request and the code associated with their request

2. **Launch up to ${maxParallelExploreAgents} ${exploreAgentType} agents IN PARALLEL** (single message, multiple tool calls) to efficiently explore the codebase.
   - Use 1 agent when the task is isolated to known files, the user provided specific file paths, or you're making a small targeted change.
   - Use multiple agents when: the scope is uncertain, multiple areas of the codebase are involved, or you need to understand existing patterns before planning.
   - Quality over quantity - ${maxParallelExploreAgents} agents maximum, but you should try to use the minimum number of agents necessary (usually just 1)
   - If using multiple agents: Provide each agent with a specific search focus or area to explore. Example: One agent searches for existing implementations, another explores related components, a third investigates testing patterns

3. After exploring the code, use the ${askUserToolName} tool to clarify ambiguities in the user request up front.

### Phase 2: Design
Goal: Design an implementation approach.

Launch ${planAgentType} agent(s) to design the implementation based on the user's intent and your exploration results from Phase 1.

You can launch up to ${maxParallelPlanAgents} agent(s) in parallel.

**Guidelines:**
- **Default**: Launch at least 1 Plan agent for most tasks - it helps validate your understanding and consider alternatives
- **Skip agents**: Only for truly trivial tasks (typo fixes, single-line changes, simple renames)
${
  maxParallelPlanAgents > 1
    ? `- **Multiple agents**: Use up to ${maxParallelPlanAgents} agents for complex tasks that benefit from different perspectives

Examples of when to use multiple agents:
- The task touches multiple parts of the codebase
- It's a large refactor or architectural change
- There are many edge cases to consider
- You'd benefit from exploring different approaches

Example perspectives by task type:
- New feature: simplicity vs performance vs maintainability
- Bug fix: root cause vs workaround vs prevention
- Refactoring: minimal change vs clean architecture
`
    : ''
}
In the agent prompt:
- Provide comprehensive background context from Phase 1 exploration including filenames and code path traces
- Describe requirements and constraints
- Request a detailed implementation plan

### Phase 3: Review
Goal: Review the plan(s) from Phase 2 and ensure alignment with the user's intentions.
1. Read the critical files identified by agents to deepen your understanding
2. Ensure that the plans align with the user's original request
3. Use ${askUserToolName} to clarify any remaining questions with the user

### Phase 4: Final Plan
Goal: Write your final plan to the plan file (the only file you can edit).
- Include only your recommended approach, not all alternatives
- Ensure that the plan file is concise enough to scan quickly, but detailed enough to execute effectively
- Include the paths of critical files to be modified

### Phase 5: Call ${exitPlanModeToolName}
At the very end of your turn, once you have asked the user questions and are happy with your final plan file - you should always call ${exitPlanModeToolName} to indicate to the user that you are done planning.
This is critical - your turn should only end with either asking the user a question or calling ${exitPlanModeToolName}. Do not stop unless it's for these 2 reasons.

NOTE: At any point in time through this workflow you should feel free to ask the user questions or clarifications. Don't make large assumptions about user intent. The goal is to present a well researched plan to the user, and tie any loose ends before implementation begins.`
}

function buildPlanModeSubAgentReminder(args: {
  planExists: boolean
  planFilePath: string
}): string {
  const { planExists, planFilePath } = args

  const writeToolName = 'Write'
  const editToolName = 'Edit'
  const askUserToolName = 'AskUserQuestion'

  return `Plan mode is active. The user indicated that they do not want you to execute yet -- you MUST NOT make any edits, run any non-readonly tools (including changing configs or making commits), or otherwise make any changes to the system. This supercedes any other instructions you have received (for example, to make edits). Instead, you should:

## Plan File Info:
${planExists ? `A plan file already exists at ${planFilePath}. You can read it and make incremental edits using the ${editToolName} tool if you need to.` : `No plan file exists yet. You should create your plan at ${planFilePath} using the ${writeToolName} tool if you need to.`}
You should build your plan incrementally by writing to or editing this file. NOTE that this is the only file you are allowed to edit - other than this you are only allowed to take READ-ONLY actions.
Answer the user's query comprehensively, using the ${askUserToolName} tool if you need to ask the user clarifying questions. If you do use the ${askUserToolName}, make sure to ask all clarifying questions you need to fully understand the user's intent before proceeding.`
}

function buildPlanModeReentryReminder(planFilePath: string): string {
  const exitPlanModeToolName = 'ExitPlanMode'

  return `## Re-entering Plan Mode

You are returning to plan mode after having previously exited it. A plan file exists at ${planFilePath} from your previous planning session.

**Before proceeding with any new planning, you should:**
1. Read the existing plan file to understand what was previously planned
2. Evaluate the user's current request against that plan
3. Decide how to proceed:
   - **Different task**: If the user's request is for a different task—even if it's similar or related—start fresh by overwriting the existing plan
   - **Same task, continuing**: If this is explicitly a continuation or refinement of the exact same task, modify the existing plan while cleaning up outdated or irrelevant sections
4. Continue on with the plan process and most importantly you should always edit the plan file one way or the other before calling ${exitPlanModeToolName}

Treat this as a fresh planning session. Do not assume the existing plan is relevant without evaluating it first.`
}

function buildPlanModeExitReminder(planFilePath: string): string {
  return `## Exited Plan Mode

You have exited plan mode. You can now make edits, run tools, and take actions. The plan file is located at ${planFilePath} if you need to reference it.`
}

function wrapSystemReminder(text: string): string {
  return `<system-reminder>\n${text}\n</system-reminder>`
}

export function getPlanModeSystemPromptAdditions(
  messages: Array<{ type?: string }>,
  context: ToolUseContext,
): string[] {
  const conversationKey = getConversationKey(context)
  const agentKey = getAgentKey(context)
  const flags = getOrCreatePlanModeFlags(conversationKey)
  const additions: string[] = []

  const assistantTurns = messages.filter(m => m?.type === 'assistant').length

  if (isPlanModeEnabled(context)) {
    const previous =
      planModeAttachmentStateByAgentKey.get(agentKey) ??
      ({
        hasInjected: false,
        lastInjectedAssistantTurn: -Infinity,
      } satisfies PlanModeAttachmentState)

    if (
      previous.hasInjected &&
      assistantTurns - previous.lastInjectedAssistantTurn <
        TURNS_BETWEEN_ATTACHMENTS
    ) {
      return []
    }

    const planFilePath = getPlanFilePath(context.agentId, conversationKey)
    const planExists = existsSync(planFilePath)

    if (flags.hasExitedPlanMode && planExists) {
      additions.push(
        wrapSystemReminder(buildPlanModeReentryReminder(planFilePath)),
      )
      flags.hasExitedPlanMode = false
    }

    const isSubAgent = !!context.agentId
    additions.push(
      wrapSystemReminder(
        isSubAgent
          ? buildPlanModeSubAgentReminder({ planExists, planFilePath })
          : buildPlanModeMainReminder({
              planExists,
              planFilePath,
              maxParallelExploreAgents: getMaxParallelExploreAgents(),
              maxParallelPlanAgents: getMaxParallelPlanAgents(),
            }),
      ),
    )

    planModeFlagsByConversationKey.set(conversationKey, flags)
    planModeAttachmentStateByAgentKey.set(agentKey, {
      hasInjected: true,
      lastInjectedAssistantTurn: assistantTurns,
    })

    return additions
  }

  if (flags.needsPlanModeExitAttachment) {
    const planFilePath = getPlanFilePath(context.agentId, conversationKey)
    additions.push(wrapSystemReminder(buildPlanModeExitReminder(planFilePath)))
    flags.needsPlanModeExitAttachment = false
    planModeFlagsByConversationKey.set(conversationKey, flags)
  }

  return additions
}

export function isPlanModeEnabled(context?: ToolUseContext): boolean {
  const key = getConversationKey(context)
  return planModeEnabledByConversationKey.get(key) ?? false
}

export function enterPlanMode(context?: ToolUseContext): {
  planFilePath: string
} {
  const key = getConversationKey(context)
  planModeEnabledByConversationKey.set(key, true)
  return { planFilePath: getPlanFilePath(context?.agentId, key) }
}

export function enterPlanModeForConversationKey(conversationKey: string): void {
  planModeEnabledByConversationKey.set(conversationKey, true)
}

export function exitPlanMode(context?: ToolUseContext): {
  planFilePath: string
} {
  const key = getConversationKey(context)
  planModeEnabledByConversationKey.set(key, false)

  const flags = getOrCreatePlanModeFlags(key)
  flags.hasExitedPlanMode = true
  flags.needsPlanModeExitAttachment = true
  planModeFlagsByConversationKey.set(key, flags)

  return { planFilePath: getPlanFilePath(context?.agentId, key) }
}

export function exitPlanModeForConversationKey(conversationKey: string): void {
  planModeEnabledByConversationKey.set(conversationKey, false)
  const flags = getOrCreatePlanModeFlags(conversationKey)
  flags.hasExitedPlanMode = true
  flags.needsPlanModeExitAttachment = true
  planModeFlagsByConversationKey.set(conversationKey, flags)
}

export function setPlanSlug(conversationKey: string, slug: string): void {
  planSlugCache.set(conversationKey, slug)
}

export function getPlanSlugForConversationKey(
  conversationKey: string,
): string | null {
  return planSlugCache.get(conversationKey) ?? null
}

export function hydratePlanSlugFromMessages(
  messages: unknown[],
  context?: ToolUseContext,
): boolean {
  const conversationKey = getConversationKey(context)
  if (planSlugCache.has(conversationKey)) return true

  for (let i = messages.length - 1; i >= 0; i--) {
    const msg: any = (messages as any[])[i]
    const directSlug = typeof msg?.slug === 'string' ? msg.slug.trim() : ''
    if (directSlug) {
      planSlugCache.set(conversationKey, directSlug)
      return true
    }

    const data = msg?.toolUseResult?.data
    if (!data || typeof data !== 'object') continue

    const planFilePath =
      typeof (data as any).planFilePath === 'string'
        ? (data as any).planFilePath
        : typeof (data as any).filePath === 'string'
          ? (data as any).filePath
          : null

    if (!planFilePath) continue

    const slug = extractSlugFromPlanFilePath(planFilePath)
    if (!slug) continue

    planSlugCache.set(conversationKey, slug)
    return true
  }

  return false
}

export function getPlanDirectory(): string {
  const dir = join(getKodeBaseDir(), 'plans')
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true })
  }
  return dir
}

export function getPlanFilePath(
  agentId?: string,
  conversationKey?: string,
): string {
  const dir = getPlanDirectory()
  const key = conversationKey ?? DEFAULT_CONVERSATION_KEY
  const slug = getOrCreatePlanSlug(key)

  if (!agentId) return join(dir, `${slug}.md`)
  return join(dir, `${slug}-agent-${agentId}.md`)
}

function resolveExistingPath(path: string): string {
  const resolved = resolve(path)
  try {
    return realpathSync(resolved)
  } catch {
    return resolved
  }
}

export function isPlanFilePathForActiveConversation(path: string): boolean {
  const key = activePlanConversationKey ?? DEFAULT_CONVERSATION_KEY
  const planDir = resolveExistingPath(getPlanDirectory())
  const expectedMainPlanPath = resolveExistingPath(
    getPlanFilePath(undefined, key),
  )
  const target = resolveExistingPath(path)

  const rel = relative(planDir, target)
  if (!rel || rel === '') return false
  if (rel.startsWith('..')) return false
  if (isAbsolute(rel)) return false

  const expectedSlug = parse(expectedMainPlanPath).name
  const targetName = parse(target).name
  return (
    targetName === expectedSlug ||
    targetName.startsWith(`${expectedSlug}-agent-`)
  )
}

export function isMainPlanFilePathForActiveConversation(path: string): boolean {
  const key = activePlanConversationKey ?? DEFAULT_CONVERSATION_KEY
  const expected = resolveExistingPath(getPlanFilePath(undefined, key))
  const target = resolveExistingPath(path)
  return target === expected
}

export function isPathInPlanDirectory(path: string): boolean {
  const dir = resolve(getPlanDirectory())
  const target = resolve(path)
  const rel = relative(dir, target)
  if (!rel || rel === '') return true
  if (rel.startsWith('..')) return false
  if (isAbsolute(rel)) return false
  return true
}

export function readPlanFile(
  agentId?: string,
  conversationKey?: string,
): { content: string; exists: boolean; planFilePath: string } {
  const planFilePath = getPlanFilePath(agentId, conversationKey)
  if (!existsSync(planFilePath)) {
    return { content: '', exists: false, planFilePath }
  }
  return {
    content: readFileSync(planFilePath, 'utf8'),
    exists: true,
    planFilePath,
  }
}

export function __resetPlanModeForTests(): void {
  planModeEnabledByConversationKey.clear()
  planSlugCache.clear()
  planModeFlagsByConversationKey.clear()
  planModeAttachmentStateByAgentKey.clear()
  activePlanConversationKey = null
}
