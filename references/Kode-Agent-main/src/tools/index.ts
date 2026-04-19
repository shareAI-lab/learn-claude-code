import { memoize } from 'lodash-es'
import { Tool } from '@tool'
import { AskExpertModelTool } from './ai/AskExpertModelTool/AskExpertModelTool'
import { AskUserQuestionTool } from './interaction/AskUserQuestionTool/AskUserQuestionTool'
import { BashTool } from './system/BashTool/BashTool'
import { TaskOutputTool } from './system/TaskOutputTool/TaskOutputTool'
import { EnterPlanModeTool } from './agent/PlanModeTool/EnterPlanModeTool'
import { ExitPlanModeTool } from './agent/PlanModeTool/ExitPlanModeTool'
import { FileEditTool } from './filesystem/FileEditTool/FileEditTool'
import { FileReadTool } from './filesystem/FileReadTool/FileReadTool'
import { FileWriteTool } from './filesystem/FileWriteTool/FileWriteTool'
import { GlobTool } from './filesystem/GlobTool/GlobTool'
import { GrepTool } from './search/GrepTool/GrepTool'
import { KillShellTool } from './system/KillShellTool/KillShellTool'
import { ListMcpResourcesTool } from './mcp/ListMcpResourcesTool/ListMcpResourcesTool'
import { LspTool } from './search/LspTool/LspTool'
import { MCPTool } from './mcp/MCPTool/MCPTool'
import { NotebookEditTool } from './filesystem/NotebookEditTool/NotebookEditTool'
import { ReadMcpResourceTool } from './mcp/ReadMcpResourceTool/ReadMcpResourceTool'
import { SlashCommandTool } from './interaction/SlashCommandTool/SlashCommandTool'
import { SkillTool } from './ai/SkillTool/SkillTool'
import { TaskTool } from './agent/TaskTool/TaskTool'
import { TodoWriteTool } from './interaction/TodoWriteTool/TodoWriteTool'
import { WebFetchTool } from './network/WebFetchTool/WebFetchTool'
import { WebSearchTool } from './network/WebSearchTool/WebSearchTool'
import { getMCPTools } from '@services/mcpClient'

export const getAllTools = (): Tool[] => [
  TaskTool as unknown as Tool,
  AskExpertModelTool as unknown as Tool,
  BashTool as unknown as Tool,
  TaskOutputTool as unknown as Tool,
  KillShellTool as unknown as Tool,
  GlobTool as unknown as Tool,
  GrepTool as unknown as Tool,
  LspTool as unknown as Tool,
  FileReadTool as unknown as Tool,
  FileEditTool as unknown as Tool,
  FileWriteTool as unknown as Tool,
  NotebookEditTool as unknown as Tool,
  TodoWriteTool as unknown as Tool,
  WebSearchTool as unknown as Tool,
  WebFetchTool as unknown as Tool,
  AskUserQuestionTool as unknown as Tool,
  EnterPlanModeTool as unknown as Tool,
  ExitPlanModeTool as unknown as Tool,
  SlashCommandTool as unknown as Tool,
  SkillTool as unknown as Tool,
  ListMcpResourcesTool as unknown as Tool,
  ReadMcpResourceTool as unknown as Tool,
  MCPTool as unknown as Tool,
]

export const getTools = memoize(
  async (_includeOptional?: boolean): Promise<Tool[]> => {
    const tools = [...getAllTools(), ...(await getMCPTools())]

    const isEnabled = await Promise.all(tools.map(tool => tool.isEnabled()))
    return tools.filter((_, i) => isEnabled[i])
  },
)

export const getReadOnlyTools = memoize(async (): Promise<Tool[]> => {
  const tools = getAllTools().filter(tool => tool.isReadOnly())
  const isEnabled = await Promise.all(tools.map(tool => tool.isEnabled()))
  return tools.filter((_, index) => isEnabled[index])
})
