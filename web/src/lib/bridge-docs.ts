import { VERSION_ORDER, type VersionId } from "@/lib/constants";

type SupportedLocale = "zh" | "en" | "ja";
type BridgeKind = "map" | "mechanism";

export interface BridgeDocDescriptor {
  slug: string;
  kind: BridgeKind;
  title: Record<SupportedLocale, string>;
  summary: Record<SupportedLocale, string>;
}

export const BRIDGE_DOCS: Record<string, BridgeDocDescriptor> = {
  "s00-architecture-overview": {
    slug: "s00-architecture-overview",
    kind: "map",
    title: {
      zh: "系统全景总览",
      en: "Architecture Overview",
      ja: "アーキテクチャ全体図",
    },
    summary: {
      zh: "先看系统全貌，再回到当前章节，能更快分清这一层到底属于哪里。",
      en: "The big-picture map. Come back here whenever you feel lost about where a chapter fits.",
      ja: "全体像を先に見てから現在の章へ戻るための俯瞰図です。",
    },
  },
  "s00a-query-control-plane": {
    slug: "s00a-query-control-plane",
    kind: "mechanism",
    title: {
      zh: "查询控制平面",
      en: "Query Control Plane",
      ja: "クエリ制御プレーン",
    },
    summary: {
      zh: "把一次请求如何穿过控制平面讲完整，适合权限、Prompt、MCP 这些章节前后补看。",
      en: "Why the simple loop needs a coordination layer as the system grows. Best read after Stage 1.",
      ja: "1つの要求が control plane をどう通るかを通しで補う資料です。",
    },
  },
  "s00b-one-request-lifecycle": {
    slug: "s00b-one-request-lifecycle",
    kind: "mechanism",
    title: {
      zh: "一次请求生命周期",
      en: "One Request Lifecycle",
      ja: "1 リクエストのライフサイクル",
    },
    summary: {
      zh: "把一次请求从进入、执行到回写走完一遍，适合主线开始混时回头校正心智。",
      en: "Traces one request from entry to write-back. Best read after Stage 2 when pieces need connecting.",
      ja: "1回の要求を入口から write-back まで通して確認する補助資料です。",
    },
  },
  "s00c-query-transition-model": {
    slug: "s00c-query-transition-model",
    kind: "mechanism",
    title: {
      zh: "Query 续行模型",
      en: "Query Transition Model",
      ja: "クエリ遷移モデル",
    },
    summary: {
      zh: "专门讲一条 query 为什么继续下一轮，适合恢复、压缩、预算、hook 开始缠在一起时回看。",
      en: "Why each continuation needs an explicit reason. Best read alongside s11 (Error Recovery).",
      ja: "エラー回復・文脈圧縮・予算制御・hook が重なり始めたときに、query がなぜ次のターンへ続くのかを補う資料です。",
    },
  },
  "s00d-chapter-order-rationale": {
    slug: "s00d-chapter-order-rationale",
    kind: "map",
    title: {
      zh: "为什么这样安排章节顺序",
      en: "Why This Chapter Order",
      ja: "なぜこの章順なのか",
    },
    summary: {
      zh: "专门解释为什么课程要按现在这个顺序展开，适合读者刚进入主线或准备自己重排章节时回看。",
      en: "Explains why the curriculum is ordered this way and what breaks when the sequence is rearranged.",
      ja: "なぜこの順序で学ぶのか、順番を崩すと何が混乱するのかを整理する資料です。",
    },
  },
  "s00f-code-reading-order": {
    slug: "s00f-code-reading-order",
    kind: "map",
    title: {
      zh: "本仓库代码阅读顺序",
      en: "Code Reading Order",
      ja: "コード読解順",
    },
    summary: {
      zh: "专门告诉你本地 `agents/*.py` 该按什么顺序打开、每章先盯住哪类状态和函数，避免重新乱翻源码。",
      en: "Shows which local `agents/*.py` files to open first and what state or functions to inspect before the code turns into noise.",
      ja: "ローカルの `agents/*.py` をどの順で開き、各章でまずどの状態や関数を見るべきかを整理した読解ガイドです。",
    },
  },
  "s00e-reference-module-map": {
    slug: "s00e-reference-module-map",
    kind: "map",
    title: {
      zh: "参考仓库模块映射图",
      en: "Reference Module Map",
      ja: "参照モジュール対応表",
    },
    summary: {
      zh: "把参考仓库里真正重要的模块簇，和当前课程章节一一对齐，专门用来验证章节顺序是否合理。",
      en: "Maps the reference repo's real module clusters onto the current curriculum to validate the chapter order.",
      ja: "参照リポジトリの高信号モジュール群と現在の教材章を対応付け、章順の妥当性を確認する地図です。",
    },
  },
  "s02a-tool-control-plane": {
    slug: "s02a-tool-control-plane",
    kind: "mechanism",
    title: {
      zh: "工具控制平面",
      en: "Tool Control Plane",
      ja: "ツール制御プレーン",
    },
    summary: {
      zh: "专门补工具调用怎样进入统一执行面，适合权限、Hook、MCP 等章节一起看。",
      en: "Why tools become a coordination layer, not just a lookup table. Best read after s02.",
      ja: "ツール呼び出しが共通の実行面に入る流れを補う資料です。",
    },
  },
  "s02b-tool-execution-runtime": {
    slug: "s02b-tool-execution-runtime",
    kind: "mechanism",
    title: {
      zh: "工具执行运行时",
      en: "Tool Execution Runtime",
      ja: "ツール実行ランタイム",
    },
    summary: {
      zh: "把工具并发、串行、进度消息、结果顺序和 context 合并这层运行时讲清楚。",
      en: "How multiple tool calls in one turn get executed safely. Best read after s02.",
      ja: "tool の並列実行と直列実行、progress 更新、結果順序、context 統合をまとめて補う資料です。",
    },
  },
  glossary: {
    slug: "glossary",
    kind: "map",
    title: {
      zh: "术语表",
      en: "Glossary",
      ja: "用語集",
    },
    summary: {
      zh: "术语一多就先回这里，统一名词边界，避免 task、runtime task、teammate 混在一起。",
      en: "Bookmark this. Come back whenever you hit an unfamiliar term.",
      ja: "用語が増えて混ざり始めたときに戻る境界整理用の用語集です。",
    },
  },
  "entity-map": {
    slug: "entity-map",
    kind: "map",
    title: {
      zh: "对象与模块关系图",
      en: "Entity Map",
      ja: "エンティティ地図",
    },
    summary: {
      zh: "按对象和模块关系看系统，适合读到中后段时重新校准模块边界。",
      en: "Use this when concepts start to blur. It tells you which layer each thing belongs to.",
      ja: "オブジェクトとモジュール関係から全体を再確認する地図です。",
    },
  },
  "data-structures": {
    slug: "data-structures",
    kind: "map",
    title: {
      zh: "关键数据结构地图",
      en: "Data Structure Map",
      ja: "主要データ構造マップ",
    },
    summary: {
      zh: "把核心记录结构放在一起看，适合任务、运行时、多 Agent 章节反复对照。",
      en: "Every important record in one place. Use when you lose track of where state lives.",
      ja: "主要な record 構造を横断的に見直すための資料です。",
    },
  },
  "s10a-message-prompt-pipeline": {
    slug: "s10a-message-prompt-pipeline",
    kind: "mechanism",
    title: {
      zh: "消息与 Prompt 装配流水线",
      en: "Message-Prompt Pipeline",
      ja: "メッセージと Prompt の組み立てパイプライン",
    },
    summary: {
      zh: "专门补消息、Prompt 片段和装配顺序，适合 s10 前后深入看。",
      en: "The full input pipeline beyond system prompt. Best read alongside s10.",
      ja: "message と prompt 片をどの順に組み立てるかを補う解説です。",
    },
  },
  "s13a-runtime-task-model": {
    slug: "s13a-runtime-task-model",
    kind: "mechanism",
    title: {
      zh: "运行时任务模型",
      en: "Runtime Task Model",
      ja: "ランタイムタスクモデル",
    },
    summary: {
      zh: "把 task goal、runtime record、notification 三层边界一次讲清。",
      en: "The most common Stage 3 confusion: two meanings of 'task'. Read between s12 and s13.",
      ja: "作業目標・実行記録・通知の3層境界をまとめて補う資料です。",
    },
  },
  "s19a-mcp-capability-layers": {
    slug: "s19a-mcp-capability-layers",
    kind: "mechanism",
    title: {
      zh: "MCP 能力层地图",
      en: "MCP Capability Layers",
      ja: "MCP 能力層マップ",
    },
    summary: {
      zh: "把本地工具、插件、MCP server 如何接回同一 capability bus 讲完整。",
      en: "MCP is more than external tools. This shows the full capability stack. Read alongside s19.",
      ja: "native tool・plugin・MCP server が 1 つの capability bus へ戻る全体像を補います。",
    },
  },
  "team-task-lane-model": {
    slug: "team-task-lane-model",
    kind: "map",
    title: {
      zh: "队友-任务-车道模型",
      en: "Teammate-Task-Lane Model",
      ja: "チームメイト・タスク・レーンモデル",
    },
    summary: {
      zh: "专门拆清队友、协议请求、任务、运行时槽位和 worktree 车道这五层边界。",
      en: "Five concepts that look similar but live on different layers. Keep open during s15-s18.",
      ja: "teammate・protocol request・task・runtime slot・worktree lane の 5 層境界を整理します。",
    },
  },
  "teaching-scope": {
    slug: "teaching-scope",
    kind: "map",
    title: {
      zh: "教学范围与取舍",
      en: "Teaching Scope",
      ja: "教材の守備範囲",
    },
    summary: {
      zh: "说明这套教学仓库刻意不讲什么，帮助读者守住主线，不被低价值细节带偏。",
      en: "What this repo teaches, what it deliberately leaves out, and why.",
      ja: "この教材が意図的に省いている範囲を示し、主線を守るための資料です。",
    },
  },
};

