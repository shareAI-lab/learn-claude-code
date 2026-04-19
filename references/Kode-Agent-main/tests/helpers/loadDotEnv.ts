import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

export function loadDotEnvIfPresent(cwd: string = process.cwd()): void {
  try {
    const envPath = join(cwd, '.env')
    if (!existsSync(envPath)) return

    const envContent = readFileSync(envPath, 'utf8')
    envContent.split('\n').forEach((line: string) => {
      const [key, ...valueParts] = line.split('=')
      if (key && valueParts.length > 0) {
        const value = valueParts.join('=')
        const normalizedKey = key.trim()
        if (!process.env[normalizedKey]) {
          process.env[normalizedKey] = value.trim()
        }
      }
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    console.log('⚠️  Could not load .env file:', message)
  }
}

