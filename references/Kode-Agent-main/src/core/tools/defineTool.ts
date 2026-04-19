import type { Tool } from './tool'

export function defineTool<T extends Tool>(tool: T): T {
  return tool
}

