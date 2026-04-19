import type { Tool } from './tool'

export type ToolRegistry = {
  readonly tools: readonly Tool[]
}

export function createToolRegistry(tools: readonly Tool[]): ToolRegistry {
  return { tools }
}

export function getToolByName(
  registry: ToolRegistry,
  name: string,
): Tool | undefined {
  return registry.tools.find(t => t.name === name)
}

