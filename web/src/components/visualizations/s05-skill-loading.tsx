"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useLocale } from "@/lib/i18n";

type SupportedLocale = "zh" | "en";

interface SkillEntry {
  name: string;
  summary: string;
  fullTokens: number;
  content: string[];
}

interface LocaleCopy {
  title: string;
  systemPrompt: string;
  alwaysPresent: string;
  userTypes: string;
  tokenLabel: string;
  mechanismNote: string;
  layer1Label: string;
  layer1Desc: string;
  layer2Label: string;
  layer2Desc: string;
  skills: SkillEntry[];
  steps: Array<{ title: string; description: string }>;
}

const COPY: Record<SupportedLocale, LocaleCopy> = {
  zh: {
    title: "按需加载技能",
    systemPrompt: "系统提示词",
    alwaysPresent: "常驻",
    userTypes: "用户输入：",
    tokenLabel: "Token",
    mechanismNote:
      "Skill（技能）工具会把内容作为 tool_result（工具结果）消息返回。模型在当前上下文中读取并执行这些指令，避免把大段技能文本常驻到 system prompt（系统提示词）。",
    layer1Label: "第 1 层",
    layer1Desc: "常驻，约 120 tokens",
    layer2Label: "第 2 层",
    layer2Desc: "按需加载，每个约 300-500 tokens",
    skills: [
      {
        name: "/commit",
        summary: "按仓库规范创建 Git 提交",
        fullTokens: 320,
        content: [
          "1. 先运行 git status + git diff 查看改动",
          "2. 分析已暂存改动并起草提交信息",
          "3. 创建提交并附加 Co-Authored-By",
          "4. 提交后再跑 git status 验证结果",
        ],
      },
      {
        name: "/review-pr",
        summary: "审查 PR 的缺陷与风格问题",
        fullTokens: 480,
        content: [
          "1. 通过 gh pr view 拉取 PR 差异",
          "2. 逐文件检查改动风险",
          "3. 聚焦 bug、安全与代码风格",
          "4. 使用 gh pr review 提交评审意见",
        ],
      },
      {
        name: "/test",
        summary: "执行并分析测试套件",
        fullTokens: 290,
        content: [
          "1. 从 package.json 判断测试框架",
          "2. 运行测试并采集输出",
          "3. 分析失败原因并给出修复建议",
          "4. 应用修复后重新回归测试",
        ],
      },
      {
        name: "/deploy",
        summary: "将应用部署到目标环境",
        fullTokens: 350,
        content: [
          "1. 部署前确认所有测试通过",
          "2. 构建生产发布包",
          "3. 通过 CI 推送到部署目标",
          "4. 验证已部署地址的健康检查",
        ],
      },
    ],
    steps: [
      {
        title: "第 1 层：摘要常驻",
        description: "所有技能只以摘要形式进入系统提示词，体积小且始终可见。",
      },
      {
        title: "触发技能调用",
        description: "模型识别技能命令后，调用 Skill 工具加载详细指令。",
      },
      {
        title: "第 2 层：正文注入",
        description: "完整技能正文通过 tool_result 注入，而非写入系统提示词。",
      },
      {
        title: "进入当前上下文",
        description: "详细指令像工具返回值一样进入上下文，模型按此精确执行。",
      },
      {
        title: "多技能叠加",
        description: "可同时加载多个技能；常驻的是摘要，正文按需进出。",
      },
      {
        title: "双层架构",
        description: "第 1 层常驻且轻量，第 2 层按需且详细，职责清晰分离。",
      },
    ],
  },
  en: {
    title: "On-Demand Skill Loading",
    systemPrompt: "System Prompt",
    alwaysPresent: "always present",
    userTypes: "User types:",
    tokenLabel: "Tokens",
    mechanismNote:
      "The Skill tool returns content as a tool_result message. The model sees it in context and follows the instructions. No system prompt bloat.",
    layer1Label: "LAYER 1",
    layer1Desc: "Always present, ~120 tokens",
    layer2Label: "LAYER 2",
    layer2Desc: "On demand, ~300-500 tokens each",
    skills: [
      {
        name: "/commit",
        summary: "Create git commits following repo conventions",
        fullTokens: 320,
        content: [
          "1. Run git status + git diff to see changes",
          "2. Analyze all staged changes and draft message",
          "3. Create commit with Co-Authored-By trailer",
          "4. Run git status after commit to verify",
        ],
      },
      {
        name: "/review-pr",
        summary: "Review pull requests for bugs and style",
        fullTokens: 480,
        content: [
          "1. Fetch PR diff via gh pr view",
          "2. Analyze changes file by file for issues",
          "3. Check for bugs, security, and style problems",
          "4. Post review comments with gh pr review",
        ],
      },
      {
        name: "/test",
        summary: "Run and analyze test suites",
        fullTokens: 290,
        content: [
          "1. Detect test framework from package.json",
          "2. Run test suite and capture output",
          "3. Analyze failures and suggest fixes",
          "4. Re-run after applying fixes",
        ],
      },
      {
        name: "/deploy",
        summary: "Deploy application to target environment",
        fullTokens: 350,
        content: [
          "1. Verify all tests pass before deploy",
          "2. Build production bundle",
          "3. Push to deployment target via CI",
          "4. Verify health check on deployed URL",
        ],
      },
    ],
    steps: [
      {
        title: "Layer 1: Compact Summaries",
        description:
          "All skills are summarized in the system prompt. Compact, always present.",
      },
      {
        title: "Skill Invocation",
        description:
          "The model recognizes a skill invocation and triggers the Skill tool.",
      },
      {
        title: "Layer 2: Full Injection",
        description:
          "The full skill instructions are injected as a tool_result, not into the system prompt.",
      },
      {
        title: "In Context Now",
        description:
          "The detailed instructions appear as if a tool returned them. The model follows them precisely.",
      },
      {
        title: "Stack Skills",
        description:
          "Multiple skills can be loaded. Only summaries are permanent; full content comes and goes.",
      },
      {
        title: "Two-Layer Architecture",
        description:
          "Layer 1: always present, tiny. Layer 2: loaded on demand, detailed. Elegant separation.",
      },
    ],
  },
};

