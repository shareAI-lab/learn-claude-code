import { beforeEach, describe, expect, test } from 'bun:test'
import { hasPermissionsToUseTool } from '@permissions'
import { FileReadTool } from '@tools/FileReadTool/FileReadTool'
import { FileWriteTool } from '@tools/FileWriteTool/FileWriteTool'
import {
  applyToolPermissionContextUpdates,
  createDefaultToolPermissionContext,
} from '@kode-types/toolPermissionContext'
import { mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import path from 'path'
import {
  __resetPlanModeForTests,
  getPlanConversationKey,
  getPlanFilePath,
} from '@utils/plan/planMode'

function makeContext(args?: {
  toolPermissionContext?: ReturnType<typeof createDefaultToolPermissionContext>
  messageLogName?: string
  forkNumber?: number
}) {
  return {
    abortController: new AbortController(),
    messageId: 'test',
    options: {
      commands: [],
      tools: [],
      verbose: false,
      slowAndCapableModel: undefined,
      safeMode: false,
      forkNumber: args?.forkNumber ?? 0,
      messageLogName: args?.messageLogName ?? 'test',
      maxThinkingTokens: 0,
      toolPermissionContext: args?.toolPermissionContext,
    },
    readFileTimestamps: {},
  }
}

describe('Reference CLI parity: filesystem permission engine', () => {
  beforeEach(() => {
    __resetPlanModeForTests()
  })

  test('allows reading inside working directory by default', async () => {
    const toolPermissionContext = createDefaultToolPermissionContext({
      isBypassPermissionsModeAvailable: true,
    })
    const ctx = makeContext({ toolPermissionContext })

    const result = await hasPermissionsToUseTool(
      FileReadTool as any,
      { file_path: 'package.json' },
      ctx as any,
      {} as any,
    )

    expect(result.result).toBe(true)
  })

  test('asks to read outside working directory and provides suggestions', async () => {
    const tmp = mkdtempSync(path.join(tmpdir(), 'kode-perm-read-'))
    const filePath = path.join(tmp, 'a.txt')
    writeFileSync(filePath, 'hello', 'utf8')

    try {
      const toolPermissionContext = createDefaultToolPermissionContext({
        isBypassPermissionsModeAvailable: true,
      })
      const ctx = makeContext({ toolPermissionContext })

      const result = await hasPermissionsToUseTool(
        FileReadTool as any,
        { file_path: filePath },
        ctx as any,
        {} as any,
      )

      expect(result.result).toBe(false)
      expect((result as any).suggestions?.length).toBeGreaterThan(0)
    } finally {
      rmSync(tmp, { recursive: true, force: true })
    }
  })

  test('applying read suggestions allows subsequent reads', async () => {
    const tmp = mkdtempSync(path.join(tmpdir(), 'kode-perm-read-apply-'))
    const filePath = path.join(tmp, 'a.txt')
    writeFileSync(filePath, 'hello', 'utf8')

    try {
      const base = createDefaultToolPermissionContext({
        isBypassPermissionsModeAvailable: true,
      })
      const ctx = makeContext({ toolPermissionContext: base })

      const denied = await hasPermissionsToUseTool(
        FileReadTool as any,
        { file_path: filePath },
        ctx as any,
        {} as any,
      )

      expect(denied.result).toBe(false)
      const updates = (denied as any).suggestions ?? []
      expect(updates.length).toBeGreaterThan(0)

      const updatedContext = applyToolPermissionContextUpdates(base, updates)
      const ctx2 = makeContext({ toolPermissionContext: updatedContext })
      const allowed = await hasPermissionsToUseTool(
        FileReadTool as any,
        { file_path: filePath },
        ctx2 as any,
        {} as any,
      )
      expect(allowed.result).toBe(true)
    } finally {
      rmSync(tmp, { recursive: true, force: true })
    }
  })

  test('applying write suggestions allows subsequent writes via acceptEdits + addDirectories', async () => {
    const tmp = mkdtempSync(path.join(tmpdir(), 'kode-perm-write-apply-'))
    const filePath = path.join(tmp, 'b.txt')

    try {
      const base = createDefaultToolPermissionContext({
        isBypassPermissionsModeAvailable: true,
      })
      const ctx = makeContext({ toolPermissionContext: base })

      const denied = await hasPermissionsToUseTool(
        FileWriteTool as any,
        { file_path: filePath, content: 'hi' },
        ctx as any,
        {} as any,
      )

      expect(denied.result).toBe(false)
      const updates = (denied as any).suggestions ?? []
      expect(updates.length).toBeGreaterThan(0)
      expect(
        updates.some(
          (u: any) => u.type === 'setMode' && u.mode === 'acceptEdits',
        ),
      ).toBe(true)
      expect(updates.some((u: any) => u.type === 'addDirectories')).toBe(true)

      const updatedContext = applyToolPermissionContextUpdates(base, updates)
      const ctx2 = makeContext({ toolPermissionContext: updatedContext })
      const allowed = await hasPermissionsToUseTool(
        FileWriteTool as any,
        { file_path: filePath, content: 'hi' },
        ctx2 as any,
        {} as any,
      )
      expect(allowed.result).toBe(true)
    } finally {
      rmSync(tmp, { recursive: true, force: true })
    }
  })

  test('allows writing to the plan file for the current conversation', async () => {
    const tmpConfig = mkdtempSync(path.join(tmpdir(), 'kode-plan-config-'))
    const previousConfigDir = process.env.KODE_CONFIG_DIR
    process.env.KODE_CONFIG_DIR = tmpConfig

    try {
      const toolPermissionContext = createDefaultToolPermissionContext({
        isBypassPermissionsModeAvailable: true,
      })
      const ctx = makeContext({
        toolPermissionContext,
        messageLogName: 'plan-test',
        forkNumber: 0,
      })

      const conversationKey = getPlanConversationKey(ctx as any)
      const planFilePath = getPlanFilePath(undefined, conversationKey)
      mkdirSync(path.dirname(planFilePath), { recursive: true })

      const result = await hasPermissionsToUseTool(
        FileWriteTool as any,
        { file_path: planFilePath, content: 'plan' },
        ctx as any,
        {} as any,
      )
      expect(result.result).toBe(true)
    } finally {
      process.env.KODE_CONFIG_DIR = previousConfigDir
      rmSync(tmpConfig, { recursive: true, force: true })
    }
  })

  test('asks for UNC paths and does not provide suggestions', async () => {
    const toolPermissionContext = createDefaultToolPermissionContext({
      isBypassPermissionsModeAvailable: true,
    })
    const ctx = makeContext({ toolPermissionContext })

    const result = await hasPermissionsToUseTool(
      FileReadTool as any,
      { file_path: '//server/share/file.txt' },
      ctx as any,
      {} as any,
    )

    expect(result.result).toBe(false)
    expect((result as any).suggestions).toBeUndefined()
  })

  test('asks for suspicious Windows path patterns and does not provide suggestions', async () => {
    const toolPermissionContext = createDefaultToolPermissionContext({
      isBypassPermissionsModeAvailable: true,
    })
    const ctx = makeContext({ toolPermissionContext })

    const result = await hasPermissionsToUseTool(
      FileReadTool as any,
      { file_path: 'C:\\\\foo:bar' },
      ctx as any,
      {} as any,
    )

    expect(result.result).toBe(false)
    expect((result as any).suggestions).toBeUndefined()
  })

  test('symlink target outside working dirs requires manual approval unless added to additionalWorkingDirectories', async () => {
    const outside = mkdtempSync(path.join(tmpdir(), 'kode-perm-symlink-out-'))
    const outsideFile = path.join(outside, 'target.txt')
    writeFileSync(outsideFile, 'x', 'utf8')

    const inside = mkdtempSync(path.join(process.cwd(), '.tmp-kode-perm-in-'))
    const linkPath = path.join(inside, 'link.txt')
    symlinkSync(outsideFile, linkPath)

    try {
      const base = createDefaultToolPermissionContext({
        isBypassPermissionsModeAvailable: true,
      })
      const ctx = makeContext({ toolPermissionContext: base })

      const denied = await hasPermissionsToUseTool(
        FileReadTool as any,
        { file_path: linkPath },
        ctx as any,
        {} as any,
      )
      expect(denied.result).toBe(false)

      const updated = applyToolPermissionContextUpdates(base, [
        {
          type: 'addDirectories',
          destination: 'session',
          directories: [outside],
        },
      ])
      const ctx2 = makeContext({ toolPermissionContext: updated })
      const allowed = await hasPermissionsToUseTool(
        FileReadTool as any,
        { file_path: linkPath },
        ctx2 as any,
        {} as any,
      )
      expect(allowed.result).toBe(true)
    } finally {
      rmSync(outside, { recursive: true, force: true })
      rmSync(inside, { recursive: true, force: true })
    }
  })
})
