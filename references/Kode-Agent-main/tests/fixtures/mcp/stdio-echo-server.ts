import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import * as z from 'zod/v4'

const server = new McpServer({
  name: 'kode-test-stdio-server',
  version: '1.0.0',
})

server.registerTool(
  'echo',
  {
    title: 'Echo Tool',
    description: 'Echoes back the provided message',
    inputSchema: { message: z.string() },
    outputSchema: { echo: z.string() },
  },
  async ({ message }) => {
    const output = { echo: `Tool echo: ${message}` }
    return {
      content: [{ type: 'text', text: JSON.stringify(output) }],
      structuredContent: output,
    }
  },
)

server.registerPrompt(
  'hello',
  {
    title: 'Hello Prompt',
    description: 'Says hello',
    argsSchema: { name: z.string() },
  },
  ({ name }) => ({
    messages: [
      {
        role: 'assistant',
        content: {
          type: 'text',
          text: `Hello, ${name}!`,
        },
      },
    ],
  }),
)

const transport = new StdioServerTransport()
await server.connect(transport)

process.stdin.on('close', () => {
  process.exit(0)
})

