import { afterEach, describe, expect, test } from 'bun:test'
import http from 'node:http'
import net from 'node:net'
import { canListenOnLoopback } from '../helpers/canListen'
import {
  __resetSandboxNetworkInfrastructureForTests,
  ensureSandboxNetworkInfrastructure,
  matchesSandboxDomainPattern,
} from '@utils/sandbox/sandboxNetworkInfrastructure'
import type { SandboxRuntimeConfig } from '@utils/sandbox/sandboxConfig'

const canListenPromise = canListenOnLoopback()

function createRuntimeConfig(
  overrides?: Partial<SandboxRuntimeConfig>,
): SandboxRuntimeConfig {
  return {
    network: {
      allowedDomains: [],
      deniedDomains: [],
      allowUnixSockets: [],
      allowAllUnixSockets: false,
      allowLocalBinding: false,
      httpProxyPort: undefined,
      socksProxyPort: undefined,
    },
    filesystem: { denyRead: [], allowWrite: ['.'], denyWrite: [] },
    ripgrep: { command: 'rg', args: [] },
    ...(overrides ?? {}),
  }
}

async function readFirstLine(socket: net.Socket): Promise<string> {
  return await new Promise(resolve => {
    let buffered = ''
    const onData = (chunk: Buffer) => {
      buffered += chunk.toString('utf8')
      const idx = buffered.indexOf('\r\n')
      if (idx !== -1) {
        socket.off('data', onData)
        resolve(buffered.slice(0, idx))
      }
    }
    socket.on('data', onData)
  })
}

afterEach(async () => {
  await __resetSandboxNetworkInfrastructureForTests()
})

describe('sandbox network infrastructure (Reference CLI parity: yc0/vc0/p64/l64/i64)', () => {
  test('matchesSandboxDomainPattern supports "*.domain" and exact matches', () => {
    expect(
      matchesSandboxDomainPattern('api.example.com', '*.example.com'),
    ).toBe(true)
    expect(
      matchesSandboxDomainPattern('API.EXAMPLE.COM', '*.example.com'),
    ).toBe(true)
    expect(matchesSandboxDomainPattern('example.com', '*.example.com')).toBe(
      false,
    )
    expect(matchesSandboxDomainPattern('example.com', 'example.com')).toBe(true)
    expect(matchesSandboxDomainPattern('Example.Com', 'example.com')).toBe(true)
  })

  test('default deny: unknown host with no callback returns 403 (CONNECT)', async () => {
    if (!(await canListenPromise)) return
    const runtimeConfig = createRuntimeConfig()
    const ports = await ensureSandboxNetworkInfrastructure({
      runtimeConfig,
      permissionCallback: null,
    })

    const socket = net.connect(ports.httpProxyPort, '127.0.0.1')
    socket.write(
      'CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n',
    )

    const line = await readFirstLine(socket)
    expect(line).toContain('403')

    socket.destroy()
  })

  test('deny rules take precedence over allow rules (CONNECT)', async () => {
    if (!(await canListenPromise)) return
    const server = http.createServer((_req, res) => res.end('ok'))
    await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
    const destPort = (server.address() as any).port as number

    const runtimeConfig = createRuntimeConfig({
      network: {
        ...createRuntimeConfig().network,
        allowedDomains: ['localhost'],
        deniedDomains: ['localhost'],
      },
    })
    const ports = await ensureSandboxNetworkInfrastructure({
      runtimeConfig,
      permissionCallback: null,
    })

    const socket = net.connect(ports.httpProxyPort, '127.0.0.1')
    socket.write(
      `CONNECT localhost:${destPort} HTTP/1.1\r\nHost: localhost:${destPort}\r\n\r\n`,
    )
    const line = await readFirstLine(socket)
    expect(line).toContain('403')

    socket.destroy()
    await new Promise<void>(resolve => server.close(() => resolve()))
  })

  test('allow rules permit CONNECT to local host', async () => {
    if (!(await canListenPromise)) return
    const server = net.createServer(sock => {
      sock.end()
    })
    await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
    const destPort = (server.address() as any).port as number

    const runtimeConfig = createRuntimeConfig({
      network: {
        ...createRuntimeConfig().network,
        allowedDomains: ['localhost'],
      },
    })
    const ports = await ensureSandboxNetworkInfrastructure({
      runtimeConfig,
      permissionCallback: null,
    })

    const socket = net.connect(ports.httpProxyPort, '127.0.0.1')
    socket.write(
      `CONNECT localhost:${destPort} HTTP/1.1\r\nHost: localhost:${destPort}\r\n\r\n`,
    )
    const line = await readFirstLine(socket)
    expect(line).toContain('200')

    socket.destroy()
    await new Promise<void>(resolve => server.close(() => resolve()))
  })
})
