export type BashGateFindingSeverity = 'high' | 'medium'

export type BashGateFindingCategory =
  | 'fs_delete'
  | 'fs_write'
  | 'privilege'
  | 'remote_exec'
  | 'persistence'
  | 'credentials'
  | 'git_data_loss'
  | 'infra_destroy'
  | 'container'
  | 'system'
  | 'process'
  | 'network'
  | 'pkg'
  | 'obfuscation'

export type BashGateFinding = {
  code: string
  severity: BashGateFindingSeverity
  category: BashGateFindingCategory
  title: string
  evidence?: string
}

type SimpleRule = {
  code: string
  severity: BashGateFindingSeverity
  category: BashGateFindingCategory
  title: string
  patterns: RegExp[]
  evidence?: (m: RegExpMatchArray) => string
}

function addUnique(
  findings: BashGateFinding[],
  finding: BashGateFinding,
): void {
  if (findings.some(f => f.code === finding.code)) return
  findings.push(finding)
}

function applySimpleRules(
  command: string,
  rules: SimpleRule[],
): BashGateFinding[] {
  const findings: BashGateFinding[] = []
  for (const rule of rules) {
    for (const re of rule.patterns) {
      const m = command.match(re)
      if (!m) continue
      addUnique(findings, {
        code: rule.code,
        severity: rule.severity,
        category: rule.category,
        title: rule.title,
        ...(rule.evidence ? { evidence: rule.evidence(m).slice(0, 200) } : {}),
      })
      break
    }
  }
  return findings
}

