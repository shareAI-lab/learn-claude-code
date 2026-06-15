"use client";

import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, ClipboardCheck, OctagonAlert, PlayCircle, ShieldAlert, ShieldCheck, UserCheck } from "lucide-react";
import { StepControls } from "@/components/visualizations/shared/step-controls";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { cn } from "@/lib/utils";

const STEPS = [
  {
    title: "Three Requests, Three Routes",
    desc: "Permission is a router: safe calls run, risky calls ask, forbidden calls stop.",
    mode: "overview",
  },
  {
    title: "Allow: Safe Read Runs Immediately",
    desc: "A read-only file request passes policy and reaches the handler without a user ticket.",
    mode: "allow",
  },
  {
    title: "Ask: Risky Local Delete Becomes a Ticket",
    desc: "A local delete command is not forbidden, but it must pause for explicit confirmation.",
    mode: "ask",
  },
  {
    title: "Approved Ask: Handler Runs After Yes",
    desc: "The same risky request executes only after the user approves this exact action.",
    mode: "ask-approved",
  },
  {
    title: "Deny: Forbidden Pattern Stops Early",
    desc: "A root-level sudo delete is blocked before any handler can touch the machine.",
    mode: "deny",
  },
  {
    title: "One Permission Desk, Three Outcomes",
    desc: "The harness keeps allow, ask, and deny decisions outside the model, then returns the decision to the loop.",
    mode: "summary",
  },
] as const;

const REQUESTS = [
  {
    id: "allow",
    tool: "read_file",
    command: "README.md",
    result: "allow",
    detail: "read-only workspace file",
    tone: "emerald",
  },
  {
    id: "ask",
    tool: "bash",
    command: "rm -rf ./tmp/build-cache",
    result: "ask",
    detail: "local destructive command",
    tone: "amber",
  },
  {
    id: "deny",
    tool: "bash",
    command: "sudo rm -rf /",
    result: "deny",
    detail: "forbidden root delete",
    tone: "red",
  },
] as const;

function toneClass(tone: "emerald" | "amber" | "red" | "blue" | "zinc") {
  if (tone === "emerald") return "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200";
  if (tone === "amber") return "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200";
  if (tone === "red") return "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200";
  if (tone === "blue") return "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-200";
  return "border-zinc-200 bg-white text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200";
}

function Surface({
  title,
  icon,
  active,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "min-w-0 rounded-lg border p-4 transition-colors",
        active
          ? "border-red-300 bg-red-50 dark:border-red-900 dark:bg-red-950/30"
          : "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900"
      )}
    >
      <div className="mb-4 flex items-center gap-3 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
        <span
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
            active
              ? "bg-red-500 text-white"
              : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-300"
          )}
        >
          {icon}
        </span>
        {title}
      </div>
      {children}
    </div>
  );
}

type StepMode = (typeof STEPS)[number]["mode"];
type RequestId = (typeof REQUESTS)[number]["id"];

function activeRequestId(mode: StepMode): RequestId | null {
  if (mode === "allow") return "allow";
  if (mode === "ask" || mode === "ask-approved") return "ask";
  if (mode === "deny") return "deny";
  return null;
}

function RequestCard({
  request,
  active,
  muted,
}: {
  request: (typeof REQUESTS)[number];
  active: boolean;
  muted: boolean;
}) {
  return (
    <motion.div
      layout
      animate={active ? { y: -1 } : { y: 0 }}
      className={cn(
        "min-w-0 rounded-xl border p-4 shadow-sm",
        active ? toneClass(request.tone) : "border-zinc-200 bg-white text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200",
        muted && "opacity-45"
      )}
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="min-w-0 text-sm font-semibold">tool request</div>
        <span className="shrink-0 rounded-full bg-white/70 px-2 py-1 font-mono text-xs font-semibold dark:bg-zinc-950/30">
          {request.tool}
        </span>
      </div>
      <code className="block min-w-0 rounded-lg bg-zinc-950 p-3 font-mono text-xs leading-relaxed text-zinc-100 whitespace-pre-wrap break-words">
        {request.command}
      </code>
      <div className="mt-3 flex items-center justify-between gap-3 text-sm">
        <span className="min-w-0 text-pretty opacity-80">{request.detail}</span>
        <span className="shrink-0 rounded bg-white/75 px-2 py-1 font-semibold dark:bg-zinc-950/30">
          {request.result}
        </span>
      </div>
    </motion.div>
  );
}

