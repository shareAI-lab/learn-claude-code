import { describe, expect, test } from 'bun:test'
import { readFileSync } from 'fs'
import { glob } from 'glob'

describe('Runtime portability', () => {
  test('src/ does not reference Bun.* at runtime', async () => {
    const files = await glob(['src/**/*.{ts,tsx}'], {
      cwd: process.cwd(),
      nodir: true,
    })

    const offenders: string[] = []
    for (const file of files) {
      const content = readFileSync(file, 'utf8')
      if (/\bBun\./.test(content)) offenders.push(file)
    }

    expect(offenders).toEqual([])
  })
})