const TOKEN_STATES = [120, 120, 440, 440, 780, 780];
const MAX_TOKEN_DISPLAY = 1000;

export default function SkillLoading({ title }: { title?: string }) {
  const locale = useLocale() === "zh" ? "zh" : "en";
  const copy = COPY[locale];
  const SKILLS = copy.skills;
  const STEPS = copy.steps;
  const {
    currentStep,
    totalSteps,
    next,
    prev,
    reset,
    isPlaying,
    toggleAutoPlay,
  } = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2500 });

  const tokenCount = TOKEN_STATES[currentStep];
  const highlightedSkill = currentStep >= 1 && currentStep <= 3 ? 0 : currentStep >= 4 ? 1 : -1;
  const showFirstContent = currentStep >= 2;
  const showSecondContent = currentStep >= 4;
  const firstContentFaded = currentStep >= 5;

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || copy.title}
      </h2>

      <div
        className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-900"
        style={{ minHeight: 500 }}
      >
        <div className="flex gap-6">
          <div className="flex-1 space-y-4">
            <div>
              <div className="mb-2 flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-zinc-400" />
                <span className="text-xs font-semibold text-zinc-600 dark:text-zinc-300">
                  {copy.systemPrompt}
                </span>
                <span className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-[10px] text-zinc-400 dark:bg-zinc-800">
                  {copy.alwaysPresent}
                </span>
              </div>
              <div className="rounded-lg border border-zinc-300 bg-zinc-900 p-4 dark:border-zinc-600">
                <div className="mb-2 font-mono text-[10px] text-zinc-500">
                  # Available Skills
                </div>
                <div className="space-y-1.5">
                  {SKILLS.map((skill, i) => {
                    const isHighlighted = i === highlightedSkill;
                    return (
                      <motion.div
                        key={skill.name}
                        animate={{
                          boxShadow: isHighlighted
                            ? "0 0 12px 2px rgba(59, 130, 246, 0.5)"
                            : "0 0 0 0px rgba(59, 130, 246, 0)",
                        }}
                        transition={{ duration: 0.4 }}
                        className={`rounded px-3 py-1.5 font-mono text-xs transition-colors ${
                          isHighlighted
                            ? "bg-blue-900/60 text-blue-300"
                            : "bg-zinc-800 text-zinc-400"
                        }`}
                      >
                        <span className="font-semibold text-zinc-200">
                          {skill.name}
                        </span>
                        {" - "}
                        {skill.summary}
                      </motion.div>
                    );
                  })}
                </div>
              </div>
            </div>

            <AnimatePresence>
              {currentStep === 1 && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 dark:border-blue-800 dark:bg-blue-950/30"
                >
                  <span className="text-xs text-blue-600 dark:text-blue-400">
                    {copy.userTypes}
                  </span>
                  <code className="rounded bg-blue-100 px-2 py-0.5 text-xs font-bold text-blue-800 dark:bg-blue-900/50 dark:text-blue-200">
                    /commit
                  </code>
                </motion.div>
              )}
              {currentStep === 4 && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 dark:border-blue-800 dark:bg-blue-950/30"
                >
                  <span className="text-xs text-blue-600 dark:text-blue-400">
                    {copy.userTypes}
                  </span>
                  <code className="rounded bg-blue-100 px-2 py-0.5 text-xs font-bold text-blue-800 dark:bg-blue-900/50 dark:text-blue-200">
                    /review-pr
                  </code>
                </motion.div>
              )}
            </AnimatePresence>

            <AnimatePresence>
              {(showFirstContent || showSecondContent) && (
                <motion.div
                  initial={{ opacity: 0, scaleY: 0 }}
                  animate={{ opacity: 1, scaleY: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex justify-center"
                >
                  <div className="flex flex-col items-center">
                    <div className="h-6 w-px bg-blue-400 dark:bg-blue-500" />
                    <div className="h-0 w-0 border-l-[5px] border-r-[5px] border-t-[6px] border-l-transparent border-r-transparent border-t-blue-400 dark:border-t-blue-500" />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="space-y-3">
              <AnimatePresence>
                {showFirstContent && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{
                      opacity: firstContentFaded ? 0.4 : 1,
                      height: "auto",
                    }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.4 }}
                    className="overflow-hidden"
                  >
                    <div className="rounded-lg border-2 border-blue-300 bg-white p-4 dark:border-blue-700 dark:bg-zinc-800">
                      <div className="mb-2 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-2 rounded-full bg-blue-500" />
                          <span className="text-xs font-bold text-blue-700 dark:text-blue-300">
                            SKILL.md: /commit
                          </span>
                        </div>
                        <span className="rounded bg-blue-100 px-1.5 py-0.5 font-mono text-[10px] text-blue-600 dark:bg-blue-900/40 dark:text-blue-300">
                          tool_result
                        </span>
                      </div>
                      <div className="space-y-1">
                        {SKILLS[0].content.map((line, i) => (
                          <motion.div
                            key={i}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{
                              opacity: firstContentFaded ? 0.5 : 1,
                              x: 0,
                            }}
                            transition={{ delay: i * 0.08 }}
                            className="font-mono text-xs text-zinc-600 dark:text-zinc-300"
                          >
                            {line}
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <AnimatePresence>
                {showSecondContent && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.4 }}
                    className="overflow-hidden"
                  >
                    <div className="rounded-lg border-2 border-purple-300 bg-white p-4 dark:border-purple-700 dark:bg-zinc-800">
                      <div className="mb-2 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-2 rounded-full bg-purple-500" />
                          <span className="text-xs font-bold text-purple-700 dark:text-purple-300">
                            SKILL.md: /review-pr
                          </span>
                        </div>
                        <span className="rounded bg-purple-100 px-1.5 py-0.5 font-mono text-[10px] text-purple-600 dark:bg-purple-900/40 dark:text-purple-300">
                          tool_result
                        </span>
                      </div>
                      <div className="space-y-1">
                        {SKILLS[1].content.map((line, i) => (
                          <motion.div
                            key={i}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.08 }}
                            className="font-mono text-xs text-zinc-600 dark:text-zinc-300"
                          >
                            {line}
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <AnimatePresence>
              {currentStep === 3 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
                >
                  {copy.mechanismNote}
                </motion.div>
              )}
            </AnimatePresence>

            <AnimatePresence>
              {currentStep === 5 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex gap-3"
                >
                  <div className="flex-1 rounded border border-zinc-200 bg-zinc-50 p-2 text-center dark:border-zinc-700 dark:bg-zinc-800">
                    <div className="text-[10px] font-semibold text-zinc-500 dark:text-zinc-400">
                      {copy.layer1Label}
                    </div>
                    <div className="text-xs text-zinc-600 dark:text-zinc-300">
                      {copy.layer1Desc}
                    </div>
                  </div>
                  <div className="flex-1 rounded border border-blue-200 bg-blue-50 p-2 text-center dark:border-blue-700 dark:bg-blue-900/20">
                    <div className="text-[10px] font-semibold text-blue-500 dark:text-blue-400">
                      {copy.layer2Label}
                    </div>
                    <div className="text-xs text-blue-600 dark:text-blue-300">
                      {copy.layer2Desc}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="flex w-16 flex-col items-center">
            <div className="mb-1 text-center font-mono text-[10px] text-zinc-400">
              {copy.tokenLabel}
            </div>
            <div
              className="relative w-8 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800"
              style={{ height: 300 }}
            >
              <motion.div
                animate={{
                  height: `${(tokenCount / MAX_TOKEN_DISPLAY) * 100}%`,
                }}
                transition={{ duration: 0.5 }}
                className={`absolute bottom-0 w-full rounded-full ${
                  tokenCount > 600
                    ? "bg-amber-500"
                    : tokenCount > 300
                      ? "bg-blue-500"
                      : "bg-emerald-500"
                }`}
              />
            </div>
            <motion.div
              key={tokenCount}
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              className="mt-2 text-center font-mono text-xs font-semibold text-zinc-600 dark:text-zinc-300"
            >
              {tokenCount}
            </motion.div>
          </div>
        </div>

        <div className="mt-6">
          <StepControls
            currentStep={currentStep}
            totalSteps={totalSteps}
            onPrev={prev}
            onNext={next}
            onReset={reset}
            isPlaying={isPlaying}
            onToggleAutoPlay={toggleAutoPlay}
            stepTitle={STEPS[currentStep].title}
            stepDescription={STEPS[currentStep].description}
          />
        </div>
      </div>
    </section>
  );
}