function CheckRow({
  label,
  detail,
  status,
  active,
}: {
  label: string;
  detail: string;
  status: "waiting" | "pass" | "allow" | "ask" | "approved" | "deny" | "skip";
  active: boolean;
}) {
  const icon =
    status === "deny" ? <OctagonAlert size={16} /> : status === "pass" || status === "allow" ? <CheckCircle2 size={16} /> : status === "ask" ? <ShieldAlert size={16} /> : status === "approved" ? <UserCheck size={16} /> : <ClipboardCheck size={16} />;
  const tone = status === "deny" ? "red" : status === "pass" || status === "allow" || status === "approved" ? "emerald" : status === "ask" ? "amber" : "zinc";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "rounded-lg border p-3",
        active ? toneClass(tone) : "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900"
      )}
    >
      <div className="mb-1 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-semibold">
          {icon}
          {label}
        </div>
        <span className="shrink-0 rounded bg-white/70 px-2 py-0.5 text-[11px] font-semibold dark:bg-zinc-950/30">
          {status}
        </span>
      </div>
      <div className="text-xs leading-relaxed opacity-80">{detail}</div>
    </motion.div>
  );
}

function PermissionDesk({ mode }: { mode: StepMode }) {
  if (mode === "overview" || mode === "summary") {
    return (
      <div className="grid gap-2">
        <CheckRow label="Safe read" detail="No write, no shell, no approval needed." status="allow" active={mode === "overview"} />
        <CheckRow label="Risky local change" detail="May be useful, but requires a human yes." status="ask" active={mode === "overview"} />
        <CheckRow label="Forbidden pattern" detail="Root delete and sudo never reach handlers." status="deny" active={mode === "overview"} />
      </div>
    );
  }

  if (mode === "allow") {
    return (
      <div className="space-y-2">
        <CheckRow label="Gate 1: hard deny" detail="No sudo, no root path, no forbidden pattern." status="pass" active={false} />
        <CheckRow label="Gate 2: allow rule" detail="Read-only workspace file can run immediately." status="allow" active />
        <CheckRow label="Gate 3: user approval" detail="Skipped because this call is already safe." status="skip" active={false} />
      </div>
    );
  }

  if (mode === "deny") {
    return (
      <div className="space-y-2">
        <CheckRow label="Gate 1: hard deny" detail="sudo + root delete is blocked immediately." status="deny" active />
        <CheckRow label="Gate 2: risk rule" detail="Skipped because hard deny already decided." status="skip" active={false} />
        <CheckRow label="Gate 3: user approval" detail="Skipped because the user cannot approve forbidden actions." status="skip" active={false} />
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <CheckRow label="Gate 1: hard deny" detail="Local project path is not globally forbidden." status="pass" active={false} />
      <CheckRow label="Gate 2: risk rule" detail="Deleting files needs an explicit approval ticket." status="ask" active={mode === "ask"} />
      <CheckRow label="Gate 3: user approval" detail="The tool waits until this request is approved." status={mode === "ask-approved" ? "approved" : "waiting"} active={mode === "ask-approved"} />
    </div>
  );
}

function CodeLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg bg-white/70 p-2 dark:bg-zinc-950/30">
      <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide opacity-70">{label}</div>
      <code className="block min-w-0 whitespace-pre-wrap break-words font-mono text-xs leading-relaxed">{value}</code>
    </div>
  );
}

