import { memoize } from 'lodash-es'
import { execFileNoThrow } from './execFileNoThrow'

export const getIsGit = memoize(async (): Promise<boolean> => {
  const { code } = await execFileNoThrow('git', [
    'rev-parse',
    '--is-inside-work-tree',
  ])
  return code === 0
})

export const getHead = async (): Promise<string> => {
  const { stdout } = await execFileNoThrow('git', ['rev-parse', 'HEAD'])
  return stdout.trim()
}

export const getBranch = async (): Promise<string> => {
  const { stdout } = await execFileNoThrow(
    'git',
    ['rev-parse', '--abbrev-ref', 'HEAD'],
    undefined,
    undefined,
    false,
  )
  return stdout.trim()
}

export const getRemoteUrl = async (): Promise<string | null> => {
  const { stdout, code } = await execFileNoThrow(
    'git',
    ['remote', 'get-url', 'origin'],
    undefined,
    undefined,
    false,
  )
  return code === 0 ? stdout.trim() : null
}

export const getIsHeadOnRemote = async (): Promise<boolean> => {
  const { code } = await execFileNoThrow(
    'git',
    ['rev-parse', '@{u}'],
    undefined,
    undefined,
    false,
  )
  return code === 0
}

export const getIsClean = async (): Promise<boolean> => {
  const { stdout } = await execFileNoThrow(
    'git',
    ['status', '--porcelain'],
    undefined,
    undefined,
    false,
  )
  return stdout.trim().length === 0
}

export interface GitRepoState {
  commitHash: string
  branchName: string
  remoteUrl: string | null
  isHeadOnRemote: boolean
  isClean: boolean
}

export async function getGitState(): Promise<GitRepoState | null> {
  try {
    const [commitHash, branchName, remoteUrl, isHeadOnRemote, isClean] =
      await Promise.all([
        getHead(),
        getBranch(),
        getRemoteUrl(),
        getIsHeadOnRemote(),
        getIsClean(),
      ])

    return {
      commitHash,
      branchName,
      remoteUrl,
      isHeadOnRemote,
      isClean,
    }
  } catch (_) {
    return null
  }
}
