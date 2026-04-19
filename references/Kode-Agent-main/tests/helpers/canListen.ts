import net from 'node:net'

export async function canListenOnLoopback(): Promise<boolean> {
  return await new Promise(resolve => {
    const server = net.createServer()

    server.once('error', () => {
      try {
        server.close(() => resolve(false))
      } catch {
        resolve(false)
      }
    })

    server.listen(0, '127.0.0.1', () => {
      try {
        server.close(() => resolve(true))
      } catch {
        resolve(true)
      }
    })
  })
}