function Outcome({ mode }: { mode: StepMode }) {
  if (mode === "overview") {
    return <div className="rounded-lg border border-dashed border-zinc-300 px-4 py-8 text-center text-sm text-zinc-500 dark:border-zinc-700 dark:text-zinc-400">select a request route</div>;
  }

  if (mode === "allow") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={cn("space-y-3 rounded-xl border p-4", toneClass("emerald"))}>
        <div className="flex items-center gap-2 text-base font-semibold">
          <PlayCircle size={17} />
          Handler runs now
        </div>
        <CodeLine label="handler" value="read_file" />
        <CodeLine label="args" value='path: "README.md"' />
      </motion.div>
    );
  }

  if (mode === "ask") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={cn("rounded-xl border p-4", toneClass("amber"))}>
        <div className="mb-2 flex items-center gap-2 text-base font-semibold">
          <UserCheck size={17} />
          Approval ticket
        </div>
        <div className="text-sm leading-relaxed">"Allow deleting local build cache?"</div>
      </motion.div>
    );
  }

  if (mode === "ask-approved") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={cn("space-y-3 rounded-xl border p-4", toneClass("blue"))}>
        <div className="flex items-center gap-2 text-base font-semibold">
          <PlayCircle size={17} />
          Handler runs after approval
        </div>
        <CodeLine label="handler" value="bash" />
        <CodeLine label="args" value="rm -rf ./tmp/build-cache" />
      </motion.div>
    );
  }

  if (mode === "deny") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={cn("rounded-xl border p-4", toneClass("red"))}>
        <div className="mb-2 flex items-center gap-2 text-base font-semibold">
          <OctagonAlert size={17} />
          Blocked before handler
        </div>
        <div className="text-sm leading-relaxed">No tool execution, no user prompt, no filesystem touch.</div>
      </motion.div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-2">
      {REQUESTS.map((request) => (
        <div key={request.id} className={cn("rounded-lg border p-3", toneClass(request.tone))}>
          <div className="mb-1 flex items-center gap-2 text-sm font-semibold">
            {request.result === "deny" ? <OctagonAlert size={15} /> : request.result === "ask" ? <ShieldAlert size={15} /> : <ShieldCheck size={15} />}
            {request.result}
          </div>
          <div className="text-xs leading-relaxed opacity-80">{request.detail}</div>
        </div>
      ))}
      <div className={cn("rounded-xl border p-4", toneClass("emerald"))}>
        <div className="mb-2 flex items-center gap-2 text-base font-semibold">
        <ShieldCheck size={17} />
          decision returned to loop
        </div>
        <div className="text-sm leading-relaxed">Permission stays outside the model, but the loop still receives a normal tool_result or blocked result.</div>
      </div>
    </motion.div>
  );
}

export default function PermissionVisualization({ title }: { title?: string }) {
  const vis = useSteppedVisualization({ totalSteps: STEPS.length, autoPlayInterval: 2500 });
  const step = vis.currentStep;
  const current = STEPS[step];
  const mode = current.mode;
  const activeId = activeRequestId(mode);

  return (
    <section className="min-h-[500px] space-y-4">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
        {title || "Permission Desk"}
      </h2>

      <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
        <div className="grid gap-3 lg:grid-cols-[1fr_1.1fr_0.95fr]">
          <Surface title="Tool requests" icon={<OctagonAlert size={20} />} active={mode === "overview" || activeId !== null}>
            <div className="space-y-2">
              {REQUESTS.map((request) => (
                <RequestCard
                  key={request.id}
                  request={request}
                  active={activeId === request.id || (mode === "overview" && step === 0)}
                  muted={activeId !== null && activeId !== request.id}
                />
              ))}
            </div>
          </Surface>

          <Surface title="Permission desk" icon={<ShieldCheck size={20} />} active={mode !== "overview"}>
            <PermissionDesk mode={mode} />
          </Surface>

          <Surface title="Outcome" icon={<PlayCircle size={20} />} active={mode !== "overview"}>
            <AnimatePresence mode="wait">
              <Outcome key={mode} mode={mode} />
            </AnimatePresence>
          </Surface>
        </div>

        <div className="mt-3 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm leading-relaxed text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800/70 dark:text-zinc-300">
          Beginner rule: the model proposes tools; the runtime routes each request to allow, ask, or deny before execution.
        </div>

        <StepControls
          className="mt-4"
          currentStep={vis.currentStep}
          totalSteps={vis.totalSteps}
          onPrev={vis.prev}
          onNext={vis.next}
          onReset={vis.reset}
          isPlaying={vis.isPlaying}
          onToggleAutoPlay={vis.toggleAutoPlay}
          stepTitle={current.title}
          stepDescription={current.desc}
        />
      </div>
    </section>
  );
}
