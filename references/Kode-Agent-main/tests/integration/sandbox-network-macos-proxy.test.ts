import { afterEach, describe, expect, test } from 'bun:test'
import http from 'node:http'
import { canListenOnLoopback } from '../helpers/canListen'
import { BunShell } from '@utils/bun/shell'
import type { BunShellSandboxOptions } from '@utils/bun/shell'
import {
  __resetSandboxNetworkInfrastructureForTests,
  ensureSandboxNetworkInfrastructure,
} from '@utils/sandbox/sandboxNetworkInfrastructure'
import type { SandboxRuntimeConfig } from '@utils/sandbox/sandboxConfig'

const canListenPromise = canListenOnLoopback()

function createRuntimeConfig(): SandboxRuntimeConfig {
  return {
    network: {
      allowedDomains: ['localhost'],
      deniedDomains: [],
      allowUnixSockets: [],
      allowAllUnixSockets: false,
      allowLocalBinding: false,
      httpProxyPort: undefined,
      socksProxyPort: undefined,
    },
    filesystem: { denyRead: [], allowWrite: ['.'], denyWrite: [] },
    ripgrep: { command: 'rg', args: [] },
  }
}

afterEach(async () => {
  await __resetSandboxNetworkInfrastructureForTests()
  BunShell.restart()
})

describe('macOS sandbox-exec network proxy (Reference CLI parity: i64/p64/l64 + seatbelt rules)', () => {
  test('sandbox blocks direct localhost connect but allows via proxy', async () => {
    if (process.platform !== 'darwin') {
      return
    }

    const sandboxExecPath = (globalThis as any).Bun?.which?.('sandbox-exec')
    if (typeof sandboxExecPath !== 'string' || sandboxExecPath.length === 0) {
      return
    }

    if (!(await canListenPromise)) {
      return
    }

    const server = http.createServer((_req, res) => {
      res.statusCode = 200
      res.setHeader('content-type', 'text/plain')
      res.end('OK')
    })
    await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
    const destPort = (server.address() as any).port as number

    const runtimeConfig = createRuntimeConfig()
    const ports = await ensureSandboxNetworkInfrastructure({
      runtimeConfig,
      permissionCallback: null,
    })

    const shell = BunShell.getInstance()
    const sandbox: BunShellSandboxOptions = {
      enabled: true,
      require: true,
      needsNetworkRestriction: true,
      allowUnixSockets: [],
      allowAllUnixSockets: false,
      allowLocalBinding: false,
      httpProxyPort: ports.httpProxyPort,
      socksProxyPort: ports.socksProxyPort,
      readConfig: { denyOnly: [] },
      writeConfig: { allowOnly: ['.'], denyWithinAllow: [] },
    }

    const direct = await shell.exec(
      `curl --noproxy '*' -sS http://localhost:${destPort} --max-time 1`,
      undefined,
      5_000,
      { sandbox },
    )
	    expect(direct.code).not.toBe(0)

	    const proxied = await shell.exec(
	      `NO_PROXY= no_proxy= curl --noproxy '' -sS http://localhost:${destPort} --max-time 2`,
	      undefined,
	      5_000,
	      { sandbox },
	    )
    expect(proxied.code).toBe(0)
    expect(proxied.stdout).toContain('OK')

    await new Promise<void>(resolve => server.close(() => resolve()))
  })
})
