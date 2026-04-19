export type ToolPermissionRuleBehavior = 'allow' | 'deny' | 'ask'

export type ToolPermissionRuleSource =
  | 'userSettings'
  | 'projectSettings'
  | 'localSettings'
  | 'flagSettings'
  | 'policySettings'
  | 'cliArg'
  | 'command'
  | 'session'

export type ToolPermissionMode =
  | 'default'
  | 'acceptEdits'
  | 'bypassPermissions'
  | 'dontAsk'

export type ToolPermissionRuleValue = {
  toolName: string
  ruleContent?: string
}

export type ToolPermissionRule = {
  source: ToolPermissionRuleSource
  ruleBehavior: ToolPermissionRuleBehavior
  ruleValue: ToolPermissionRuleValue
}

export function describeToolPermissionRuleSource(
  source: ToolPermissionRuleSource,
): string {
  switch (source) {
    case 'cliArg':
      return 'CLI argument'
    case 'command':
      return 'command configuration'
    case 'session':
      return 'current session'
    case 'localSettings':
      return 'project local settings'
    case 'projectSettings':
      return 'project settings'
    case 'policySettings':
      return 'policy settings'
    case 'userSettings':
      return 'user settings'
    case 'flagSettings':
      return 'flag settings'
  }
}

export function parseToolPermissionRuleValue(
  rule: string,
): ToolPermissionRuleValue {
  const match = rule.match(/^([^(]+)\(([^)]+)\)$/)
  if (!match) return { toolName: rule }

  const toolName = match[1]
  const ruleContent = match[2]
  if (!toolName || !ruleContent) return { toolName: rule }

  return { toolName, ruleContent }
}

export function formatToolPermissionRuleValue(
  rule: ToolPermissionRuleValue,
): string {
  return rule.ruleContent
    ? `${rule.toolName}(${rule.ruleContent})`
    : rule.toolName
}

export type ParsedMcpToolName = { serverName: string; toolName?: string }

export function parseMcpToolName(name: string): ParsedMcpToolName | null {
  const parts = name.split('__')
  const [prefix, serverName, ...rest] = parts
  if (prefix !== 'mcp' || !serverName) return null
  const toolName = rest.length > 0 ? rest.join('__') : undefined
  return { serverName, toolName }
}