export const FOUNDATION_DOC_SLUGS = [
  "s00-architecture-overview",
  "s00d-chapter-order-rationale",
  "s00f-code-reading-order",
  "s00e-reference-module-map",
  "teaching-scope",
  "glossary",
  "data-structures",
  "entity-map",
] as const;

export const MECHANISM_DOC_SLUGS = [
  "s00a-query-control-plane",
  "s00b-one-request-lifecycle",
  "s00c-query-transition-model",
  "s02a-tool-control-plane",
  "s02b-tool-execution-runtime",
  "s10a-message-prompt-pipeline",
  "s13a-runtime-task-model",
  "team-task-lane-model",
  "s19a-mcp-capability-layers",
] as const;

export const RESET_DOC_SLUGS = [
  "s00a-query-control-plane",
  "s02b-tool-execution-runtime",
  "s13a-runtime-task-model",
  "team-task-lane-model",
  "s19a-mcp-capability-layers",
] as const;

export const BRIDGE_DOC_RELATED_VERSIONS: Partial<
  Record<string, readonly VersionId[]>
> = {
  "s00-architecture-overview": ["s01", "s07", "s12", "s15"],
  "s00d-chapter-order-rationale": ["s01", "s12", "s15"],
  "s00f-code-reading-order": ["s01", "s07", "s12", "s15"],
  "s00e-reference-module-map": ["s01", "s07", "s12", "s15", "s18", "s19"],
  glossary: ["s01", "s09", "s16", "s19"],
  "entity-map": ["s04", "s12", "s15", "s18", "s19"],
  "data-structures": ["s03", "s09", "s12", "s13", "s18"],
  "teaching-scope": ["s01", "s05", "s12", "s19"],
  "s00a-query-control-plane": ["s07", "s10", "s11", "s19"],
  "s00b-one-request-lifecycle": ["s04", "s11", "s14"],
  "s00c-query-transition-model": ["s11", "s17"],
  "s02a-tool-control-plane": ["s02", "s08", "s19"],
  "s02b-tool-execution-runtime": ["s02", "s07", "s13", "s19"],
  "s10a-message-prompt-pipeline": ["s10"],
  "s13a-runtime-task-model": ["s12", "s13", "s14", "s17"],
  "team-task-lane-model": ["s15", "s16", "s17", "s18"],
  "s19a-mcp-capability-layers": ["s19"],
};

