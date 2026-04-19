export type ToolNameAliasResolution = {
  originalName: string
  resolvedName: string
  wasAliased: boolean
}

export function resolveToolNameAlias(name: string): ToolNameAliasResolution {
  const originalName = name

  const resolvedName =
    name === 'AgentOutputTool'
      ? 'TaskOutput'
      : name === 'BashOutputTool'
        ? 'TaskOutput'
        : name === 'BashOutput'
          ? 'TaskOutput'
          : name === 'TaskOutputTool'
            ? 'TaskOutput'
            : name

  return {
    originalName,
    resolvedName,
    wasAliased: resolvedName !== originalName,
  }
}
