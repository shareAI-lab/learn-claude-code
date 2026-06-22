export type EngineeringTrack =
  | "Loop Engineering"
  | "Prompt Engineering"
  | "Context Engineering"
  | "Harness Engineering";

export interface BeginnerChapter {
  zhTitle: string;
  plain: string;
  analogy: string;
  track: EngineeringTrack;
  focus: string;
}

export const BEGINNER_CHAPTERS: Record<string, BeginnerChapter> = {
  s01: { zhTitle: "Agent 循环", plain: "让 AI 在“思考 → 用工具 → 看结果”之间反复工作，直到任务完成。", analogy: "像你问师傅问题；师傅需要时拿工具干活，看完结果再决定下一步。", track: "Loop Engineering", focus: "先看懂 while True、messages 和 tool_use 三个词。" },
  s02: { zhTitle: "工具使用", plain: "给 AI 增加读文件、写文件、查找等能力，而不改动主循环。", analogy: "主循环是插座，新增工具只是再插一件电器。", track: "Harness Engineering", focus: "看懂 TOOLS 是说明书，TOOL_HANDLERS 是执行人员表。" },
  s03: { zhTitle: "权限控制", plain: "在工具真正执行前，先判断允许、询问还是拒绝。", analogy: "像办公楼门禁：普通门放行，敏感门询问，危险门拒绝。", track: "Harness Engineering", focus: "只记住 deny、ask、allow 三种结果。" },
  s04: { zhTitle: "钩子（前后置动作）", plain: "在工具执行前后插入日志、检查或通知，不污染主循环。", analogy: "像快递过安检：进站前检查，出站后登记。", track: "Harness Engineering", focus: "区分 PreToolUse 和 PostToolUse。" },
  s05: { zhTitle: "待办计划", plain: "让 AI 先列任务清单，再逐项完成并更新状态。", analogy: "像装修前先列施工清单，不再想到哪做到哪。", track: "Harness Engineering", focus: "看懂 pending、in_progress、completed。" },
  s06: { zhTitle: "子 Agent", plain: "把大任务交给一个拥有干净上下文的小助手处理。", analogy: "主厨把切菜交给帮厨，帮厨只带结果回来。", track: "Context Engineering", focus: "理解为什么子任务要使用新的 messages。" },
  s07: { zhTitle: "技能按需加载", plain: "需要某项专业知识时才加载，避免上下文被无关内容塞满。", analogy: "做菜时才翻菜谱，不把整座图书馆背进厨房。", track: "Context Engineering", focus: "理解“先看目录、需要时再展开”。" },
  s08: { zhTitle: "上下文压缩", plain: "对话太长时压缩旧内容，为后续工作腾出空间。", analogy: "行李箱满了，把旧衣服压缩打包，但保留重要证件。", track: "Context Engineering", focus: "理解保留目标、决定、错误和下一步。" },
  s09: { zhTitle: "长期记忆", plain: "把以后仍有用的信息保存到会话之外。", analogy: "上下文是工作台，记忆是档案柜。", track: "Context Engineering", focus: "区分当前对话与跨会话记忆。" },
  s10: { zhTitle: "系统提示词", plain: "按运行环境动态组装 Agent 的身份、规则、工具和知识。", analogy: "像员工上岗手册：岗位、权限、工具和现场情况一起组成。", track: "Prompt Engineering", focus: "Prompt 不是一句魔法咒语，而是结构化说明书。" },
  s11: { zhTitle: "错误恢复", plain: "识别不同错误，选择重试、换方案或停止。", analogy: "导航走错路时，不是原地重复，而是判断堵车、没油还是目的地错误。", track: "Harness Engineering", focus: "先分类错误，再决定是否重试。" },
  s12: { zhTitle: "任务系统", plain: "把目标拆成有依赖关系、可保存和可追踪的任务。", analogy: "像项目看板：必须先打地基，才能砌墙。", track: "Harness Engineering", focus: "看懂 blockedBy 表示“要先完成谁”。" },
  s13: { zhTitle: "后台任务", plain: "把耗时工作放到后台，让 Agent 同时继续处理别的事情。", analogy: "洗衣机在转时，你可以去做饭。", track: "Harness Engineering", focus: "区分启动任务与等待任务完成。" },
  s14: { zhTitle: "定时调度", plain: "让 Harness 在指定时间自动创建和执行任务。", analogy: "像闹钟和日历提醒，到点触发，不靠 AI 自己记住。", track: "Harness Engineering", focus: "时间由系统保证，不由模型记忆保证。" },
  s15: { zhTitle: "Agent 团队", plain: "多个长期存在的小助手通过邮箱并行协作。", analogy: "像一个项目群：每个人有岗位，也有自己的收件箱。", track: "Harness Engineering", focus: "理解独立上下文与消息传递。" },
  s16: { zhTitle: "团队协议", plain: "规定 Agent 之间请求、回复和交接的固定格式。", analogy: "像接力赛，交棒姿势统一才不会掉棒。", track: "Prompt Engineering", focus: "协议让消息可预测、可检查。" },
  s17: { zhTitle: "自主领取任务", plain: "空闲 Agent 自己查看任务板并领取可做的任务。", analogy: "像餐厅出餐屏，空闲厨师主动接下一单。", track: "Loop Engineering", focus: "看懂“检查 → 领取 → 执行 → 再检查”的循环。" },
  s18: { zhTitle: "工作区隔离", plain: "给并行 Agent 分配不同目录，避免同时修改同一份文件。", analogy: "多人画画时每人一张画布，最后再合并。", track: "Harness Engineering", focus: "隔离对话还不够，也要隔离文件。" },
  s19: { zhTitle: "MCP 外部工具", plain: "用标准协议发现和调用外部服务提供的工具。", analogy: "像 USB 标准，不同设备用统一接口接进电脑。", track: "Harness Engineering", focus: "理解发现工具、调用工具、返回结果三步。" },
  s20: { zhTitle: "完整 Agent", plain: "把前面所有机制放回同一个核心循环，形成完整 Harness。", analogy: "发动机仍是同一台，最终补齐方向盘、刹车、仪表和车身。", track: "Loop Engineering", focus: "回头寻找始终没变的 agent_loop。" },
};

export const BEGINNER_TRACKS = [
  {
    name: "Loop Engineering",
    zhName: "循环工程",
    plain: "设计 AI 怎样一轮一轮地思考、行动、观察，直到结束。",
    chapters: "重点看 s01、s17、s20",
  },
  {
    name: "Prompt Engineering",
    zhName: "提示词工程",
    plain: "把身份、目标、规则和输出格式说清楚。",
    chapters: "重点看 s10、s16",
  },
  {
    name: "Context Engineering",
    zhName: "上下文工程",
    plain: "决定 AI 此刻应该看到什么、记住什么、忘掉什么。",
    chapters: "重点看 s06–s09",
  },
  {
    name: "Harness Engineering",
    zhName: "运行框架工程",
    plain: "为 AI 提供工具、权限、任务、后台运行和协作环境。",
    chapters: "贯穿 s02–s20",
  },
] as const;

export function getBeginnerChapter(version: string) {
  return BEGINNER_CHAPTERS[version];
}
