import {
  ProjectConfig,
  getCurrentProjectConfig as getCurrentProjectConfigDefault,
  saveCurrentProjectConfig as saveCurrentProjectConfigDefault,
} from '@utils/config'

export type ProjectConfigHandler = {
  getCurrentProjectConfig: () => ProjectConfig
  saveCurrentProjectConfig: (config: ProjectConfig) => void
}

const defaultConfigHandler: ProjectConfigHandler = {
  getCurrentProjectConfig: getCurrentProjectConfigDefault,
  saveCurrentProjectConfig: saveCurrentProjectConfigDefault,
}

export function handleListApprovedTools(
  cwd: string,
  projectConfigHandler: ProjectConfigHandler = defaultConfigHandler,
): string {
  const projectConfig = projectConfigHandler.getCurrentProjectConfig()
  return `Allowed tools for ${cwd}:\n${projectConfig.allowedTools.join('\n')}`
}

export function handleRemoveApprovedTool(
  tool: string,
  projectConfigHandler: ProjectConfigHandler = defaultConfigHandler,
): { success: boolean; message: string } {
  const projectConfig = projectConfigHandler.getCurrentProjectConfig()
  const originalToolCount = projectConfig.allowedTools.length
  const updatedAllowedTools = projectConfig.allowedTools.filter(t => t !== tool)

  if (originalToolCount !== updatedAllowedTools.length) {
    projectConfig.allowedTools = updatedAllowedTools
    projectConfigHandler.saveCurrentProjectConfig(projectConfig)
    return {
      success: true,
      message: `Removed ${tool} from the list of approved tools`,
    }
  } else {
    return {
      success: false,
      message: `${tool} was not in the list of approved tools`,
    }
  }
}
