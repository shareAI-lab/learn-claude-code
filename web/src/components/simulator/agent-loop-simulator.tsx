"use client";

import { useRef, useEffect, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { useLocale, useTranslations } from "@/lib/i18n";
import { useSimulator } from "@/hooks/useSimulator";
import { SimulatorControls } from "./simulator-controls";
import { SimulatorMessage } from "./simulator-message";
import type { Scenario } from "@/types/agent-data";
import {
  isGenericScenarioVersion,
  resolveLegacySessionAssetVersion,
} from "@/lib/session-assets";

const scenarioModules: Record<string, () => Promise<{ default: Scenario }>> = {
  s01: () => import("@/data/scenarios/s01.json") as Promise<{ default: Scenario }>,
  s02: () => import("@/data/scenarios/s02.json") as Promise<{ default: Scenario }>,
  s03: () => import("@/data/scenarios/s03.json") as Promise<{ default: Scenario }>,
  s04: () => import("@/data/scenarios/s04.json") as Promise<{ default: Scenario }>,
  s05: () => import("@/data/scenarios/s05.json") as Promise<{ default: Scenario }>,
  s06: () => import("@/data/scenarios/s06.json") as Promise<{ default: Scenario }>,
  s07: () => import("@/data/scenarios/s07.json") as Promise<{ default: Scenario }>,
  s08: () => import("@/data/scenarios/s08.json") as Promise<{ default: Scenario }>,
  s09: () => import("@/data/scenarios/s09.json") as Promise<{ default: Scenario }>,
  s10: () => import("@/data/scenarios/s10.json") as Promise<{ default: Scenario }>,
  s11: () => import("@/data/scenarios/s11.json") as Promise<{ default: Scenario }>,
  s12: () => import("@/data/scenarios/s12.json") as Promise<{ default: Scenario }>,
};

function buildGenericScenario(version: string, locale: string): Scenario {
  if (locale === "zh") {
    const zh: Record<string, Scenario> = {
      s07: {
        version,
        title: "权限系统",
        description: "先把模型意图送进权限闸门，再决定允许、拒绝还是询问用户。",
        steps: [
          {
            type: "user_message",
            content: "请直接删除整个 build 目录，然后重新生成。",
            annotation: "模型会尝试执行带破坏性的文件系统操作。",
          },
          {
            type: "system_event",
            content: "permission_check(action=delete, target=build/, risk=high, mode=ask)",
            annotation: "权限层先把原始 tool call 规范化成统一意图对象。",
          },
          {
            type: "tool_call",
            toolName: "request_permission",
            content: "{ action: 'delete', target: 'build/', reason: 'high-risk filesystem mutation' }",
            annotation: "高风险操作进入 ask 分支，而不是直接落到 shell。",
          },
          {
            type: "tool_result",
            toolName: "request_permission",
            content: "User denied destructive delete. Suggest safer alternative.",
            annotation: "拒绝结果也会回写到主循环，让模型据此重新规划。",
          },
          {
            type: "assistant_text",
            content: "我不会直接删除整个 build 目录。更安全的做法是只清理生成产物，或先列出待删除文件让你确认。",
            annotation: "模型根据 deny 结果调整方案，而不是假装执行成功。",
          },
        ],
      },
      s08: {
        version,
        title: "Hook 系统",
        description: "主循环保持稳定，日志、审计、追踪等旁路逻辑通过生命周期 Hook 挂接。",
        steps: [
          {
            type: "user_message",
            content: "修复登录页的表单校验，并把修改过程记录下来。",
            annotation: "任务既需要执行工具，也需要旁路审计信息。",
          },
          {
            type: "system_event",
            content: "emit pre_tool(tool=edit_file, path=ui/login.tsx)",
            annotation: "在真正调用工具前，循环发出统一生命周期事件。",
          },
          {
            type: "tool_call",
            toolName: "edit_file",
            content: "ui/login.tsx\n---\nvalidateEmail(value)\n-> validateEmail(value.trim())",
            annotation: "主流程只负责执行工具本身。",
          },
          {
            type: "system_event",
            content: "hook[audit_log].append({ tool: 'edit_file', path: 'ui/login.tsx', status: 'ok' })",
            annotation: "审计 Hook 通过事件拿到结构化信息，不需要改 edit_file 实现。",
          },
          {
            type: "assistant_text",
            content: "登录页校验已修复，审计记录也已追加到日志通道。",
            annotation: "Hook 让附加能力围绕主循环扩展，而不是侵入主循环。",
          },
        ],
      },
      s09: {
        version,
        title: "Memory 系统",
        description: "只把跨会话还需要的事实写入长期记忆，当前过程仍由上下文承担。",
        steps: [
          {
            type: "user_message",
            content: "以后默认都用 pnpm，不要再用 npm。",
            annotation: "这是用户偏好，属于跨会话事实。",
          },
          {
            type: "system_event",
            content: "memory_load(scope=user, keys=['package_manager_preference']) -> none",
            annotation: "模型调用前先加载相关长期记忆。",
          },
          {
            type: "tool_call",
            toolName: "memory_write",
            content: "{ key: 'package_manager_preference', value: 'pnpm', reason: 'user explicit preference' }",
            annotation: "任务结束后，把可复用事实提炼写回 memory。",
          },
          {
            type: "tool_result",
            toolName: "memory_write",
            content: "Stored durable memory: package_manager_preference=pnpm",
            annotation: "长期记忆写入完成，后续会话可直接加载。",
          },
          {
            type: "assistant_text",
            content: "已记录。之后涉及包管理命令时，我会默认优先使用 pnpm。",
            annotation: "Memory 保存的是稳定事实，而不是整段原始对话。",
          },
        ],
      },
      s10: {
        version,
        title: "System Prompt",
        description: "系统输入由多段信息按顺序装配，而不是一整块不可见的大字符串。",
        steps: [
          {
            type: "user_message",
            content: "帮我检查这个仓库里和支付有关的实现风险。",
            annotation: "运行时需要把角色、目录、工具、记忆等一起装到模型输入里。",
          },
          {
            type: "system_event",
            content: "prompt_build = role_policy + workspace_state + tool_catalog + memory_context + task_focus",
            annotation: "Prompt pipeline 明确展示了输入由哪些片段构成。",
          },
          {
            type: "tool_call",
            toolName: "preview_prompt",
            content: "[role_policy]\nYou are a coding agent...\n[workspace_state]\nrepo=payments-app\n[tool_catalog]\nread_file, rg, ...",
            annotation: "这一步强调“系统输入是被构建出来的”。",
          },
          {
            type: "tool_result",
            toolName: "preview_prompt",
            content: "Prompt sections assembled successfully (5 sections, 2217 chars)",
            annotation: "只有装配完成后，模型才看到最终输入。",
          },
          {
            type: "assistant_text",
            content: "我会先根据当前仓库状态和可用工具聚焦支付模块，再逐步检查边界、校验和失败处理逻辑。",
            annotation: "模型的行为来自有结构的输入流水线，而不是一段神秘提示词。",
          },
        ],
      },
      s11: {
        version,
        title: "错误恢复",
        description: "恢复分支必须可解释，失败原因也要成为模型后续可见的状态。",
        steps: [
          {
            type: "user_message",
            content: "运行测试并修复失败用例。",
            annotation: "这是一个常见会触发工具异常或超时的任务。",
          },
          {
            type: "tool_call",
            toolName: "bash",
            content: "pytest tests/auth/test_login.py -q",
            annotation: "主循环先正常执行工具。",
          },
          {
            type: "tool_result",
            toolName: "bash",
            content: "Error: Timeout after 120s",
            annotation: "工具失败后，系统不能只是把错误静默吞掉。",
          },
          {
            type: "system_event",
            content: "recovery_branch(reason=timeout, strategy=retry_with_narrow_scope, attempts=1/2)",
            annotation: "恢复层把失败分类，并写出为什么要继续。",
          },
          {
            type: "assistant_text",
            content: "完整测试超时了。我先缩小到认证模块的失败用例重试，再根据更小范围的结果定位问题。",
            annotation: "恢复理由进入上下文后，模型才能稳定地选择下一步。",
          },
        ],
      },
      s12: {
        version,
        title: "任务系统",
        description: "任务板把工作目标变成持久记录，并用依赖关系控制何时解锁后续工作。",
        steps: [
          {
            type: "user_message",
            content: "把支付模块重构拆成几个可持续推进的任务。",
            annotation: "这里要创建的是 durable task records，而不是一次会话里的 todo 文本。",
          },
          {
            type: "tool_call",
            toolName: "task_create",
            content: "{ id: 'task-auth-migrate', title: '迁移鉴权层', blocks: ['task-payment-adapter'] }",
            annotation: "任务记录会显式声明依赖和后继关系。",
          },
          {
            type: "tool_result",
            toolName: "task_create",
            content: "Created task-auth-migrate (status=pending, blocks=1)",
            annotation: "任务板现在知道这项工作存在，并且后续节点暂时被它阻塞。",
          },
          {
            type: "system_event",
            content: "task_complete(task-auth-migrate) -> unlock(task-payment-adapter)",
            annotation: "完成一个节点后，系统会检查依赖并解锁后续节点。",
          },
          {
            type: "assistant_text",
            content: "我先把重构拆成持久任务节点。这样后续工作不是靠记忆硬撑，而是由任务板持续推进。",
            annotation: "教学重点是 durable graph，而不是会话内提醒清单。",
          },
        ],
      },
      s13: {
        version,
        title: "后台任务",
        description: "慢命令进入 runtime record，完整输出落盘，下一轮再用通知把结果带回主循环。",
        steps: [
          {
            type: "user_message",
            content: "后台跑完整测试，同时先继续整理失败模块的文件结构。",
            annotation: "这是典型的前台继续推进、后台慢执行场景。",
          },
          {
            type: "tool_call",
            toolName: "background_run",
            content: "{ command: 'pytest -q', task_id: 'rt_42' }",
            annotation: "主循环先创建 runtime task，而不是同步等待测试跑完。",
          },
          {
            type: "system_event",
            content: "runtime_task_saved(id=rt_42, status=running, output_file=.runtime-tasks/rt_42.log)",
            annotation: "运行记录和完整输出位置被单独保存，和 task goal 分层。",
          },
          {
            type: "system_event",
            content: "notification_drain -> [bg:rt_42] failed preview='3 tests failing in payments/test_retry.py'",
            annotation: "下一轮前先把 preview 注入上下文，而不是把整份日志直接塞进 prompt。",
          },
          {
            type: "assistant_text",
            content: "后台测试已经回来了，我先根据失败摘要聚焦到 retry 用例，必要时再去读完整日志文件。",
            annotation: "notification 负责提醒，output_file 负责保存原文。",
          },
        ],
      },
      s14: {
        version,
        title: "Cron 调度",
        description: "时间规则只负责触发，真正执行仍然交给后台运行时。",
        steps: [
          {
            type: "user_message",
            content: "每天凌晨 2 点自动运行仓库健康检查。",
            annotation: "用户并没有直接请求一次执行，而是在创建时间触发规则。",
          },
          {
            type: "tool_call",
            toolName: "cron_schedule_create",
            content: "{ name: 'nightly-health-check', cron: '0 2 * * *', task_template: 'repo_health_check' }",
            annotation: "Cron 记录的是触发规则和任务模板。",
          },
          {
            type: "system_event",
            content: "cron_tick -> rule matched -> runtime_task_spawn(name='repo_health_check')",
            annotation: "时间命中后，调度器生成 runtime task，而不是直接执行业务逻辑。",
          },
          {
            type: "tool_result",
            toolName: "runtime_task_spawn",
            content: "Queued background runtime task #42 for nightly-health-check",
            annotation: "真正执行交给后台任务层接管。",
          },
          {
            type: "assistant_text",
            content: "规则已建立。之后每天 02:00 会先触发 runtime task，再由后台执行层完成实际检查。",
            annotation: "教学重点是调度触发面和执行运行时的职责分离。",
          },
        ],
      },
      s15: {
        version,
        title: "Agent Teams",
        description: "队友是长期存在的角色，有自己的名字、身份和 inbox，而不是一次性 subagent。",
        steps: [
          {
            type: "user_message",
            content: "你负责主线，我想让一个专门看测试、一个专门看重构。",
            annotation: "这时系统需要的是持久队友，而不是短命委派。",
          },
          {
            type: "tool_call",
            toolName: "spawn_teammate",
            content: "{ name: 'alice', role: 'test-specialist', prompt: 'Own the failing tests.' }",
            annotation: "TeammateManager 为队友分配长期身份和职责。",
          },
          {
            type: "tool_result",
            toolName: "spawn_teammate",
            content: "Spawned 'alice' (role: test-specialist)",
            annotation: "队友进入 roster，后续可被反复派活。",
          },
          {
            type: "tool_call",
            toolName: "send_message",
            content: "{ to: 'alice', content: '先检查 retry 相关失败用例。' }",
            annotation: "协作通过 inbox 边界发生，而不是共用一段 messages[]。",
          },
          {
            type: "assistant_text",
            content: "测试队友已经接入团队。之后我可以继续点名协作，而不是每次都临时重新创建子任务执行者。",
            annotation: "长期身份和独立 inbox 才是这一章的关键增量。",
          },
        ],
      },
      s16: {
        version,
        title: "团队协议",
        description: "审批和关机这类协作必须带 request_id 和 request record，而不是只靠自由文本往返。",
        steps: [
          {
            type: "user_message",
            content: "在 alice 真正改鉴权层前，先让她提交计划给我审批。",
            annotation: "高风险协作需要结构化 request / response。",
          },
          {
            type: "tool_call",
            toolName: "plan_approval",
            content: "{ request_id: 'req_91', from: 'alice', plan: 'Refactor auth boundary before retries.' }",
            annotation: "协议消息会把 request_id 和 payload 一起发送。",
          },
          {
            type: "system_event",
            content: "request_record_saved(id=req_91, kind=plan_approval, status=pending)",
            annotation: "真正被追踪的是 durable request record，而不只是临时内存字典。",
          },
          {
            type: "tool_result",
            toolName: "plan_review",
            content: "{ request_id: 'req_91', approve: true, feedback: 'Proceed with adapter boundary first.' }",
            annotation: "收到明确响应后，请求状态从 pending 进入 approved。",
          },
          {
            type: "assistant_text",
            content: "这次协作已经有编号和状态了。后面无论继续、拒绝还是超时，都能准确追到同一个请求记录。",
            annotation: "request_id + request record 才是协议层真正的新结构。",
          },
        ],
      },
      s17: {
        version,
        title: "自治 Agent",
        description: "队友在空闲时可以轮询共享状态，自行认领工作，再恢复到正确上下文继续推进。",
        steps: [
          {
            type: "system_event",
            content: "idle_cycle(worker='alice') -> poll inbox + task board",
            annotation: "自治的入口不是魔法，而是稳定的 idle polling。",
          },
          {
            type: "system_event",
            content: "claimable_task_found(task='task-payment-adapter', policy='test-specialist may claim retry-related work')",
            annotation: "只有符合 self-claim 规则的工作才会被队友主动认领。",
          },
          {
            type: "tool_call",
            toolName: "claim_task",
            content: "{ teammate: 'alice', task_id: 'task-payment-adapter' }",
            annotation: "认领动作本身也要回写状态，避免多个队友撞车。",
          },
          {
            type: "tool_result",
            toolName: "claim_task",
            content: "alice claimed task-payment-adapter and resumed prior context",
            annotation: "系统根据任务状态和角色状态恢复执行，而不是凭空继续。",
          },
          {
            type: "assistant_text",
            content: "alice 已经在没有新指令的情况下接手后续工作了，但她仍然受 claim policy 和团队状态约束。",
            annotation: "自治的关键是可控地 self-claim 和 self-resume。",
          },
        ],
      },
      s18: {
        version,
        title: "Worktree 隔离",
        description: "任务被绑定到独立执行车道，进入各自目录执行，再带着 closeout 语义回到主系统。",
        steps: [
          {
            type: "user_message",
            content: "给重构任务开一个隔离目录，避免和主线修改互相干扰。",
            annotation: "这里新增的是 execution lane，不是新的任务类型。",
          },
          {
            type: "tool_call",
            toolName: "worktree_create",
            content: "{ task_id: 'task-auth-migrate', lane: 'wt-auth-migrate' }",
            annotation: "系统先分配 worktree，并把它和任务记录绑定。",
          },
          {
            type: "system_event",
            content: "worktree_event(type=create, task_id=task-auth-migrate, path=.worktrees/wt-auth-migrate)",
            annotation: "执行车道的生命周期事件被显式写出来，方便观察。",
          },
          {
            type: "tool_result",
            toolName: "worktree_closeout",
            content: "{ path: '.worktrees/wt-auth-migrate', keep: true, reason: 'needs follow-up review' }",
            annotation: "closeout 决定这个车道是保留还是回收，而不是简单结束命令。",
          },
          {
            type: "assistant_text",
            content: "这项工作现在在独立车道里推进，主线目录不会被混写，后续也能根据 closeout 状态决定是否继续保留该环境。",
            annotation: "task goal 和 isolated lane 的分层是这一章的主心智。",
          },
        ],
      },
      s19: {
        version,
        title: "MCP 与 Plugin",
        description: "外部能力进入系统后，也应遵循与本地工具一致的发现、路由、授权和结果回写流程。",
        steps: [
          {
            type: "user_message",
            content: "读取 Figma 设计稿里的按钮规范，然后同步到当前组件库。",
            annotation: "这是一个典型需要外部能力接入的请求。",
          },
          {
            type: "system_event",
            content: "capability_router.resolve(['native_tools', 'plugin_registry', 'mcp_servers']) -> mcp:figma.inspect",
            annotation: "系统先在统一 capability bus 上做能力发现与路由选择。",
          },
          {
            type: "tool_call",
            toolName: "mcp.figma.inspect",
            content: "{ fileId: 'design-123', node: 'PrimaryButton' }",
            annotation: "外部 MCP 能力被当成标准 capability 调用。",
          },
          {
            type: "tool_result",
            toolName: "mcp.figma.inspect",
            content: "{ padding: '12x18', radius: 10, typography: 'SemiBold 14', states: ['default','hover','disabled'] }",
            annotation: "返回结果先标准化，再回到主循环。",
          },
          {
            type: "assistant_text",
            content: "我已经拿到设计规范。下一步会按统一结果格式，把这些约束映射到当前按钮组件实现里。",
            annotation: "MCP 不是外挂世界，而是被接回同一条 agent 控制平面。",
          },
        ],
      },
    };

    return zh[version] ?? buildFallbackScenario(version, locale);
  }

  if (locale === "ja") {
    const ja: Record<string, Scenario> = {
      s07: {
        version,
        title: "権限システム",
        description: "model の意図をそのまま実行せず、権限ゲートで allow / deny / ask に分岐させます。",
        steps: [
          {
            type: "user_message",
            content: "build ディレクトリをまるごと削除して、全部作り直してください。",
            annotation: "model が破壊的なファイル操作を提案しそうな場面です。",
          },
          {
            type: "system_event",
            content: "permission_check(action=delete, target=build/, risk=high, mode=ask)",
            annotation: "生の tool call は、まず統一された intent object に正規化されます。",
          },
          {
            type: "tool_call",
            toolName: "request_permission",
            content: "{ action: 'delete', target: 'build/', reason: 'high-risk filesystem mutation' }",
            annotation: "高リスク操作は shell へ直行せず、ask 分岐へ入ります。",
          },
          {
            type: "tool_result",
            toolName: "request_permission",
            content: "ユーザーが破壊的な削除を拒否しました。より安全な代替案を提示してください。",
            annotation: "deny 結果も main loop へ戻り、次の再計画材料になります。",
          },
          {
            type: "assistant_text",
            content: "build ディレクトリ全体は直接削除しません。まず生成物だけを安全に掃除するか、削除対象一覧を出して確認します。",
            annotation: "model は deny 結果を見て方針を組み替えます。",
          },
        ],
      },
      s08: {
        version,
        title: "Hook システム",
        description: "main loop は安定したままにし、監査や追跡のような横断処理は lifecycle hook に載せます。",
        steps: [
          {
            type: "user_message",
            content: "ログイン画面のフォーム検証を直して、変更履歴も残してください。",
            annotation: "tool 実行と audit のような横断処理が同時に必要な場面です。",
          },
          {
            type: "system_event",
            content: "emit pre_tool(tool=edit_file, path=ui/login.tsx)",
            annotation: "実際の tool 実行前に、loop が安定した lifecycle event を発火します。",
          },
          {
            type: "tool_call",
            toolName: "edit_file",
            content: "ui/login.tsx\n---\nvalidateEmail(value)\n-> validateEmail(value.trim())",
            annotation: "主処理は tool 本体の実行だけに集中します。",
          },
          {
            type: "system_event",
            content: "hook[audit_log].append({ tool: 'edit_file', path: 'ui/login.tsx', status: 'ok' })",
            annotation: "audit hook は構造化 event から必要情報を取り出します。",
          },
          {
            type: "assistant_text",
            content: "ログイン画面の検証を修正し、監査ログにも今回の変更を追記しました。",
            annotation: "hook は主線を壊さず、loop の周辺機能を増やします。",
          },
        ],
      },
      s09: {
        version,
        title: "Memory システム",
        description: "今後も効く事実だけを長期 memory に残し、現在ターンの詳細は context 側に置きます。",
        steps: [
          {
            type: "user_message",
            content: "今後は npm ではなく、必ず pnpm を使ってください。",
            annotation: "これは一度きりの会話ではなく、次回以降にも効く user preference です。",
          },
          {
            type: "system_event",
            content: "memory_load(scope=user, keys=['package_manager_preference']) -> none",
            annotation: "model 呼び出し前に、関連する長期 memory を読み込みます。",
          },
          {
            type: "tool_call",
            toolName: "memory_write",
            content: "{ key: 'package_manager_preference', value: 'pnpm', reason: 'user explicit preference' }",
            annotation: "再利用価値のある事実だけを抽出して memory へ書き込みます。",
          },
          {
            type: "tool_result",
            toolName: "memory_write",
            content: "長期 memory を保存しました: package_manager_preference=pnpm",
            annotation: "次回の session ではこの事実を先に読み戻せます。",
          },
          {
            type: "assistant_text",
            content: "記録しました。以後、パッケージ管理コマンドでは pnpm を優先して使います。",
            annotation: "memory に残すのは会話全文ではなく、継続価値のある事実です。",
          },
        ],
      },
      s10: {
        version,
        title: "System Prompt",
        description: "system input は見えない巨大文字列ではなく、複数の section を順に組み立てた結果です。",
        steps: [
          {
            type: "user_message",
            content: "このリポジトリの支払い処理まわりの実装リスクを洗い出してください。",
            annotation: "役割、workspace 状態、tool、memory などを一緒に model input へ積む必要があります。",
          },
          {
            type: "system_event",
            content: "prompt_build = role_policy + workspace_state + tool_catalog + memory_context + task_focus",
            annotation: "prompt pipeline は入力がどの section から成るかを可視化します。",
          },
          {
            type: "tool_call",
            toolName: "preview_prompt",
            content: "[role_policy]\nYou are a coding agent...\n[workspace_state]\nrepo=payments-app\n[tool_catalog]\nread_file, rg, ...",
            annotation: "system input は「組み立てられたもの」だと見せるためのプレビューです。",
          },
          {
            type: "tool_result",
            toolName: "preview_prompt",
            content: "Prompt sections assembled successfully (5 sections, 2217 chars)",
            annotation: "組み立てが終わって初めて、model は最終入力を受け取ります。",
          },
          {
            type: "assistant_text",
            content: "まず現在のリポジトリ状態と利用可能な tool を踏まえて支払いモジュールを絞り込み、境界・検証・失敗処理を順に確認します。",
            annotation: "model の振る舞いは、構造化された入力パイプラインから生まれます。",
          },
        ],
      },
      s11: {
        version,
        title: "エラー回復",
        description: "失敗後の分岐には理由を残し、回復そのものを次の推論に見える状態として渡します。",
        steps: [
          {
            type: "user_message",
            content: "テストを実行して、落ちているケースを直してください。",
            annotation: "tool 失敗や timeout が起きやすい典型タスクです。",
          },
          {
            type: "tool_call",
            toolName: "bash",
            content: "pytest tests/auth/test_login.py -q",
            annotation: "まずは通常どおり tool を実行します。",
          },
          {
            type: "tool_result",
            toolName: "bash",
            content: "Error: Timeout after 120s",
            annotation: "失敗を黙って飲み込まず、回復分岐へ明示的に渡します。",
          },
          {
            type: "system_event",
            content: "recovery_branch(reason=timeout, strategy=retry_with_narrow_scope, attempts=1/2)",
            annotation: "失敗理由と次の継続理由を state に書き込みます。",
          },
          {
            type: "assistant_text",
            content: "全体テストは timeout しました。まず認証まわりの失敗ケースだけに絞って再実行し、そこから原因を詰めます。",
            annotation: "継続理由が見えているから、次の行動も説明可能になります。",
          },
        ],
      },
      s12: {
        version,
        title: "タスクシステム",
        description: "作業目標を durable task record に変換し、依存関係で次の仕事を解放します。",
        steps: [
          {
            type: "user_message",
            content: "支払いモジュールのリファクタリングを、継続できる複数の仕事に分解してください。",
            annotation: "ここで作るべきなのは session 内メモではなく durable task node です。",
          },
          {
            type: "tool_call",
            toolName: "task_create",
            content: "{ id: 'task-auth-migrate', title: 'Migrate auth layer', blocks: ['task-payment-adapter'] }",
            annotation: "task record には dependency edge を明示します。",
          },
          {
            type: "tool_result",
            toolName: "task_create",
            content: "Created task-auth-migrate (status=pending, blocks=1)",
            annotation: "task board はこの仕事の存在と依存状態を覚えます。",
          },
          {
            type: "system_event",
            content: "task_complete(task-auth-migrate) -> unlock(task-payment-adapter)",
            annotation: "ある node が終わると、board が依存を見て次ノードを解放します。",
          },
          {
            type: "assistant_text",
            content: "まず durable task node に落としておきます。これで次の作業は記憶頼みではなく、task board 上で継続できます。",
            annotation: "重点は todo text ではなく durable graph です。",
          },
        ],
      },
      s13: {
        version,
        title: "バックグラウンドタスク",
        description: "遅い実行は runtime record と出力ファイルに逃がし、次ターンで notification preview だけを main loop へ戻します。",
        steps: [
          {
            type: "user_message",
            content: "フルテストを裏で走らせつつ、先に失敗モジュールの構造を整理してください。",
            annotation: "前景の作業継続と、裏で遅い処理を走らせる典型場面です。",
          },
          {
            type: "tool_call",
            toolName: "background_run",
            content: "{ command: 'pytest -q', task_id: 'rt_42' }",
            annotation: "同期で待たず、まず runtime task を作成します。",
          },
          {
            type: "system_event",
            content: "runtime_task_saved(id=rt_42, status=running, output_file=.runtime-tasks/rt_42.log)",
            annotation: "実行状態と完全出力の保存先を、goal task と分けて記録します。",
          },
          {
            type: "system_event",
            content: "notification_drain -> [bg:rt_42] failed preview='3 tests failing in payments/test_retry.py'",
            annotation: "次ターン前には preview だけを context へ戻し、全文ログは出力ファイル側に置きます。",
          },
          {
            type: "assistant_text",
            content: "バックグラウンドテスト結果は戻ってきました。まず失敗サマリから retry 系のケースへ絞り、必要なら完全ログを読みます。",
            annotation: "notification は知らせる役、output_file は原文を保持する役です。",
          },
        ],
      },
      s14: {
        version,
        title: "Cron スケジューラ",
        description: "時間規則は trigger だけを担当し、実際の実行は background runtime に渡します。",
        steps: [
          {
            type: "user_message",
            content: "毎日午前 2 時にリポジトリ健全性チェックを自動実行してください。",
            annotation: "これは今すぐ 1 回走らせる依頼ではなく、時間規則を作る依頼です。",
          },
          {
            type: "tool_call",
            toolName: "cron_schedule_create",
            content: "{ name: 'nightly-health-check', cron: '0 2 * * *', task_template: 'repo_health_check' }",
            annotation: "cron record は trigger rule と task template を保存します。",
          },
          {
            type: "system_event",
            content: "cron_tick -> rule matched -> runtime_task_spawn(name='repo_health_check')",
            annotation: "時間条件が一致すると、scheduler は runtime task を生成します。",
          },
          {
            type: "tool_result",
            toolName: "runtime_task_spawn",
            content: "Queued background runtime task #42 for nightly-health-check",
            annotation: "実際の作業は background task layer が引き継ぎます。",
          },
          {
            type: "assistant_text",
            content: "ルールを登録しました。今後は毎日 02:00 に runtime task を起こし、その後の実行は background layer が担当します。",
            annotation: "教えるべき要点は、trigger 面と execution 面の責務分離です。",
          },
        ],
      },
      s15: {
        version,
        title: "Agent Teams",
        description: "チームメイトは長く存在する役割であり、毎回作り直す一時 subagent ではありません。",
        steps: [
          {
            type: "user_message",
            content: "主線はあなたが担当して、テスト専任とリファクタ専任の 2 人を置きたいです。",
            annotation: "必要なのは一回きりの委譲ではなく、継続的に残る teammate です。",
          },
          {
            type: "tool_call",
            toolName: "spawn_teammate",
            content: "{ name: 'alice', role: 'test-specialist', prompt: 'Own the failing tests.' }",
            annotation: "TeammateManager は名前・役割・状態を持つ長期メンバーを作ります。",
          },
          {
            type: "tool_result",
            toolName: "spawn_teammate",
            content: "Spawned 'alice' (role: test-specialist)",
            annotation: "新しい teammate は roster に入り、後続ラウンドでも再利用できます。",
          },
          {
            type: "tool_call",
            toolName: "send_message",
            content: "{ to: 'alice', content: '先に retry 系の失敗ケースを確認してください。' }",
            annotation: "協調は inbox 境界を通して行い、1 本の messages[] を共有しません。",
          },
          {
            type: "assistant_text",
            content: "テスト担当の teammate をチームへ追加しました。以後は毎回作り直さず、このメンバーへ継続して仕事を振れます。",
            annotation: "この章の増分は、長期 identity と独立 inbox です。",
          },
        ],
      },
      s16: {
        version,
        title: "チームプロトコル",
        description: "承認や停止のような協調は、自由文ではなく request_id と request record を伴う構造化プロトコルで扱います。",
        steps: [
          {
            type: "user_message",
            content: "alice が認証境界を本当に触る前に、まず作業計画を私に承認依頼してください。",
            annotation: "高リスク協調では request / response を構造化する必要があります。",
          },
          {
            type: "tool_call",
            toolName: "plan_approval",
            content: "{ request_id: 'req_91', from: 'alice', plan: 'Refactor auth boundary before retries.' }",
            annotation: "protocol message は request_id と payload を一緒に送ります。",
          },
          {
            type: "system_event",
            content: "request_record_saved(id=req_91, kind=plan_approval, status=pending)",
            annotation: "追跡対象は durable request record であり、単なる一時メモではありません。",
          },
          {
            type: "tool_result",
            toolName: "plan_review",
            content: "{ request_id: 'req_91', approve: true, feedback: 'Proceed with adapter boundary first.' }",
            annotation: "response が返ると request 状態が pending から approved へ進みます。",
          },
          {
            type: "assistant_text",
            content: "この協調には番号と状態が付いたので、承認・拒否・タイムアウトのどれになっても同じ request を追跡できます。",
            annotation: "protocol 層の新しい中核は request_id と request record です。",
          },
        ],
      },
      s17: {
        version,
        title: "自律 Agent",
        description: "idle な teammate は共有状態を見て自分で仕事を claim し、必要な state を復元してから再開します。",
        steps: [
          {
            type: "system_event",
            content: "idle_cycle(worker='alice') -> poll inbox + task board",
            annotation: "自律の入口は魔法ではなく、安定した idle polling です。",
          },
          {
            type: "system_event",
            content: "claimable_task_found(task='task-payment-adapter', policy='test-specialist may claim retry-related work')",
            annotation: "self-claim は常に policy 境界の内側でのみ起こります。",
          },
          {
            type: "tool_call",
            toolName: "claim_task",
            content: "{ teammate: 'alice', task_id: 'task-payment-adapter' }",
            annotation: "claim 動作自体を state に残し、複数 worker の衝突を防ぎます。",
          },
          {
            type: "tool_result",
            toolName: "claim_task",
            content: "alice claimed task-payment-adapter and resumed prior context",
            annotation: "再開は task / role / mailbox state を見える形で復元してから行います。",
          },
          {
            type: "assistant_text",
            content: "alice は新しい指示がなくても後続作業を引き取りましたが、claim policy と team state の範囲内でのみ動いています。",
            annotation: "この章の本質は、制御された self-claim と self-resume です。",
          },
        ],
      },
      s18: {
        version,
        title: "Worktree 分離",
        description: "task は goal を持ち、worktree はその task が走る execution lane を持ちます。",
        steps: [
          {
            type: "user_message",
            content: "リファクタ作業は隔離ディレクトリで進めて、主線の変更と混ざらないようにしてください。",
            annotation: "増えるのは新しい task 種別ではなく、独立した execution lane です。",
          },
          {
            type: "tool_call",
            toolName: "worktree_create",
            content: "{ task_id: 'task-auth-migrate', lane: 'wt-auth-migrate' }",
            annotation: "system は worktree を作り、task あるいは runtime slot と結び付けます。",
          },
          {
            type: "system_event",
            content: "worktree_event(type=create, task_id=task-auth-migrate, path=.worktrees/wt-auth-migrate)",
            annotation: "lane の lifecycle event を見える形で残します。",
          },
          {
            type: "tool_result",
            toolName: "worktree_closeout",
            content: "{ path: '.worktrees/wt-auth-migrate', keep: true, reason: 'needs follow-up review' }",
            annotation: "closeout は keep / remove の意味を明示し、単なる終了にしません。",
          },
          {
            type: "assistant_text",
            content: "この作業は独立した lane に入りました。主線ディレクトリを汚さず進められ、あとで保持するか回収するかも closeout で判断できます。",
            annotation: "この章の心智は、goal task と isolated lane を分けることです。",
          },
        ],
      },
      s19: {
        version,
        title: "MCP と Plugin",
        description: "外部 capability も native tool と同じく、発見・ルーティング・権限・結果正規化の主線へ戻します。",
        steps: [
          {
            type: "user_message",
            content: "Figma のデザイン稿からボタン仕様を読んで、今のコンポーネントへ反映してください。",
            annotation: "外部 capability 接続が必要な典型リクエストです。",
          },
          {
            type: "system_event",
            content: "capability_router.resolve(['native_tools', 'plugin_registry', 'mcp_servers']) -> mcp:figma.inspect",
            annotation: "system は統一 capability bus 上で discovery と routing を行います。",
          },
          {
            type: "tool_call",
            toolName: "mcp.figma.inspect",
            content: "{ fileId: 'design-123', node: 'PrimaryButton' }",
            annotation: "外部 MCP capability も標準 capability として呼び出されます。",
          },
          {
            type: "tool_result",
            toolName: "mcp.figma.inspect",
            content: "{ padding: '12x18', radius: 10, typography: 'SemiBold 14', states: ['default','hover','disabled'] }",
            annotation: "remote response は正規化されてから main loop に戻ります。",
          },
          {
            type: "assistant_text",
            content: "デザイン仕様を取得しました。次はこの制約を現在のボタン実装へマッピングし、既存 UI と整合させます。",
            annotation: "MCP は外の別世界ではなく、同じ control plane へ接続される能力層です。",
          },
        ],
      },
    };

    return ja[version] ?? buildFallbackScenario(version, locale);
  }

  const en: Record<string, Scenario> = {
    s07: {
      version,
      title: "Permission System",
      description: "Intent passes through a permission gate before it becomes execution.",
      steps: [
        {
          type: "user_message",
          content: "Delete the whole build directory and regenerate everything.",
          annotation: "The model is about to propose a destructive action.",
        },
        {
          type: "system_event",
          content: "permission_check(action=delete, target=build/, risk=high, mode=ask)",
          annotation: "The raw tool request is normalized into a structured intent first.",
        },
        {
          type: "tool_call",
          toolName: "request_permission",
          content: "{ action: 'delete', target: 'build/', reason: 'high-risk filesystem mutation' }",
          annotation: "High-risk work goes to ask-mode instead of executing immediately.",
        },
        {
          type: "tool_result",
          toolName: "request_permission",
          content: "User denied destructive delete. Suggest safer alternative.",
          annotation: "The denial is written back into the loop as visible state.",
        },
        {
          type: "assistant_text",
          content: "I will not delete the entire build directory directly. A safer option is to clear generated artifacts or show the exact files first.",
          annotation: "The model replans from the deny result instead of pretending it succeeded.",
        },
      ],
    },
    s08: {
      version,
      title: "Hook System",
      description: "Lifecycle hooks add side effects around the loop without rewriting the loop.",
      steps: [
        {
          type: "user_message",
          content: "Fix login-form validation and keep an audit trail of the change.",
          annotation: "The task needs both execution and side-channel bookkeeping.",
        },
        {
          type: "system_event",
          content: "emit pre_tool(tool=edit_file, path=ui/login.tsx)",
          annotation: "The loop emits a normalized lifecycle event before the tool runs.",
        },
        {
          type: "tool_call",
          toolName: "edit_file",
          content: "ui/login.tsx\n---\nvalidateEmail(value)\n-> validateEmail(value.trim())",
          annotation: "The core path still only executes the requested tool.",
        },
        {
          type: "system_event",
          content: "hook[audit_log].append({ tool: 'edit_file', path: 'ui/login.tsx', status: 'ok' })",
          annotation: "The audit hook consumes the event without modifying tool code.",
        },
        {
          type: "assistant_text",
          content: "The validation fix is in place, and the audit channel now contains the change record.",
          annotation: "Hooks grow the system around the loop instead of invading the loop.",
        },
      ],
    },
    s09: {
      version,
      title: "Memory System",
      description: "Only durable cross-session facts belong in memory.",
      steps: [
        {
          type: "user_message",
          content: "From now on, prefer pnpm instead of npm.",
          annotation: "This is durable user preference, not temporary task state.",
        },
        {
          type: "system_event",
          content: "memory_load(scope=user, keys=['package_manager_preference']) -> none",
          annotation: "Relevant long-term memory is loaded before prompt assembly.",
        },
        {
          type: "tool_call",
          toolName: "memory_write",
          content: "{ key: 'package_manager_preference', value: 'pnpm', reason: 'user explicit preference' }",
          annotation: "After the task, durable facts are extracted and written back.",
        },
        {
          type: "tool_result",
          toolName: "memory_write",
          content: "Stored durable memory: package_manager_preference=pnpm",
          annotation: "The fact is now available to future sessions.",
        },
        {
          type: "assistant_text",
          content: "Recorded. I will default to pnpm for future package-manager commands.",
          annotation: "Memory stores stable facts, not whole conversations.",
        },
      ],
    },
    s10: {
      version,
      title: "System Prompt",
      description: "The system input is assembled from ordered sections instead of one giant hidden string.",
      steps: [
        {
          type: "user_message",
          content: "Review the implementation risks around payments in this repo.",
          annotation: "The model needs role policy, workspace state, tools, and memory together.",
        },
        {
          type: "system_event",
          content: "prompt_build = role_policy + workspace_state + tool_catalog + memory_context + task_focus",
          annotation: "The prompt pipeline shows which sections make up the final model input.",
        },
        {
          type: "tool_call",
          toolName: "preview_prompt",
          content: "[role_policy]\nYou are a coding agent...\n[workspace_state]\nrepo=payments-app\n[tool_catalog]\nread_file, rg, ...",
          annotation: "This makes the assembled structure visible to the learner.",
        },
        {
          type: "tool_result",
          toolName: "preview_prompt",
          content: "Prompt sections assembled successfully (5 sections, 2217 chars)",
          annotation: "Only after assembly is the final input ready for the model.",
        },
        {
          type: "assistant_text",
          content: "I will inspect payment boundaries, validation, and failure handling based on the current repo state and tool context.",
          annotation: "The model behavior comes from a structured input pipeline.",
        },
      ],
    },
    s11: {
      version,
      title: "Error Recovery",
      description: "Recovery branches stay explicit so failures can turn into continued work instead of silent loops.",
      steps: [
        {
          type: "user_message",
          content: "Run the tests and fix the failing cases.",
          annotation: "This task commonly triggers tool failures or timeouts.",
        },
        {
          type: "tool_call",
          toolName: "bash",
          content: "pytest tests/auth/test_login.py -q",
          annotation: "The tool runs normally first.",
        },
        {
          type: "tool_result",
          toolName: "bash",
          content: "Error: Timeout after 120s",
          annotation: "The system cannot just swallow the failure.",
        },
        {
          type: "system_event",
          content: "recovery_branch(reason=timeout, strategy=retry_with_narrow_scope, attempts=1/2)",
          annotation: "Recovery classifies the reason and records why execution will continue.",
        },
        {
          type: "assistant_text",
          content: "The full test run timed out. I will retry on the narrower auth subset and use that result to localize the issue.",
          annotation: "The recovery reason becomes visible state for the next step.",
        },
      ],
    },
    s12: {
      version,
      title: "Task System",
      description: "The task board turns work goals into durable records and uses dependency edges to unlock later work.",
      steps: [
        {
          type: "user_message",
          content: "Break the payment refactor into a few durable tasks we can keep advancing.",
          annotation: "This creates durable task records, not just a per-session todo list.",
        },
        {
          type: "tool_call",
          toolName: "task_create",
          content: "{ id: 'task-auth-migrate', title: 'Migrate auth layer', blocks: ['task-payment-adapter'] }",
          annotation: "The task record explicitly declares dependency and unlock edges.",
        },
        {
          type: "tool_result",
          toolName: "task_create",
          content: "Created task-auth-migrate (status=pending, blocks=1)",
          annotation: "The board now knows the work exists and what it is blocking.",
        },
        {
          type: "system_event",
          content: "task_complete(task-auth-migrate) -> unlock(task-payment-adapter)",
          annotation: "Completing one node checks dependencies and unlocks downstream work.",
        },
        {
          type: "assistant_text",
          content: "I am turning the refactor into durable task nodes so the system can keep progressing without relying on conversational memory alone.",
          annotation: "The teaching focus is the durable graph, not a temporary reminder list.",
        },
      ],
    },
    s13: {
      version,
      title: "Background Tasks",
      description: "Slow commands get a runtime record, full output goes to disk, and notifications carry a preview back on a later turn.",
      steps: [
        {
          type: "user_message",
          content: "Run the full test suite in the background while we keep organizing the failing module.",
          annotation: "This is the classic foreground-progress plus background-execution case.",
        },
        {
          type: "tool_call",
          toolName: "background_run",
          content: "{ command: 'pytest -q', task_id: 'rt_42' }",
          annotation: "The loop creates runtime work instead of blocking on the full command.",
        },
        {
          type: "system_event",
          content: "runtime_task_saved(id=rt_42, status=running, output_file=.runtime-tasks/rt_42.log)",
          annotation: "The runtime record and full output path are persisted separately from the task goal.",
        },
        {
          type: "system_event",
          content: "notification_drain -> [bg:rt_42] failed preview='3 tests failing in payments/test_retry.py'",
          annotation: "Only a preview returns to context; the full log stays on disk.",
        },
        {
          type: "assistant_text",
          content: "The background run has reported back. I will use the preview to focus the next step and read the full log only if needed.",
          annotation: "Notifications alert the loop; output files keep the heavy detail.",
        },
      ],
    },
    s14: {
      version,
      title: "Cron Scheduler",
      description: "Time rules trigger runtime work; execution still belongs to the runtime layer.",
      steps: [
        {
          type: "user_message",
          content: "Run a repo health check every day at 2:00 AM.",
          annotation: "The user is creating a time trigger, not directly starting one execution.",
        },
        {
          type: "tool_call",
          toolName: "cron_schedule_create",
          content: "{ name: 'nightly-health-check', cron: '0 2 * * *', task_template: 'repo_health_check' }",
          annotation: "Cron stores a rule and a task template.",
        },
        {
          type: "system_event",
          content: "cron_tick -> rule matched -> runtime_task_spawn(name='repo_health_check')",
          annotation: "A time hit creates runtime work instead of running the business logic directly.",
        },
        {
          type: "tool_result",
          toolName: "runtime_task_spawn",
          content: "Queued background runtime task #42 for nightly-health-check",
          annotation: "The background runtime takes over the actual execution.",
        },
        {
          type: "assistant_text",
          content: "The schedule is active. Every day at 02:00 it will spawn a runtime task and let the background layer execute it.",
          annotation: "The teaching boundary is trigger-time vs execution-time responsibility.",
        },
      ],
    },
    s15: {
      version,
      title: "Agent Teams",
      description: "Teammates are long-lived workers with names, roles, and inboxes, not disposable subagents.",
      steps: [
        {
          type: "user_message",
          content: "Keep me on the mainline and add one specialist for tests and one for refactors.",
          annotation: "This requires persistent teammates rather than one-shot delegation.",
        },
        {
          type: "tool_call",
          toolName: "spawn_teammate",
          content: "{ name: 'alice', role: 'test-specialist', prompt: 'Own the failing tests.' }",
          annotation: "The team manager assigns a durable identity and role.",
        },
        {
          type: "tool_result",
          toolName: "spawn_teammate",
          content: "Spawned 'alice' (role: test-specialist)",
          annotation: "The teammate joins the roster and can be reused later.",
        },
        {
          type: "tool_call",
          toolName: "send_message",
          content: "{ to: 'alice', content: 'Start with the retry-related failures.' }",
          annotation: "Coordination travels through inbox boundaries instead of one shared messages[] buffer.",
        },
        {
          type: "assistant_text",
          content: "The test specialist is now part of the standing team, so I can keep assigning work without recreating a child worker each time.",
          annotation: "Persistent identity and inboxes are the key chapter boundary.",
        },
      ],
    },
    s16: {
      version,
      title: "Team Protocols",
      description: "Approvals and shutdown flows need request IDs and durable request records, not only free-form messages.",
      steps: [
        {
          type: "user_message",
          content: "Before alice changes the auth boundary, make her submit a plan for approval.",
          annotation: "Risky coordination needs a structured request / response flow.",
        },
        {
          type: "tool_call",
          toolName: "plan_approval",
          content: "{ request_id: 'req_91', from: 'alice', plan: 'Refactor auth boundary before retries.' }",
          annotation: "The protocol envelope carries a request_id and payload together.",
        },
        {
          type: "system_event",
          content: "request_record_saved(id=req_91, kind=plan_approval, status=pending)",
          annotation: "The durable request record is the real thing being tracked.",
        },
        {
          type: "tool_result",
          toolName: "plan_review",
          content: "{ request_id: 'req_91', approve: true, feedback: 'Proceed with adapter boundary first.' }",
          annotation: "The explicit response moves state from pending to approved.",
        },
        {
          type: "assistant_text",
          content: "This collaboration now has a stable request record. Future approval, rejection, or timeout can all resolve against the same ID.",
          annotation: "request_id plus durable state is the actual protocol upgrade.",
        },
      ],
    },
    s17: {
      version,
      title: "Autonomous Agents",
      description: "Workers become autonomous when they can poll for eligible work, claim it, and resume with the right state.",
      steps: [
        {
          type: "system_event",
          content: "idle_cycle(worker='alice') -> poll inbox + task board",
          annotation: "Autonomy begins with stable idle polling, not with magic.",
        },
        {
          type: "system_event",
          content: "claimable_task_found(task='task-payment-adapter', policy='test-specialist may claim retry-related work')",
          annotation: "Only work allowed by the self-claim policy becomes eligible.",
        },
        {
          type: "tool_call",
          toolName: "claim_task",
          content: "{ teammate: 'alice', task_id: 'task-payment-adapter' }",
          annotation: "The claim action itself writes state so multiple workers do not collide.",
        },
        {
          type: "tool_result",
          toolName: "claim_task",
          content: "alice claimed task-payment-adapter and resumed prior context",
          annotation: "The worker resumes from visible task and role state, not from nowhere.",
        },
        {
          type: "assistant_text",
          content: "alice has picked up the next step without a new user turn, but still remains bounded by claim rules and team state.",
          annotation: "Controlled self-claim and self-resume are the important autonomy mechanics.",
        },
      ],
    },
    s18: {
      version,
      title: "Worktree Isolation",
      description: "Tasks get their own execution lanes, run in isolated directories, and return through explicit closeout semantics.",
      steps: [
        {
          type: "user_message",
          content: "Give the refactor task its own isolated directory so it does not interfere with the mainline.",
          annotation: "The new object here is an execution lane, not a new task type.",
        },
        {
          type: "tool_call",
          toolName: "worktree_create",
          content: "{ task_id: 'task-auth-migrate', lane: 'wt-auth-migrate' }",
          annotation: "The system allocates a worktree and binds it to the task record.",
        },
        {
          type: "system_event",
          content: "worktree_event(type=create, task_id=task-auth-migrate, path=.worktrees/wt-auth-migrate)",
          annotation: "Execution-lane lifecycle events are emitted explicitly.",
        },
        {
          type: "tool_result",
          toolName: "worktree_closeout",
          content: "{ path: '.worktrees/wt-auth-migrate', keep: true, reason: 'needs follow-up review' }",
          annotation: "Closeout decides whether the lane is preserved or reclaimed.",
        },
        {
          type: "assistant_text",
          content: "That refactor is now running in its own lane, and the closeout record will decide whether the environment stays around for follow-up work.",
          annotation: "The chapter boundary is task goal vs isolated execution lane.",
        },
      ],
    },
    s19: {
      version,
      title: "MCP & Plugin",
      description: "External capability still follows the same discovery, routing, policy, and write-back path as native tools.",
      steps: [
        {
          type: "user_message",
          content: "Inspect the button spec from Figma and sync it into the current component library.",
          annotation: "This requires external capability instead of only local tools.",
        },
        {
          type: "system_event",
          content: "capability_router.resolve(['native_tools', 'plugin_registry', 'mcp_servers']) -> mcp:figma.inspect",
          annotation: "The system resolves the request on one shared capability bus.",
        },
        {
          type: "tool_call",
          toolName: "mcp.figma.inspect",
          content: "{ fileId: 'design-123', node: 'PrimaryButton' }",
          annotation: "The external MCP capability is called through the same routing model.",
        },
        {
          type: "tool_result",
          toolName: "mcp.figma.inspect",
          content: "{ padding: '12x18', radius: 10, typography: 'SemiBold 14', states: ['default','hover','disabled'] }",
          annotation: "The remote response is normalized before returning to the loop.",
        },
        {
          type: "assistant_text",
          content: "I have the design spec. Next I will map those constraints into the current button component implementation.",
          annotation: "MCP is not a separate universe. It plugs back into the same control plane.",
        },
      ],
    },
  };

  return en[version] ?? buildFallbackScenario(version, locale);
}

function buildFallbackScenario(version: string, locale: string): Scenario {
  return {
    version,
    title: version,
    description:
      locale === "zh"
        ? "该章节暂未提供专属模拟脚本，当前展示的是最小占位场景。"
        : locale === "ja"
          ? "この章にはまだ専用シミュレーションがないため、最小のプレースホルダーを表示しています。"
        : "This chapter does not have a dedicated simulation yet. Showing a minimal placeholder.",
    steps: [
      {
        type: "system_event",
        content:
          locale === "zh"
            ? `simulator_unavailable(version=${version})`
            : `simulator_unavailable(version=${version})`,
        annotation:
          locale === "zh"
            ? "可视化层已迁移到新章节主线，但这里还缺专门的逐步模拟数据。"
            : locale === "ja"
              ? "可視化レイヤーは新しい章立てへ移りましたが、この章専用の段階シナリオはまだ未整備です。"
            : "The visualization layer has moved to the new chapter map, but this session still lacks a dedicated step-by-step scenario.",
      },
    ],
  };
}

interface AgentLoopSimulatorProps {
  version: string;
}

export function AgentLoopSimulator({ version }: AgentLoopSimulatorProps) {
  const t = useTranslations("version");
  const locale = useLocale();
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    setScenario(null);

    if (isGenericScenarioVersion(version)) {
      setScenario(buildGenericScenario(version, locale));
      return () => {
        active = false;
      };
    }

    const loader = scenarioModules[resolveLegacySessionAssetVersion(version)];
    if (!loader) {
      setScenario(buildFallbackScenario(version, locale));
      return () => {
        active = false;
      };
    }

    loader().then((mod) => {
      if (!active) return;
      setScenario({ ...mod.default, version });
    });

    return () => {
      active = false;
    };
  }, [locale, version]);

  const sim = useSimulator(scenario?.steps ?? []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [sim.visibleSteps.length]);

  if (!scenario) {
    return (
      <section>
        <h2 className="mb-2 text-xl font-semibold">{t("simulator")}</h2>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-6 text-sm text-[var(--color-text-secondary)]">
          {locale === "zh"
            ? "正在加载当前章节的模拟场景..."
            : locale === "ja"
              ? "この章のシミュレーションを読み込んでいます..."
              : "Loading the simulation scenario for this chapter..."}
        </div>
      </section>
    );
  }

  const readyText =
    locale === "zh"
      ? "点击播放或单步开始"
      : locale === "ja"
        ? "再生またはステップで開始"
        : "Press Play or Step to begin";

  return (
    <section>
      <h2 className="mb-2 text-xl font-semibold">{t("simulator")}</h2>
      <p className="mb-4 text-sm text-[var(--color-text-secondary)]">
        {scenario.description}
      </p>

      <div className="overflow-hidden rounded-xl border border-[var(--color-border)]">
        <div className="border-b border-[var(--color-border)] bg-zinc-50 px-4 py-3 dark:bg-zinc-900">
          <SimulatorControls
            isPlaying={sim.isPlaying}
            isComplete={sim.isComplete}
            currentIndex={sim.currentIndex}
            totalSteps={sim.totalSteps}
            speed={sim.speed}
            onPlay={sim.play}
            onPause={sim.pause}
            onStep={sim.stepForward}
            onReset={sim.reset}
            onSpeedChange={sim.setSpeed}
          />
        </div>

        <div
          ref={scrollRef}
          className="flex max-h-[500px] min-h-[200px] flex-col gap-3 overflow-y-auto p-4"
        >
          {sim.visibleSteps.length === 0 && (
            <div className="flex flex-1 items-center justify-center text-sm text-[var(--color-text-secondary)]">
              {readyText}
            </div>
          )}
          <AnimatePresence mode="popLayout">
            {sim.visibleSteps.map((step, i) => (
              <SimulatorMessage key={i} step={step} index={i} />
            ))}
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}
