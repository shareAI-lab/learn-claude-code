import type { Command } from '@commands'
import {
  getClients,
  getMcprcServerStatus,
  listMCPServers,
} from '@services/mcpClient'
import { PRODUCT_COMMAND } from '@constants/product'
import chalk from 'chalk'
import { getTheme } from '@utils/theme'
import { getProjectMcpServerDefinitions } from '@utils/config'

const mcp = {
  type: 'local',
  name: 'mcp',
  description: 'Show MCP server connection status',
  isEnabled: true,
  isHidden: false,
  async call() {
    const servers = listMCPServers()
    const clients = await getClients()
    const theme = getTheme()
    const projectFileServers = getProjectMcpServerDefinitions()

    if (Object.keys(servers).length === 0) {
      return [
        '⎿  No MCP servers configured.',
        `⎿  - Create \`.mcp.json\` or \`.mcprc\` in this project, or run \`${PRODUCT_COMMAND} mcp add\`.`,
        `⎿  - Run \`${PRODUCT_COMMAND} mcp list\` to view configured servers.`,
      ].join('\n')
    }

    const clientByName = new Map<string, (typeof clients)[number]>()
    for (const client of clients) {
      clientByName.set(client.name, client)
    }

    const serverStatusLines = Object.keys(servers)
      .sort((a, b) => a.localeCompare(b))
      .map(name => {
        const client = clientByName.get(name)
        if (client?.type === 'connected') {
          return `⎿  • ${name}: ${chalk.hex(theme.success)('connected')}`
        }
        if (client?.type === 'failed') {
          return `⎿  • ${name}: ${chalk.hex(theme.error)('failed')}`
        }

        if (projectFileServers.servers[name]) {
          const approval = getMcprcServerStatus(name)
          if (approval === 'pending') {
            return `⎿  • ${name}: ${chalk.hex(theme.warning)('pending approval')}`
          }
          if (approval === 'rejected') {
            return `⎿  • ${name}: ${chalk.hex(theme.error)('rejected')}`
          }
        }

        return `⎿  • ${name}: ${chalk.hex(theme.error)('disconnected')}`
      })

    return ['⎿  MCP Server Status', ...serverStatusLines].join('\n')
  },
  userFacingName() {
    return 'mcp'
  },
} satisfies Command

export default mcp
