import { cwd } from 'process'
import { BunShell } from '@utils/bun/shell'

const STATE: {
  originalCwd: string
} = {
  originalCwd: cwd(),
}

export async function setCwd(cwd: string): Promise<void> {
  await BunShell.getInstance().setCwd(cwd)
}

export function setOriginalCwd(cwd: string): void {
  STATE.originalCwd = cwd
}

export function getOriginalCwd(): string {
  return STATE.originalCwd
}

export function getCwd(): string {
  return BunShell.getInstance().pwd()
}