export const CHAPTER_BRIDGE_DOCS: Partial<Record<VersionId, string[]>> = {
  s01: ["s00-architecture-overview", "s00d-chapter-order-rationale", "s00f-code-reading-order", "s00e-reference-module-map", "glossary"],
  s02: ["s02a-tool-control-plane", "s02b-tool-execution-runtime"],
  s03: ["data-structures", "glossary"],
  s04: ["entity-map", "s00b-one-request-lifecycle"],
  s05: ["glossary", "teaching-scope"],
  s06: ["data-structures", "s00b-one-request-lifecycle"],
  s07: ["s00f-code-reading-order", "s00a-query-control-plane", "s02b-tool-execution-runtime"],
  s08: ["s02a-tool-control-plane", "entity-map"],
  s09: ["data-structures", "glossary"],
  s10: ["s10a-message-prompt-pipeline", "s00a-query-control-plane"],
  s11: ["s00c-query-transition-model", "s00b-one-request-lifecycle"],
  s12: ["s00f-code-reading-order", "data-structures", "entity-map"],
  s13: ["s13a-runtime-task-model", "s02b-tool-execution-runtime"],
  s14: ["s13a-runtime-task-model", "s00b-one-request-lifecycle"],
  s15: ["s00f-code-reading-order", "team-task-lane-model", "entity-map"],
  s16: ["team-task-lane-model", "glossary"],
  s17: ["team-task-lane-model", "s13a-runtime-task-model"],
  s18: ["team-task-lane-model", "data-structures"],
  s19: ["s19a-mcp-capability-layers", "s02b-tool-execution-runtime"],
};

export function getBridgeDocDescriptors(version: VersionId): BridgeDocDescriptor[] {
  return (CHAPTER_BRIDGE_DOCS[version] ?? [])
    .map((slug) => BRIDGE_DOCS[slug])
    .filter((doc): doc is BridgeDocDescriptor => Boolean(doc));
}

export function getChaptersForBridgeDoc(slug: string): VersionId[] {
  const mappedVersions = BRIDGE_DOC_RELATED_VERSIONS[slug] ?? [];
  const referencedVersions = Object.entries(CHAPTER_BRIDGE_DOCS)
    .filter(([, slugs]) => slugs?.includes(slug))
    .map(([version]) => version as VersionId);

  return VERSION_ORDER.filter((version) =>
    new Set([...mappedVersions, ...referencedVersions]).has(version)
  );
}