function analyzeRm(command: string): BashGateFinding[] {
  const findings: BashGateFinding[] = []
  if (!/(^|[;&|()\s])rm(\s|$)/.test(command)) return findings

  addUnique(findings, {
    code: 'FS_RM_ANY',
    severity: 'high',
    category: 'fs_delete',
    title: 'rm deletes files/directories (always review)',
  })

  if (/\s-rf(\s|$)/i.test(command) || /\s-fR(\s|$)/i.test(command)) {
    addUnique(findings, {
      code: 'FS_RM_FORCE_RECURSIVE',
      severity: 'high',
      category: 'fs_delete',
      title: 'rm uses force+recursive flags (high data-loss risk)',
    })
  }

  const criticalTargets = [
    { re: /(^|\s)\/(\s|$)/, label: '/' },
    { re: /(^|\s)~(\/|\s|$)/, label: '~' },
    { re: /(^|\s)\.(\s|$)/, label: '.' },
    { re: /(^|\s)\.\.(\s|$)/, label: '..' },
    {
      re: /(^|\s)\/(etc|bin|sbin|usr|var|lib|proc|sys)(\/|\s|$)/,
      label: '/(etc|bin|sbin|usr|var|lib|proc|sys)',
    },
  ]
  for (const t of criticalTargets) {
    if (t.re.test(command)) {
      addUnique(findings, {
        code: 'FS_RM_CRITICAL_TARGET',
        severity: 'high',
        category: 'fs_delete',
        title: 'rm targets a critical path',
        evidence: t.label,
      })
      break
    }
  }

  if (
    /[^\n]*\*/.test(command) ||
    /[^\n]*\?/.test(command) ||
    /[^\n]*\{/.test(command)
  ) {
    addUnique(findings, {
      code: 'FS_RM_GLOB',
      severity: 'high',
      category: 'fs_delete',
      title: 'rm uses glob/expansion patterns (wider blast radius)',
    })
  }

  return findings
}

function analyzeGit(command: string): BashGateFinding[] {
  const findings: BashGateFinding[] = []
  if (!/(^|[;&|()\s])git(\s|$)/.test(command)) return findings

  const dataLossOps: Array<{ code: string; title: string; re: RegExp }> = [
    {
      code: 'GIT_CHECKOUT',
      title: 'git checkout can discard working changes',
      re: /\bgit\b[^\n]*\bcheckout\b/i,
    },
    {
      code: 'GIT_RESTORE',
      title: 'git restore can discard working changes',
      re: /\bgit\b[^\n]*\brestore\b/i,
    },
    {
      code: 'GIT_RESET',
      title: 'git reset can discard commits/changes',
      re: /\bgit\b[^\n]*\breset\b/i,
    },
    {
      code: 'GIT_RESET_HARD',
      title: 'git reset --hard discards local changes',
      re: /\bgit\b[^\n]*\breset\b[^\n]*--hard\b/i,
    },
    {
      code: 'GIT_CLEAN',
      title: 'git clean deletes untracked files',
      re: /\bgit\b[^\n]*\bclean\b/i,
    },
    {
      code: 'GIT_CLEAN_FDX',
      title: 'git clean -fdx deletes untracked + ignored files',
      re: /\bgit\b[^\n]*\bclean\b[^\n]*-(?:[^\n]*f[^\n]*d|[^\n]*d[^\n]*f)[^\n]*x/i,
    },
    {
      code: 'GIT_PUSH_FORCE',
      title: 'git push --force rewrites remote history',
      re: /\bgit\b[^\n]*\bpush\b[^\n]*(--force|--force-with-lease|\s-f(\s|$))/i,
    },
    {
      code: 'GIT_PUSH_DELETE',
      title: 'git push --delete deletes remote refs',
      re: /\bgit\b[^\n]*\bpush\b[^\n]*(--delete|:\S+)/i,
    },
    {
      code: 'GIT_FILTER_REWRITE',
      title: 'history rewrite (filter-branch/filter-repo/rebase/amend)',
      re: /\bgit\b[^\n]*\b(filter-branch|filter-repo|rebase|commit\b[^\n]*--amend)\b/i,
    },
    {
      code: 'GIT_RECOVERY_REDUCE',
      title: 'reduces recoverability (reflog expire / gc --prune=now)',
      re: /\bgit\b[^\n]*\b(reflog\b[^\n]*expire|gc\b[^\n]*--prune=now)\b/i,
    },
    {
      code: 'GIT_STASH_DROP',
      title: 'stash drop/clear removes saved work',
      re: /\bgit\b[^\n]*\bstash\b[^\n]*\b(drop|clear)\b/i,
    },
  ]

  for (const op of dataLossOps) {
    if (!op.re.test(command)) continue
    addUnique(findings, {
      code: op.code,
      severity: 'high',
      category: 'git_data_loss',
      title: op.title,
    })
  }

  return findings
}

const SIMPLE_RULES: SimpleRule[] = [
  {
    code: 'PRIV_SUDO',
    severity: 'high',
    category: 'privilege',
    title: 'sudo escalates privileges',
    patterns: [/\bsudo\b/i],
  },
  {
    code: 'PRIV_SU',
    severity: 'high',
    category: 'privilege',
    title: 'su changes user identity',
    patterns: [/\bsu\b(\s|$)/i],
  },
  {
    code: 'PRIV_SUDOERS',
    severity: 'high',
    category: 'privilege',
    title: 'modifies sudoers policy',
    patterns: [/\/etc\/sudoers(\.d\/[^\s]+)?/i],
  },

  {
    code: 'SYS_SHUTDOWN',
    severity: 'high',
    category: 'system',
    title: 'shutdown/reboot/poweroff',
    patterns: [/\b(shutdown|reboot|poweroff|halt|init\s+0)\b/i],
  },
  {
    code: 'SYS_SYSTEMCTL_STOP',
    severity: 'high',
    category: 'system',
    title: 'systemctl stop/disable/mask can break services',
    patterns: [/\bsystemctl\b[^\n]*\b(stop|disable|mask)\b/i],
  },

  {
    code: 'FS_MKFS',
    severity: 'high',
    category: 'fs_delete',
    title: 'mkfs formats filesystems',
    patterns: [/\bmkfs(\.[a-z0-9]+)?\b/i],
  },
  {
    code: 'FS_PARTITION',
    severity: 'high',
    category: 'fs_delete',
    title: 'disk partitioning tools',
    patterns: [/\b(fdisk|parted|sfdisk|gdisk)\b/i],
  },
  {
    code: 'FS_WIPE',
    severity: 'high',
    category: 'fs_delete',
    title: 'secure wipe/destructive disk ops',
    patterns: [/\b(shred|wipefs|blkdiscard)\b/i],
  },
  {
    code: 'FS_DD_OF',
    severity: 'high',
    category: 'fs_delete',
    title: 'dd writes to output target (of=...)',
    patterns: [/\bdd\b[^\n]*\bof=\S+/i],
  },

  {
    code: 'RCE_PIPE_TO_SHELL',
    severity: 'high',
    category: 'remote_exec',
    title: 'pipe remote content into shell',
    patterns: [/\b(curl|wget)\b[^\n]*\|\s*(bash|sh)\b/i],
  },
  {
    code: 'RCE_EVAL',
    severity: 'high',
    category: 'remote_exec',
    title: 'eval/source execution',
    patterns: [/\beval\b/i, /\bsource\b\s+\S+/i, /\b\.\s+\S+/i],
  },
  {
    code: 'RCE_BASE64',
    severity: 'high',
    category: 'remote_exec',
    title: 'decode then execute',
    patterns: [/\bbase64\b[^\n]*\s+-d\b[^\n]*\|\s*(bash|sh)\b/i],
  },
  {
    code: 'RCE_ONE_LINER',
    severity: 'high',
    category: 'remote_exec',
    title: 'interpreter one-liner execution',
    patterns: [
      /\bpython3?\b\s+-c\b/i,
      /\bperl\b\s+-e\b/i,
      /\bruby\b\s+-e\b/i,
      /\bnode\b\s+-e\b/i,
    ],
  },

  {
    code: 'PERSIST_RC',
    severity: 'high',
    category: 'persistence',
    title: 'modifies shell startup files',
    patterns: [/~\/\.(bashrc|zshrc|profile|bash_profile)\b/i],
  },
  {
    code: 'PERSIST_CRON',
    severity: 'high',
    category: 'persistence',
    title: 'modifies cron jobs',
    patterns: [/\bcrontab\b/i, /\/etc\/cron\./i, /cron\.d/i],
  },
	  {
	    code: 'PERSIST_SYSTEMD',
	    severity: 'high',
	    category: 'persistence',
	    title: 'modifies systemd units',
	    patterns: [/\/etc\/systemd\/system\//i, /\bsystemctl\b[^\n]*\benable\b/i],
	  },

	  {
	    code: 'CRED_SSH',
	    severity: 'high',
	    category: 'credentials',
	    title: 'SSH key material access',
	    patterns: [/~\/\.ssh\//i, /\/etc\/ssh\//i],
	  },
  {
    code: 'CRED_SHADOW',
    severity: 'high',
    category: 'credentials',
    title: 'reads /etc/shadow',
    patterns: [/\/etc\/shadow\b/i],
  },
  {
    code: 'CRED_ENV_FILE',
    severity: 'high',
    category: 'credentials',
    title: 'reads .env secrets file',
    patterns: [
      /(\s|^)(cat|sed|awk|perl|python3?)\b[^\n]*\s+(\.\/)?\.env(\s|$)/i,
      /(^|\/)\.env(\.|$)/i,
    ],
  },

  {
    code: 'INFRA_KUBECTL_DELETE',
    severity: 'high',
    category: 'infra_destroy',
    title: 'kubectl delete can destroy cluster resources',
    patterns: [/\bkubectl\b[^\n]*\bdelete\b/i],
  },
  {
    code: 'INFRA_TERRAFORM_DESTROY',
    severity: 'high',
    category: 'infra_destroy',
    title: 'terraform destroy destroys infrastructure',
    patterns: [/\bterraform\b[^\n]*\bdestroy\b/i],
  },
  {
    code: 'INFRA_PULUMI_DESTROY',
    severity: 'high',
    category: 'infra_destroy',
    title: 'pulumi destroy destroys infrastructure',
    patterns: [/\bpulumi\b[^\n]*\bdestroy\b/i],
  },

  {
    code: 'DOCKER_PRUNE',
    severity: 'high',
    category: 'container',
    title: 'docker prune can delete data',
    patterns: [/\bdocker\b[^\n]*\b(system\s+prune|volume\s+rm)\b/i],
  },

  {
    code: 'PKG_REMOVE',
    severity: 'high',
    category: 'pkg',
    title: 'package removal/purge can break environment',
    patterns: [
      /\bapt(-get)?\b[^\n]*\b(remove|purge)\b/i,
      /\byum\b[^\n]*\bremove\b/i,
      /\bdnf\b[^\n]*\bremove\b/i,
      /\bpacman\b[^\n]*\b-R(ns)?\b/i,
      /\bnpm\b[^\n]*\buninstall\b/i,
      /\bpnpm\b[^\n]*\bremove\b/i,
      /\byarn\b[^\n]*\bremove\b/i,
    ],
  },

  {
    code: 'OBF_FORK_BOMB',
    severity: 'high',
    category: 'obfuscation',
    title: 'fork bomb pattern',
    patterns: [/:\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;:/],
  },
]

export function getBashGateFindings(command: string): BashGateFinding[] {
  const c = command.trim()
  if (!c) return []
  const findings = [
    ...analyzeRm(c),
    ...analyzeGit(c),
    ...applySimpleRules(c, SIMPLE_RULES),
  ]

  findings.sort((a, b) => a.code.localeCompare(b.code))
  return findings
}

export function shouldReviewBashCommand(findings: BashGateFinding[]): boolean {
  return findings.some(f => f.severity === 'high')
}
